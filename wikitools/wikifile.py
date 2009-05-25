# -*- coding: utf-8 -*-
# Copyright 2009 Mr.Z-man

# This file is part of wikitools.
# wikitools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
 
# wikitools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
 
# You should have received a copy of the GNU General Public License
# along with wikitools.  If not, see <http://www.gnu.org/licenses/>.

import wiki
import page
import api
import urllib2

class FileDimensionError(wiki.WikiError):
	"""Invalid dimensions"""

class File(page.Page):
	"""A file on the wiki"""
	def __init__(self, wiki, title, check=True, followRedir=False, section=False, sectionnumber=False):
		"""	
		wiki - A wiki object
		title - The page title, as a string or unicode object
		check - Checks for existence, normalizes title, required for most things
		followRedir - follow redirects (check must be true)
		section - the section name
		sectionnumber - the section number
		pageid - pageid, can be in place of title
		""" 
		self.local = ''
		self.url = ''
		page.Page.__init__(self, wiki, title, check, followRedir, section, sectionnumber)
		if self.namespace != 6:
			self.setNamespace(6, check)
		self.usage = []
			
	def getUsage(self, force=False namespaces=False):
		"""Gets all list of all the pages that use the file
		
		force - load the list even if we already loaded it before
		namespaces - list of namespaces to look in
		
		"""	
		if self.usage and not force:
			return self.usage
		if not self.title:
			self.setPageInfo()
			if not self.title:
				raise page.NoPage
		params = {
			'action': 'query',
			'list': 'imageusage',
			'iulimit': self.site.limit,
		}
		if namespaces is not False:
			params['iunamespace'] = '|'.join([str(ns) for ns in namespaces])
		params['iutitle'] = self.title	
		req = api.APIRequest(self.site, params)
		response = req.query()
		if isinstance(response, list):
			for part in response:
				self.usage.extend(self.__extractToList(part, 'imageusage'))
		else:
			self.usage = self.__extractToList(response, 'imageusage')
		return self.usage
		
	def __extractToList(self, json, stuff):
		list = []
		if stuff in json['query']:
			for item in json['query'][stuff]:
				list.append(item['title'])
		return list
	
	def download(self, width=False, height=False, location=False):
		"""Download the image to a local file
		
		width/height - set width OR height of the downloaded image
		location - set the filename to save to. If not set, the page title
		minus the namespace prefix will be used and saved to the current directory
		
		"""
		if self.pageid == 0:
			self.setPageInfo()
		params = {'action':'query',
			'prop':'imageinfo',
			'iiprop':'url'
		}
		if width and height:
			raise DimensionError("Can't specify both width and height")
		if width:
			params['iiurlwidth'] = width
		if height:
			params['iiurlheight'] = height
		if self.pageid != 0:
			params['pageids'] = self.pageid
		elif self.title:
			params['titles'] = self.title
		else:
			self.setPageInfo()
			if not self.exists: # Non-existant files may be on a shared repo (e.g. commons)
				params['titles'] = self.title
			else:
				params['pageids'] = self.pageid
		req = api.APIRequest(self.site, params)
		res = req.query(False)
		key = res['query']['pages'].keys()[0]
		url = res['query']['pages'][key]['imageinfo'][0]['url']
		if not location:
			location = self.title.split(':', 1)[1]
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.site.cookies))
		headers = { "User-agent": self.site.useragent }
		request = urllib2.Request(url, None, headers)
		data = opener.open(request)
		f = open(location, 'wb', 0)
		f.write(data.read())
		f.close()
		return location
			
			