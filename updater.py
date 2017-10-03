# -*- coding: utf-8 -*-
import os
import settings
import logger
from random import choice
import re
import transmissionrpc
import bencode
import hashlib
import telebot
from lxml import etree
import requests
import pickle
import datetime
import urllib

logger = logger.logger()
config = settings.config()
token = config['telegram']['token']
bot = telebot.TeleBot(token)
bot.config['api_key'] = token

def get_useragent():
	default = config['useragent']['default']
	ua = []
	if os.path.exists(os.path.join(config['base_dir'], config['useragent']['file'])):
		f = open(os.path.join(config['base_dir'], config['useragent']['file']))
		ua = f.read().split('\n')
		f.close()
	if ua:
		return choice(ua)
	else:
		return default


def get_proxy():
	r = requests.get("http://www.ip-adress.com/proxy_list/")
	selector = etree.HTML(r.text)
	proxies = []
	for tr_node in selector.xpath('//table[@class="htable proxylist"]/tbody/tr'):
		ip_port_content = tr_node.xpath('td[1]')[0]
		ip_port = ip_port_content.xpath('string(.)')
		proxies.append(ip_port)
	return proxies

def id_by_task(url):
	return re.search(r'php\?t=(\d+)', url).group(1)

def check_same_files(trans_item_hash, new_data):
	metainfo = bencode.bdecode(new_data)
	rhash = hashlib.sha1(bencode.bencode(metainfo['info'])).hexdigest()
	return trans_item_hash == rhash

def read_cookies():
	with open(config['cookie_file']) as f:
		return requests.utils.cookiejar_from_dict(pickle.load(f))
		
def write_cookies(data):
	with open(config['cookie_file'], 'w') as f:
		pickle.dump(data, f)

def is_rotten():
	if not os.path.exists(config['cookie_file']):
		return True
	cdate = datetime.date.fromtimestamp(os.path.getctime(config['cookie_file']))
	ndate = datetime.datetime.now().date()
	#1 day
	if int(str(ndate-cdate)[0]) > 0:
		os.remove(config['cookie_file'])
		return True
	else:
		return False

def check_tasks(tc, proxies):
	proxy = choice(proxies)
	s = requests.Session()
	#login
	data = {'login_username': config['rutracker']['login'].encode(config['rutracker']['encoding']),
							'login_password': config['rutracker']['password'].encode(config['rutracker']['encoding']),
							'login': u'Вход'.encode(config['rutracker']['encoding'])}
	headers = {'User-Agent' : get_useragent()}
	s.proxies = {'https': proxy, 'http': proxy}
	s.keep_alive = False
	if is_rotten():
		try:
			page = s.post(config['rutracker']['login_url'], data=data, headers=headers) # create connection
			write_cookies(requests.utils.dict_from_cookiejar(s.cookies))
		except Exception as e:
			logger.error('login failed: %s' % e)
			return
	
	#download and open torrent file
	for task in tc.get_torrents():
		logger.info(u'checking torrent "%s"...' % task.name)
		id = id_by_task(task.comment)
		post_params = {'t': id}
		file = s.get('%s?%s' % (config['rutracker']['download_url'], urllib.urlencode(post_params)) , timeout = 20, cookies=read_cookies(),stream=True)
		if file.status_code == 200:
			file_data = file.content
			if not check_same_files(task.hashString, file_data):
				logger.info(u'getting new series for "%s"...' % task.name)
				new_torrent_file = os.path.join(config['rutracker']['dir'], config['rutracker']['template_file_name'] % id)
				with open(new_torrent_file, 'wb') as tf:
					tf.write(file_data)
				tc.remove_torrent(task.hashString)
				tc.add_torrent(r'file://%s' % new_torrent_file)

				#notifications
				for b in config['telegram']['chat_id']:
					bot.send_message(b, u'Скачиваются новые серии для %s' % task.name)
		else:
			logger.warning('error update "%s": http response: %d' % (task.name, file.status_code))
			raise
		tc.start_all()

def main():
	try:
		tc = transmissionrpc.Client(config['transmission']['host'], port=config['transmission']['port'])
	except transmissionrpc.error.TransmissionError as e:
		logger.error(e)

	proxies = get_proxy()	
	if tc.get_torrents():
		while True:
			try:
				check_tasks(tc, proxies)
				break
			except Exception as e:
				logger.warning('Failed. %s\nTry again...' % e)
				continue
		logger.info('exit')

if __name__ == '__main__':
	main()