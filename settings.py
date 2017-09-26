# -*- coding: utf-8 -*-
import os
import json

def config():
	BASE_DIR = os.getcwd()
	json_data = open(os.path.join(BASE_DIR, 'config.json')).read()
	config = json.loads(json_data)
	config['debug'] = True
	config['base_dir'] = BASE_DIR
	return config

