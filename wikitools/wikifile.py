# -*- coding: utf-8 -*-
# Copyright 2009-2013 Alex Zaddach (mrzmanwiki@gmail.com)

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

import wikitools.wiki
import wikitools.page
import wikitools.api
import urllib.request
import base64
import io

class FileDimensionError(wikitools.wiki.WikiError):
	"""Invalid dimensions"""

class UploadError(wikitools.wiki.WikiError):
	"""Error during uploading"""

class File(wikitools.page.Page):
	"""A file on the wiki"""
	def __init__(self, site, title=None, check=True, followRedir=True, section=None, sectionnumber=None, pageid=None):
		"""
		site - A wiki object
		title - The page title, as a string or unicode object
		check - Checks for existence, normalizes title, required for most things
		followRedir - follow redirects (check must be true)
		section - the section name
		sectionnumber - the section number
		pageid - pageid, can be in place of title
		"""
		wikitools.page.Page.__init__(self, site=site, title=title, check=check, followRedir=followRedir, section=section, sectionnumber=sectionnumber, pageid=pageid)
		if self.namespace != 6:
			self.setNamespace(6, check)
		self.filehistory = []

	def getFileHistory(self, force=False):
		if self.filehistory and not force:
			return self.filehistory
		params = {
			'action': 'query',
			'prop': 'imageinfo',
			'iilimit': self.site.limit,
		}
		if self.pageid > 0:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title
		req = wikitools.api.APIRequest(self.site, params)
		self.filehistory = []
		for data in req.queryGen():
			pid = list(data['query']['pages'].keys())[0]
			for item in data['query']['pages'][pid]['imageinfo']:
				self.filehistory.append(item)
		return self.filehistory

	def getUsage(self, titleonly=False, namespaces=None):
		"""Gets a list of pages that use the file

		titleonly - set to True to only create a list of strings,
		else it will be a list of Page objects
		namespaces - List of namespaces to restrict to

		"""
		usage = []
		for title in self.__getUsageInternal(namespaces):
			if titleonly:
				usage.append(title.title)
			else:
				usage.append(title)
		return usage

	def getUsageGen(self, titleonly=False, namespaces=None):
		"""Generator function for pages that use the file

		titleonly - set to True to return strings,
		else it will return Page objects
		namespaces - List of namespaces to restrict to

		"""
		for title in self.__getUsageInternal():
			if titleonly:
				yield title.title
			else:
				yield title

	def __getUsageInternal(self, namespaces, limit):
		params = {'action':'query',
			'list':'imageusage',
			'iutitle':self.title,
			'iulimit':limit,
		}
		if namespaces is not None:
			params['iunamespace'] = '|'.join([str(ns) for ns in namespaces])

		req = wikitools.api.APIRequest(self.site, params)
		for data in req.queryGen():
			for item in data['query']['imageusage']:
				p = wikitools.page.Page(self.site, title=item['title'], pageid=item['pageid'], check=False, followRedir=False)
				p.exists = True # Non-existent pages can't have images
				yield p

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
			raise FileDimensionError("Can't specify both width and height")
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
		req = wikitools.api.APIRequest(self.site, params)
		res = req.query(False)
		key = list(res['query']['pages'].keys())[0]
		url = res['query']['pages'][key]['imageinfo'][0]['url']
		if not location:
			location = self.title.split(':', 1)[1]

		headers = { "User-agent": self.site.useragent,
			'Accept-Encoding': 'gzip'
		}
		if self.site.auth:
			headers['Authorization'] = "Basic {0}".format(
				base64.encodestring(self.site.auth[0] + ":" + self.site.auth[1])).replace('\n','')
		authman = None if self.site.auth is None else HTTPDigestAuth(self.site.auth)
		data = self.site.session.get(url, headers=headers, auth=authman)
		f = open(location, 'wb', 0)
		f.write(data.content)
		f.close()
		return location

	def upload(self, fileobj=None, comment='', url=None, ignorewarnings=False, watch=False, watchlist='preferences'):
		"""Upload a file

		fileobj - A file object opened for reading
		comment - The log comment, used as the inital page content if the file
		doesn't already exist on the wiki
		url - A URL to upload the file from, if allowed on the wiki
		ignorewarnings - Ignore warnings about duplicate files, etc.
		watch - Add the page to your watchlist (DEPRECATED, use watchlist)
		watchlist - Options are "preferences", "watch", "unwatch", or "nochange"

		"""
		if not fileobj and not url:
			raise UploadError("Must give either a file object or a URL")
		if fileobj and url:
			raise UploadError("Cannot give a file and a URL")
		if fileobj:
			if not isinstance(fileobj, io.IOBase):
				raise UploadError('If uploading from a file, a file object must be passed')
			if 'r' not in fileobj.mode:
				raise UploadError('File must be readable')
			fileobj.seek(0)
		params = {'action':'upload',
			'comment':comment,
			'filename':self.unprefixedtitle,
			'token':self.site.getToken('csrf')
		}
		if url:
			params['url'] = url
		if ignorewarnings:
			params['ignorewarnings'] = ''
		if watch:
			params['watch'] = ''
		if watchlist:
			params['watchlist'] = watchlist
		req = wikitools.api.APIRequest(self.site, params, write=True, file=fileobj)
		res = req.query()
		if 'upload' in res:
			if res['upload']['result'] == 'Success':
				self.wikitext = ''
				self.links = []
				self.templates = []
				self.exists = True
			elif res['upload']['result'] == 'Warning':
				for warning in list(res['upload']['warnings'].keys()):
					if warning == 'duplicate':
						print('File is a duplicate of ' + res['upload']['warnings']['duplicate'][0])
					elif warning == 'page-exists' or warning == 'exists':
						print('Page already exists: ' + res['upload']['warnings'][warning])
					else:
						print('Warning: ' + warning + ' ' + res['upload']['warnings'][warning])
		return res

			
