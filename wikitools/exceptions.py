# -*- coding: utf-8 -*-
# Copyright 2008-2016 Alex Zaddach (mrzmanwiki@gmail.com)

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

class APIError(Exception):
	"""Base class for errors"""

class APIQueryError(APIError):
	"""Error message in API query"""

class APIDisabled(APIError):
	"""API not enabled"""

class APIFailure(APIError):
	"""API appears to be broken, or this isn't a MediaWiki API"""

class WikiError(Exception):
	"""Base class for errors"""

class UserBlocked(WikiError):
	"""Trying to edit while blocked"""

class UnsupportedError(WikiError):
	"""Feature not available on this wiki"""

class BadTitle(WikiError):
	"""Invalid title"""

class NoPage(WikiError):
	"""Non-existent page"""

class BadNamespace(WikiError):
	"""Invalid namespace number"""

class EditError(WikiError):
	"""Problem with edit request"""

class ProtectError(WikiError):
	"""Problem with protection request"""

class FileDimensionError(WikiError):
	"""Invalid dimensions"""

class UploadError(WikiError):
	"""Error during uploading"""
