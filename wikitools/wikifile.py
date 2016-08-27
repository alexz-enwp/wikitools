# -*- coding: utf-8 -*-
# Copyright 2009-2016 Alex Zaddach (mrzmanwiki@gmail.com)

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

from . import api
from . import exceptions
from . import page
from . import internalfunctions
from wikitools.pagelist import makePage
import io
import os.path
import warnings

class File(page.Page):
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
		page.Page.__init__(self, site=site, title=title, check=check, followRedir=followRedir, section=section, sectionnumber=sectionnumber, pageid=pageid)
		if self.namespace != 6:
			self.setNamespace(6, check)

	def getFileHistory(self, exif=True, limit='all'):
		"""Get the file upload history

		exif - If False, get only basic information (timestamp, upload summary, user, etc)
			If True (default), also get the EXIF metadata
		limit - Only retrieve a certain number of revisions. If 'all' (default), all revisions are returned

		The data is returned as a list of dicts like:
		{'bitdepth': '8',
		  'comment': 'Upload summary',
		  'descriptionurl': 'https://commons.wikimedia.org/wiki/File:Filename.jpg',
		  'height': 259,
		  'mediatype': 'BITMAP',
		  'metadata': [{'name': 'Orientation', 'value': 1}, # EXIF data, only included if exif=True
			       {'name': 'XResolution', 'value': '2000000/10000'},
			       {'name': 'YResolution', 'value': '2000000/10000'},
				# Actual metadata included will vary depending on the file
			       {'name': 'MEDIAWIKI_EXIF_VERSION', 'value': 1}],
		  'mime': 'image/jpeg',
		  'sha1': 'c858353eed661f22be5d5e44b82c3e18388a25f9',
		  'size': 50786,
		  'timestamp': '2009-01-19T06:19:25Z',
		  'url': 'https://upload.wikimedia.org/wikipedia/commons/3/31/Filename.jpg',
		  'user': 'Username',
		  'userid': '141409',
		  'width': 555}
		"""
		if not self.title:
			self.setPageInfo()
		iiprop = 'timestamp|user|userid|comment|url|size|dimensions|sha1|mime|mediatype|bitdepth'
		iimetadataversion = None
		if exif:
			iiprop+='|metadata'
			iimetadataversion = 'latest'
		return internalfunctions.getList(self, 'prop', 'imageinfo', 'ii', limit=limit, 
		titles=self.title, iiprop=iiprop, iimetadataversion=iimetadataversion)


	def getFileHistoryGen(self, exif=True, limit='all'):
		"""Generator function for file history

		The interface is the same as getFileHistory, but it will only retrieve 1 revision at a time.
		This will be slower and have much higher network overhead, but does not require storing
		the entire history in memory
		"""
		if not self.title:
			self.setPageInfo()
		iiprop = 'timestamp|user|userid|comment|url|size|dimensions|sha1|mime|mediatype|bitdepth'
		iimetadataversion = None
		if exif:
			iiprop+='|metadata'
			iimetadataversion = 'latest'
		return internalfunctions.getListGen(self, 'prop', 'imageinfo', 'ii', limit=limit, 
		titles=self.title, iiprop=iiprop, iimetadataversion=iimetadataversion)

	def getUsage(self, titleonly=False, force=False, namespaces=None):
		"""Gets a list of pages that use the file

		force - Deprecated, unused
		titleonly - set to True to only create a list of strings,
		else it will be a list of Page objects
		namespaces - List of namespaces to restrict to

		Any changes to getUsage functions should also be made to getAllMembers in category
		"""
		usage = []
		for title in self.__getUsageInternal(namespaces, self.site.limit):
			if titleonly:
				usage.append(title.title)
			else:
				usage.append(title)
		return usage

	def getUsageGen(self, titleonly=False, force=False, namespaces=None):
		"""Generator function for pages that use the file

		force - Deprecated, unused
		titleonly - set to True to return strings,
		else it will return Page objects
		namespaces - List of namespaces to restrict to

		"""
		for title in self.__getUsageInternal(namespaces, 50):
			if titleonly:
				yield title.title
			else:
				yield title

	def __getUsageInternal(self, namespaces, limit):
		if 'continue' not in self.site.features:
			raise exceptions.UnsupportedError("MediaWiki 1.21+ is required for this function")
		params = {'action':'query',
			'list':'imageusage',
			'iutitle':self.title,
			'iulimit':limit,
		}
		if namespaces is not None:
			params['iunamespace'] = '|'.join([str(ns) for ns in namespaces])

		req = api.APIRequest(self.site, params)
		for data in req.queryGen():
			for item in data['query']['imageusage']:
				yield makePage(item, self.site, False)

	def download(self, width=False, height=False, location=False):
		"""Download the image to a local file

		width/height - set width OR height of the downloaded image, in pixels
		location - set the path and/or filename to save to. If not set, the page title
		minus the namespace prefix will be used and saved to the current directory

		"""
		if self.pageid == 0:
			self.setPageInfo()
		params = {'action':'query',
			'prop':'imageinfo',
			'iiprop':'url'
		}
		if width and height:
			raise exceptions.FileDimensionError("Can't specify both width and height")
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
		key = list(res['query']['pages'].keys())[0]
		url = res['query']['pages'][key]['imageinfo'][0]['url']
		if location:
			location = os.path.expanduser(os.path.expandvars(location))
			if os.path.isdir(location):
				location += '/'+self.title.split(':', 1)[1]
			location = os.path.normpath(location)
		if not location:
			location = self.title.split(':', 1)[1]

		headers = { "User-agent": self.site.useragent }
		with open(location, 'wb') as handle:
			response = self.site.session.get(url, headers=headers, auth=self.site.auth, stream=True)
			for block in response.iter_content(1024):
				if not block:
				            break
				handle.write(block)
		return location

	def upload(self, fileobj=None, comment='', text='', url=None, ignorewarnings=False, watch=False, watchlist='preferences'):
		"""Upload a file

		fileobj - A file object opened for reading
		comment - The log comment
		text - Initial page text for new files, comment will be used if not specified
		doesn't already exist on the wiki
		url - A URL to upload the file from, if allowed on the wiki
		ignorewarnings - Ignore warnings about duplicate files, etc.
		watch - Add the page to your watchlist (DEPRECATED, use watchlist)
		watchlist - Options are "preferences", "watch", "unwatch", or "nochange"

		"""
		if not fileobj and not url:
			raise exceptions.UploadError("Must give either a file object or a URL")
		if fileobj and url:
			raise exceptions.UploadError("Cannot give a file and a URL")
		if fileobj:
			if not isinstance(fileobj, io.IOBase):
				raise exceptions.UploadError('If uploading from a file, a file object must be passed')
			if not hasattr(fileobj, 'mode') or 'r' not in fileobj.mode:
				raise exceptions.UploadError('File must be readable')
			fileobj.seek(0)
		params = {'action':'upload',
			'comment':comment,
			'filename':self.unprefixedtitle,
			'token':self.site.getToken('csrf')
		}
		if fileobj:
			params['file'] = fileobj
		if url:
			params['url'] = url
		if ignorewarnings:
			params['ignorewarnings'] = ''
		if watch:
			params['watch'] = ''
		if watchlist:
			params['watchlist'] = watchlist
		if text:
			params['text'] = text
		req = api.APIRequest(self.site, params, write=True)
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
						warnings.warn('File is a duplicate of ' + res['upload']['warnings']['duplicate'][0])
					elif warning == 'page-exists' or warning == 'exists':
						warnings.warn('Page already exists: ' + res['upload']['warnings'][warning])
					else:
						warnings.warn('Warning: ' + warning + ' ' + res['upload']['warnings'][warning])
		return res

	def __getattr__(self, name):
		"""Computed attributes:
		usage
		"""
		if name != 'usage':
			return super().__getattr__(name)
		return self.getUsage()
			
