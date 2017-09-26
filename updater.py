# -*- coding: utf-8 -*-
import os
import logger
import settings
from random import choice
import cookielib
import urllib2
import urllib
import re
import transmissionrpc
import bencode
import hashlib
import telebot
from lxml import etree
logger = logger.logger()
config = settings.config()

token = config['telegram']['token']
bot = telebot.TeleBot(token)
bot.config['api_key'] = token


def get_proxy():
	request = urllib2.Request("http://www.ip-adress.com/proxy_list/")
	request.add_header("Referer","https://www.google.co.in/")
	f = urllib2.urlopen(request)
	str1 = f.read()
	selector = etree.HTML(str1)
	proxies = []
	for tr_node in selector.xpath('//table[@class="htable proxylist"]/tbody/tr'):
		ip_port_content = tr_node.xpath('td[1]')[0]
		ip_port = ip_port_content.xpath('string(.)')
		proxies.append(ip_port)
	f.close()
	return choice(proxies)

def id_by_task(url):
	return re.search(r'php\?t=(\d+)', url).group(1)

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

def check_same_files(trans_item_hash, new_data):
	metainfo = bencode.bdecode(new_data)
	rhash = unicode(hashlib.sha1(bencode.bencode(metainfo['info'])).hexdigest())
	return trans_item_hash == rhash

def check_tasks(tc):
	proxy = get_proxy()
	cookies = cookielib.CookieJar()
	logger.info('using proxy %s' % proxy)
	opener = urllib2.build_opener(urllib2.ProxyHandler({'https': proxy, 'http': proxy}), urllib2.HTTPCookieProcessor(cookies))
	urllib2.install_opener(opener)
	#login
	data = urllib.urlencode({'login_username': config['rutracker']['login'].encode(config['rutracker']['encoding']),
							'login_password': config['rutracker']['password'].encode(config['rutracker']['encoding']),
							'login': u'Вход'.encode(config['rutracker']['encoding'])})
	headers = {'User-agent' : get_useragent()}
	req = urllib2.Request(config['rutracker']['login_url'], data = data, headers= headers)
	try:
		response = opener.open(req)
	except:
		logger.error('login failed')
	if response.getcode() != 200:
		raise urllib.error.HTTPError(response.geturl(), response.getcode(),
			"HTTP request to {} failed with status: {}".format(config['rutracker']['encoding'], response.getcode()),
			response.info(), None)
	if 'bb_session' not in [cookie.name for cookie in cookies]:
		raise ValueError("unable to connect using given credentials.")
	else:
		logger.info("login successful.")
	#download and open torrent file
	for task in tc.get_torrents():
		logger.info(u'checking torrent "%s"...' % task.name)
		id = id_by_task(task.comment)
		post_params = {'t': id}
		req = urllib2.Request(config['rutracker']['download_url'], urllib.urlencode(post_params), headers= headers)
		handle = opener.open(req)
		file_data = handle.read()
		if not check_same_files(task.hashString, file_data):
			logger.info(u'getting new series for "%s"...' % task.name)
			new_torrent_file = os.path.join(config['rutracker']['dir'], config['rutracker']['template_file_name'] % id)
			tf = open(new_torrent_file, 'wb')
			tf.write(file_data)
			tf.close()
			tc.remove_torrent(task.hashString)
			tc.add_torrent(r'file://%s' % new_torrent_file)
			for b in config['telegram_chat_id']:
				bot.send_message(b, u'Скачиваются новые серии для %s' % task.name)
		tc.start_all()

def main():
	try:
		tc = transmissionrpc.Client(config['transmission']['host'], port=config['transmission']['port'])
	except transmissionrpc.error.TransmissionError as e:
		logger.error(e)

		
	if tc.get_torrents():
		# req_proxy = RequestProxy()
		while True:
			try:
				check_tasks(tc)
				break
			except Exception as e:
				logger.warning('Failed. %s\nTry again...' % e)
				continue
		logger.info('exit')

if __name__ == '__main__':
	main()