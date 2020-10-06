'''
Zettelkasten converter
Eugene Ho, 17 Aug 2020

Convert zettelkasten between txt and csv

Next steps
Accelerate timestamping
'''

import re
import os
import csv
import time
import tkinter as tk
from tkinter import filedialog
from datetime import datetime, timezone

class Controller:
	'''Provide GUI to choose file and split into path root and extension'''

	def __init__(self):
		self.file_path = ''

	def tkgui_getfile(self, message = "Select file"):
		'''Select file with dialog and check'''
		root = tk.Tk(); root.withdraw()		
		self.file_path = filedialog.askopenfilename(
			initialdir = "..\\data",title = message)

		return self.file_path

	def split_path(self, path):
		'''os.path.splitext file path to separate path root and .extension'''
		path_root, extension = os.path.splitext(path)
		return path_root, extension

class Zettel:
	'''Import and export information for one zettel with index as variable name'''

	def __init__(self):
		self.parent = ''
		self.title = ''
		self.zettel = ''
		self.reference = ''
		self.keyword = ''
		self.type = 'zettel'

	def __str__(self):
		if 'section' in self.type:
			return f"[parent] {self.parent} [title] {self.title}"
		elif 'zettel' in self.type:
			return f"[parent] {self.parent} [title] {self.title}\
\n[zettel] {self.zettel} \n[reference] {self.reference} \n[keyword] {self.keyword}"
		else: return print(f"Zettel.__str__ Zettel type ({self.type}) not recognised")

	def clean_text(self, text, capitals = False):
		'''Scrub string of double spaces, colons, and capitalize'''
		text = " ".join(text.split()) # remove double spaces

		if len(text) > 1: # empty/short strings create index errors
			text = text.translate(str.maketrans(';', ',')) # replace certain characters
			return text[0].upper() + text[1:] if capitals else text
		else: return text

	def store_index_zettel(self, library, parent, field_name, field_contents):
		'''Store previously extracted section contents into zettel'''
		self.parent = parent
		self.title = self.clean_text(field_name, True)
		self.zettel = field_contents
		self.type = 'section'

	def store_zettel_field(self, library = {}, key = 0, parent = 0, field_name = '', field_contents = ''):
		'''Store previously extracted zettelkasten into dictionary
		library: to which fields will be added
		key: index of zettel to which field belongs
		parent: manually specify parent field
		field_name: string - index, parent, zettel, reference
		field_contents: string body of field
		'''
		field_name = field_name.lower()
		# print('store_zettel_field: ', field_name)#, field_contents)

		if 'title' in field_name:
			self.title = self.clean_text(field_contents, True)

		# recognise section zettel based on contents		
		elif ('zettel' in field_name and 
			('index card' in field_contents.lower() 
				or 'section header' in field_contents.lower())):
			self.zettel = self.clean_text(field_contents, True)
			self.type = 'section'

		elif 'zettel' in field_name and ':' not in field_contents:
			self.zettel = self.clean_text(field_contents, True)

		# split contents into title and zettel if colon present and title empty
		elif 'zettel' in field_name and ':' in field_contents and not self.title:
			split_contents = re.split('[:]', field_contents)
			self.title = self.clean_text(split_contents[0], True)
			self.zettel = self.clean_text(split_contents[1], True)

		elif 'reference' in field_name:
			self.reference = field_contents

		elif 'keyword' in field_name:
			self.keyword = field_contents

		elif 'parent' in field_name:
			self.parent = field_contents

		else: print(f'Error: Field {field_name} not identified \n'
			f'Field contents: {field_contents}')

class Zettelkasten(Zettel):
	'''Convert zettelkasten between txt and csv formats'''

	def __init__(self, diagnostics = False):
		'''Initialise library[key = UID] of dictionaries[keys = parent, title, contents, reference, keyword]'''
		self.diagnostics = diagnostics # switch for diagnostics information
		self.library = {}
		python_timestamp = datetime.now(timezone.utc) - datetime(1899, 12, 30, tzinfo = timezone.utc)
		sheets_timestamp = python_timestamp.days + python_timestamp.seconds/(3600*24) + python_timestamp.microseconds/(3600*24*1000000)
		self.timestamp = sheets_timestamp
		self.master_key = sheets_timestamp

	def display(self, quantity, start_index = 0):
		'''Show some number of zettels'''
		for key, value in list(self.library.items())[start_index:start_index+quantity]:
			print(f"[index] {key} [parent] {value.parent} [title] {value.title}")

	def gsheets_timestamp(self, timestamp = None):
		'''Generate timestamp in Googlesheets format UTC (counts days from 30/12/1899)'''
		if timestamp == None: timestamp = self.timestamp
		self.timestamp += 0.00002
		return '{:.6f}'.format(timestamp)

	def import_csv_odict_gen(self, file_path = ''):
		'''Read csv file and row contents as odict generator'''

		# check file type
		if not file_path.lower().endswith('.csv'):
			print('Error: Wrong filetype in importing .csv')
			return dict()

		with open(file_path, 'r', encoding = 'utf-8') as my_file:
			contents = csv.DictReader(my_file, delimiter=',')
			for row_odict in contents: yield row_odict
		# return csv_dict

	def dict_to_zk(self, csv_dict, library = None):
		'''Store csv as dict into library'''
		# clean out library
		if library == None: library = dict()
		split_lib, key = dict(), 0
		# row contains one zettel
		for field_name, field_contents in csv_dict.items():
			fields_tuple = field_name.lower(), field_contents
			# print("fields_tuple: ", fields_tuple)
			key, split_lib = self.store_tuple_to_lib(fields_tuple, 
				'zettel', split_lib, key)
			# ignore empty dictionary outputs
			if split_lib: library.update(split_lib)
			else: print("In dict_to_zk, empty zettel")
		return library

	def import_txt_to_str(self, file_path = ''):
		'''Read txt file and return library'''
		# check file type
		if not file_path.lower().endswith('.txt'):
			print('Error: Wrong filetype in importing .txt')
			return library

		with open(file_path, 'r', encoding = 'utf-8') as my_file:
			contents = my_file.read()
			my_file.close()

		return contents

	def find_sections_in_txt(self, contents, library = {}, field_type = ''):
		'''Extract subsections as search results from text using regex'''
		if 'section' in field_type:
			pattern = r'\n{1}[\w ,]{2,100}\n{2}'
			# whitespace necessary in [\w ] to allow spaces in header
		elif 'zettel' in field_type:
			pattern = r'\[\w{1,10}\]'
		else: print('Field type error'); return None

		# print(['',contents[11000:11500]])
		# print(len(re.findall(pattern, contents)))
		search_results = re.finditer(pattern, contents)
		return search_results

	def sort_search_results_to_tuple(self, contents, search_results):
		'''Iterate results and find each field marker to sort into tuple'''

		key, end_index, field_name, field_contents = 0, 0, '', ''
		fields_out_list = []

		for result in search_results:

			# for sections, capture set of text before first subtitle
			if not end_index:
				start_index, end_index = 0, 0
				field_name = ''#self.clean_text(result.group(), False)

			# extract, clean, yield field contents
			next_start_index = result.start()
			field_contents =  self.clean_text(contents[end_index: next_start_index], False)
			start_index, end_index = result.span()
			yield field_name, field_contents

			# update field_name
			field_name = self.clean_text(result.group(), False)

		# capture final entry
		field_contents = self.clean_text(contents[end_index:-1], False)
		yield field_name, field_contents

	def split_generator(self, contents, field_type, parent):
		'''Store contents into zettels and yield key, zettel pair'''
		split_lib, key = dict(), 0
		search_results = self.find_sections_in_txt(contents, field_type = field_type)
		results_generator = self.sort_search_results_to_tuple(contents, search_results)
		for fields_tuple in results_generator:
			key, split_lib = self.store_tuple_to_lib(fields_tuple, field_type, split_lib, key, parent)
			# ignore empty dictionary outputs
			if split_lib: yield key, split_lib[key]
			else: print("In split_generator, empty library")

	def store_tuple_to_lib(self, fields_tuple, field_type, library = None, key = 0, parent = 0):
		'''Store zettelkasten contents or sections into fields in library'''
		if library == None: library = dict()

		field_name, field_contents = fields_tuple
		# store in dictionary according to section or zettel
		# print('store_list_to_lib: ', field_name, field_contents)
		if 'section' in field_type:
			key, library = self.store_subsections(library, field_name, field_contents)
		elif not field_name: pass
		elif 'zettel' in field_type and 'index' in field_name:
		# create new dictionary entry at each instance of 'index'
			key = self.gsheets_timestamp() if len(field_contents) < 10 else field_contents
			if key in library.keys(): print('Error: Duplicate key when assigning index')
			else: library[key] = Zettel(); library[key].parent = parent

		elif 'zettel' in field_type and key:
			library[key].store_zettel_field(library, key, parent, field_name, field_contents)
		else: print(f'Error: Field type {field_type}, Field name: {field_name} not recognised', '\n',
			f"Field contents: {field_contents}, Key: {key}")
		
		return key, library

	def store_subsections(self, library = {}, field_name = '', field_contents = ''):
		'''Store chunk of text in dictionary with section heading as title and section as zettel'''
		key = self.gsheets_timestamp()
		if key in library.keys(): print('Error: Duplicate key while storing subsection')
		elif (field_name or field_contents): # ignore empty sections
			library[key] = Zettel()
			library[key].store_index_zettel(library, self.gsheets_timestamp(self.master_key),
				field_name, field_contents)
		else: print(f"Section omitted: field_name: {field_name} field_contents: {field_contents}")
		return key, library

	def run_txt(self, file_path):
		'''Full procedure to import zettelkasten using file_path from txt 
		incl section headers to zettels'''
		library = dict()
		contents = self.import_txt_to_str(file_path = file_path)
		if self.diagnostics: print("During import \n", contents[:500])

		parent, field_type = self.gsheets_timestamp(), 'section'
		section_zettel_generator = self.split_generator(contents, field_type, parent)
		for parent, section_zettel in section_zettel_generator:
			contents, field_type = section_zettel.zettel, 'zettel'
			section_zettel.zettel = "Index card"
			library.update({parent: section_zettel})

			if self.diagnostics: print("Section generator \n", contents[:100])
			
			zettel_generator = self.split_generator(contents, field_type, parent)
			for key, zettel in zettel_generator: library.update({key:zettel})
		
		return library

	def run_csv(self, file_path):
		'''Full procedure to import zettelkasten using file_path from csv'''
		library = dict()
		csv_odict_gen = self.import_csv_odict_gen(file_path = file_path)
		for csv_odict in csv_odict_gen:
			row_lib = self.dict_to_zk(csv_odict)
			library.update(row_lib)
			if self.diagnostics:
				print("During import \n", row_lib)
		
		return library

	def clear_empty_zettel(self, library):
		'''Clear empty zettels'''
		library = {k: v for k, v in library.items() if (v.title or v.zettel)}
		return library

	def export_zk_txt(self, file_path, library = None):
		'''Write dictionary from memory to txt'''
		if library == None: library = self.library
		out_file_path = file_path + '_' +\
			str(self.gsheets_timestamp(self.master_key)) + '.txt'
		txt_output = open(out_file_path,'w', newline='')
		for key, zettel in library.items():
			txt_output.write(f"[index] {key} {zettel}\n\n")
		txt_output.close()
		return out_file_path

	def export_zk_csv(self, file_path, library = None):
		'''Write dictionary from memory to csv'''
		if library == None: library = self.library
		out_file_path = file_path + '_' +\
			str(self.gsheets_timestamp(self.master_key)) + '.csv'
		csv_output = open(out_file_path,'w', newline='')
		csv_writer = csv.writer(csv_output , delimiter=';')

		for key, zettel in library.items():
			csv_writer.writerow([key, zettel.parent, zettel.title, zettel.zettel, 
				zettel.reference, zettel.keyword])
		csv_output.close()
		return out_file_path

if __name__ == '__main__':
	zkn = Zettelkasten(diagnostics = True)
	controller = Controller()
	file_path = controller.tkgui_getfile()
	# print(file_path)
# 	file_path = 'C:/Users/Eugene/Documents/GitHub/zettelkasten_txt_to_csv\
# /data/Learning to Learn zettelkasten - Oakley - Coursera.txt'
	path_root, extension = controller.split_path(file_path)
# 	file_path = 'C:/Users/Eugene/Documents\
# /GitHub/zettelkasten_txt_to_csv/data/Zettelkasten v0_2.csv'
	
	# csv_odict_gen = zkn.import_csv_odict_gen(file_path = file_path)
	# for csv_odict in csv_odict_gen:
	if extension in '.csv':
		zkn.library = zkn.run_csv(file_path)
	elif extension in '.txt':
		zkn.library = zkn.run_txt(file_path)
	else: print(f'Extension not recognised: {extension}')
	# zkn.library = zkn.run_csv(file_path)
	zkn.display(10)
	print(len(zkn.library), len(set(zkn.library.keys())))
	zkn.library = zkn.clear_empty_zettel(zkn.library)
	print(len(zkn.library), len(set(zkn.library.keys())))
	# zkn.export_zk_txt(path_root, zkn.library)