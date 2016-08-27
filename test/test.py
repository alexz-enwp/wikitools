import unittest
from wikitools import api
from wikitools import wiki
from wikitools import page
from wikitools import category
from wikitools import wikifile
from wikitools import user
from wikitools import pagelist
import wikitools.exceptions
import warnings
import requests.exceptions
import os
import io

class TestAPI(unittest.TestCase):

	def setUp(self):
		# requests causes a bunch of unclosed socket warnings
		warnings.filterwarnings("ignore", category=ResourceWarning)
		self.site = wiki.Wiki('http://localhost/w/api.php')

	def test_query(self):
		params = {'action':'query'}
		req = api.APIRequest(self.site, params)
		res = req.query(False)
		self.assertIsInstance(res, api.APIResult)

	def test_query_APIError(self):
		params = {'action':'error'}
		req = api.APIRequest(self.site, params)
		with self.assertRaises(wikitools.exceptions.APIQueryError):
			res = req.query(False)

	def test_queryGen_APIError(self):
		params = {'action':'error'}
		req = api.APIRequest(self.site, params)
		with self.assertRaises(wikitools.exceptions.APIQueryError):
			for data in req.queryGen():
				pass

	def test_queryGen(self):
		params = {'action':'query'}
		req = api.APIRequest(self.site, params)
		for data in req.queryGen():
			self.assertIsInstance(data, api.APIResult)

	def test_getRaw_HTTP_error_write(self):
		self.site.apibase = 'http://httpbin.org/status/500'
		params = {}
		warnings.filterwarnings("error", category=UserWarning, module='wikitools.api')
		with self.assertRaises(requests.exceptions.HTTPError):
			req = api.APIRequest(self.site, params, write=True)
			res = req.query(False)
		warnings.filterwarnings("default", category=UserWarning, module='wikitools.api')

	def test_getRaw_HTTP_error_nonwrite(self):
		self.site.apibase = 'http://httpbin.org/status/500'
		self.site.maxwaittime = 10
		params = {}
		with self.assertWarns(UserWarning):
			with self.assertRaises(requests.exceptions.HTTPError):
				req = api.APIRequest(self.site, params)
				res = req.query(False)

	def test_parseJSON_bad_data_write(self):
		self.site.apibase = 'http://localhost/w/index.php'
		params = {}
		warnings.filterwarnings("error", category=UserWarning, module='wikitools.api')
		with self.assertRaises(wikitools.exceptions.APIFailure):
			req = api.APIRequest(self.site, params, write=True)
			res = req.query(False)
		warnings.filterwarnings("default", category=UserWarning, module='wikitools.api')

	def test_parseJSON_bad_data_nonwrite(self):
		self.site.apibase = 'http://localhost/w/index.php'
		self.site.maxwaittime = 10
		params = {}
		with self.assertWarns(UserWarning):
			with self.assertRaises(wikitools.exceptions.APIFailure):
				req = api.APIRequest(self.site, params)
				res = req.query(False)

	def test_parseJSON_maxlag(self):
		site = wiki.Wiki('https://en.wikipedia.org/w/api.php')
		params = {'action':'query'}
		req = api.APIRequest(site, params)
		req.changeParam('maxlag', '-1')
		warnings.filterwarnings("error", category=UserWarning, module='wikitools.api')
		with self.assertRaises(UserWarning):
			req.query(False)
		warnings.filterwarnings("default", category=UserWarning, module='wikitools.api')

class TestWiki(unittest.TestCase):

	def setUp(self):
		# requests causes a bunch of unclosed socket warnings
		warnings.filterwarnings("ignore", category=ResourceWarning)
		self.site = wiki.Wiki('http://localhost/w/api.php')

	def test_constructor(self):
		self.assertIsInstance(self.site.NS_MAIN, wiki.Namespace)
		self.assertEqual(self.site.NS_TALK, 1)
		self.assertIn('newtoken', self.site.features)

	def test_login_bad_name(self):
		with self.assertWarns(UserWarning):
			self.site.login('badusername<>|#', 'password')

	def test_login_good_name(self):
		self.assertTrue(self.site.login('GoodUsername', 'goodpassword'))

	def test_getToken_anon(self):
		token = self.site.getToken('csrf')
		self.assertEqual(token, '+\\')

	def test_getToken(self):
		self.site.login('GoodUsername', 'goodpassword')
		token = self.site.getToken('csrf')
		self.assertNotEqual(token, '+\\')

	def test_isLoggedIn(self):
		self.assertFalse(self.site.isLoggedIn())
		self.site.login('GoodUsername', 'goodpassword')
		self.assertTrue(self.site.isLoggedIn('GoodUsername'))

	def test_logout(self):
		self.site.login('GoodUsername', 'goodpassword')
		self.site.logout()
		self.assertEqual(self.site.username, '')
		self.assertFalse(self.site.isLoggedIn())

	def test_hash(self):
		newsite = wiki.Wiki('http://localhost/w/api.php')
		d = {self.site : 'Foo' }
		self.assertTrue(newsite in d.keys())	
		
	def test_equality(self):
		newsite = wiki.Wiki('http://localhost/w/api.php')
		othersite = wiki.Wiki('https://en.wikipedia.org/w/api.php')
		self.assertEqual(newsite, self.site)
		self.assertNotEqual(othersite, self.site)

	def test_Namespace_combination(self):
		self.assertEqual(self.site.NS_MAIN|self.site.NS_TEMPLATE|self.site.NS_USER,
			'0|10|2')

class TestPage(unittest.TestCase):

	def setUp(self):
		# requests causes a bunch of unclosed socket warnings
		warnings.filterwarnings("ignore", category=ResourceWarning)
		self.site = wiki.Wiki('http://localhost/w/api.php')

	def tearDown(self):
		api.logging = False
		api.querylog = api.deque()
		api.resultlog = api.deque()

	def test_namespaceDetect(self):
		self.assertEqual(page.namespaceDetect('Normal title', self.site), 0)
		self.assertEqual(page.namespaceDetect('Colon:Title', self.site), 0)
		self.assertEqual(page.namespaceDetect('project:Title', self.site), 4)
		self.assertEqual(page.namespaceDetect('File talk:Title', self.site), 7)
		self.assertEqual(page.namespaceDetect('User talk:More:text', self.site), 3)
		self.assertEqual(page.namespaceDetect('Image:Title', self.site), 6)

	def test_constructor(self):
		api.logging = True
		p1 = page.Page(self.site, 'talk:page')
		self.assertEqual(p1.title, 'Talk:Page')
		self.assertEqual(p1.unprefixedtitle, 'Page')
		self.assertEqual(p1.urltitle, 'Talk%3APage')
		self.assertTrue(p1.exists)
		self.assertIs(p1.namespace, 1)
		self.assertGreater(p1.pageid, 0)
		self.assertIs(len(api.querylog), 1)
		log = api.querylog.pop()
		self.assertIn('redirects', log)

	def test_constructor_pageid_check_false(self):
		api.logging = True
		p1 = page.Page(self.site, pageid=123, check=False)
		self.assertIs(p1.exists, None)
		self.assertIs(p1.pageid, 123)
		self.assertIs(p1.namespace, None)
		self.assertEqual(p1.unprefixedtitle, None)
		self.assertTrue(p1.followRedir)
		self.assertIs(len(api.querylog), 0)

	def test_constructor_pageid_check_true(self):
		api.logging = True
		with self.assertRaises(wikitools.exceptions.WikiError):
			p1 = page.Page(self.site, pageid=123456789, check=True)

	def test_constructor_check_false(self):
		api.logging = True
		p1 = page.Page(self.site, 'talk:page', check=False)
		self.assertIs(p1.exists, None)
		self.assertIs(p1.pageid, 0)
		self.assertIs(p1.namespace, 1)
		self.assertEqual(p1.unprefixedtitle, 'Page')
		self.assertTrue(p1.followRedir)
		self.assertIs(len(api.querylog), 0)

	def test_constructor_no_title_or_pageid(self):
		with self.assertRaises(wikitools.exceptions.WikiError):
			p1 = page.Page(self.site, title='', pageid=0)

	def test_constructor_separate_ns(self):
		p1 = page.Page(self.site, 'page', namespace=1)
		self.assertEqual(p1.title, 'Talk:Page')
		self.assertEqual(p1.unprefixedtitle, 'Page')
		self.assertEqual(p1.urltitle, 'Talk%3APage')
		self.assertTrue(p1.exists)
		self.assertIs(p1.namespace, 1)
		self.assertGreater(p1.pageid, 0)

	def test_constructor_section_priority(self):
		p1 = page.Page(self.site, 'Page#Section 2', sectionnumber=0, section='Section 1')
		self.assertIs(p1.section, 0)
		p1 = page.Page(self.site, 'Page#Section 2', section='Section 1')
		self.assertIs(p1.section, 1)
		p1 = page.Page(self.site, 'Page#Section 2')
		self.assertIs(p1.section, 2)

	def test_urltitle(self):
		p1 = page.Page(self.site, 'page $/Б_官話', check=False)
		self.assertEqual(p1.urltitle, 'Page_%24/%D0%91_%E5%AE%98%E8%A9%B1')

	def test_setNamespace(self):
		p1 = page.Page(self.site, 'Page')
		p1_id = p1.pageid
		api.logging = True
		p1.setNamespace(1)
		self.assertNotEqual(p1_id, p1.pageid)
		self.assertGreater(p1.pageid, 0)
		self.assertEqual(p1.title, 'Talk:Page')
		self.assertEqual(p1.unprefixedtitle, 'Page')
		self.assertEqual(p1.urltitle, 'Talk%3APage')
		self.assertIs(len(api.querylog), 1)
		log = api.querylog.pop()
		self.assertIn('redirects', log)

	def test_setSection_valid_name(self):
		p1 = page.Page(self.site, "Page")
		p1.setSection("Section 1")
		self.assertEqual(p1.section, 1)		

	def test_setSection_invalid_name(self):
		p1 = page.Page(self.site, "Page")
		p1.setSection("Section Q")
		self.assertIs(p1.section, None)	

	def test_toggleTalk(self):
		p1 = page.Page(self.site, "Page")
		p2 = p1.toggleTalk()
		self.assertIs(p1.namespace, 0)
		self.assertGreater(p1.pageid, 0)
		self.assertEqual(p2.title, 'Talk:Page')
		self.assertEqual(p2.unprefixedtitle, 'Page')
		self.assertEqual(p2.urltitle, 'Talk%3APage')

	def test_getWikiText(self):
		p1 = page.Page(self.site, "Page")
		p2 = page.Page(self.site, "Page#Section 1")
		api.logging = True
		text = p1.getWikiText()
		self.assertIs(len(api.querylog), 1)
		log = api.querylog.pop()
		self.assertNotIn('rvsection', log)
		text = p2.getWikiText()
		self.assertIs(len(api.querylog), 1)
		log = api.querylog.pop()
		self.assertIn('rvsection', log)
		self.assertNotEqual(p1.lastedittime, '')

	def test_getHistory(self):
		p1 = page.Page(self.site, "Page")
		api.logging = True
		hist = p1.getHistory(content = False)
		self.assertIs(len(api.querylog), 1)
		log = api.querylog.pop()
		self.assertNotIn('content', log['rvprop'])

	def test_getHistory_no_revs(self):
		p1 = page.Page(self.site, "Page")
		api.logging = True
		hist = p1.getHistory(content = False, user='NotAUser')
		self.assertIs(len(api.querylog), 1)
		self.assertIs(hist[0], None)
		self.assertIs(len(hist), 1)

	def test_getHistoryGen(self):
		p1 = page.Page(self.site, "Page")
		api.logging = True
		for rev in p1.getHistoryGen():
			pass
		self.assertGreater(len(api.querylog), 1)
		log = api.querylog.pop()
		self.assertIn('content', log['rvprop'])

	def test_getLogs(self):
		p1 = page.Page(self.site, "File:Test1.jpg")
		api.logging = True
		log = p1.getLogs(logtype = 'upload', limit=10)
		self.assertIs(len(api.querylog), 1)
		log = api.querylog.pop()
		self.assertEqual(log['letitle'], "File:Test1.jpg")
		self.assertEqual(log['letype'], 'upload')
		self.assertNotIn('leuser', log)

	def test_getLogsGen(self):
		p1 = page.Page(self.site, "File:Test1.jpg")
		api.logging = True
		for log in p1.getLogsGen(logtype='upload', limit=5):
			pass
		self.assertGreater(len(api.querylog), 1)
		log = api.querylog.pop()
		self.assertNotIn('leuser', log)

	def test_edit(self):
		self.site.login('GoodUsername', 'goodpassword')
		p1 = page.Page(self.site, "Anotherpage")
		api.logging = True
		res = p1.edit(text='~~~~', minor=True, watchlist='preferences', badarg='Test', summary='test_edit')
		self.assertEqual(res['edit']['result'], 'Success')
		log1 = api.querylog.pop()
		self.assertEqual(log1['action'], 'query')
		self.assertEqual(log1['meta'], 'tokens')
		log2 = api.querylog.pop()
		self.assertIn('text', log2)
		self.assertIn('minor', log2)
		self.assertEqual(log2['md5'], 'ed790e134796eb704dd092dde146a792')
		self.assertNotIn('section', log2)
		self.assertIn('watchlist', log2)
		self.assertNotIn('badarg', log2)

	def test_move(self):
		self.site.login('GoodUsername', 'goodpassword')
		p1 = page.Page(self.site, "Anotherpage")
		api.logging = True
		res = p1.move(mvto='User:Anotherpage', reason='test_move')
		log1 = api.querylog.pop()
		self.assertEqual(log1['action'], 'query')
		self.assertEqual(log1['meta'], 'tokens')
		log2 = api.querylog.pop()
		self.assertIn('reason', log2)
		self.assertIn('watchlist', log2)
		self.assertEqual(p1.namespace, 2)
		self.assertEqual(p1.title, 'User:Anotherpage')
		self.assertEqual(p1.unprefixedtitle, 'Anotherpage')
		self.assertEqual(p1.urltitle, 'User%3AAnotherpage')
		res = p1.move(mvto='Anotherpage', reason='test_move')
		self.assertIn('move', res)

	def test_protect(self):
		self.site.login('GoodUsername', 'goodpassword')
		p1 = page.Page(self.site, "Talk:Page")
		api.logging = True
		r = {'edit':'autoconfirmed', 'move':'sysop'}
		e = {'edit':'1 week'}
		res = p1.protect(restrictions=r, expirations=e, reason='test_protect')
		log1 = api.querylog.pop()
		self.assertEqual(log1['action'], 'query')
		self.assertEqual(log1['meta'], 'tokens')
		log2 = api.querylog.pop()
		ebits = log2['expiry'].split('|')
		pbits = log2['protections'].split('|')
		self.assertIn('edit=autoconfirmed', pbits)
		self.assertIn('move=sysop', pbits)
		i = pbits.index('edit=autoconfirmed')
		self.assertEqual(ebits[i], '1 week')
		i = pbits.index('move=sysop')
		self.assertEqual(ebits[i], 'indefinite')
		self.assertNotIn('cascade', log2)
		res = p1.protect(restrictions={'edit':'all', 'move':'all'}, reason='test_protect')
		self.assertEqual(len(res['protect']['protections']), 2)
		for prot in res['protect']['protections']:
			if 'edit' in prot:
				self.assertEqual(prot['edit'], '')
			else:
				self.assertEqual(prot['move'], '')

	def test_delete(self):
		self.site.login('GoodUsername', 'goodpassword')
		p1 = page.Page(self.site, "Page to delete")
		p1.edit(text='text')
		api.logging = True
		res = p1.delete(reason='test_delete')
		log1 = api.querylog.pop()
		self.assertEqual(log1['action'], 'query')
		self.assertEqual(log1['meta'], 'tokens')
		log2 = api.querylog.pop()
		self.assertIn('reason', log2)
		self.assertIn('watchlist', log2)
		self.assertIn('delete', res)

	def test_hash(self):
		p1 = page.Page(self.site, 'Page', check=True)
		d = {p1:'Test'}
		p2 = page.Page(self.site, 'Page', check=False)
		self.assertTrue(p2 in d.keys())

	def test_equality(self):
		p1 = page.Page(self.site, 'Page', check=True)
		p2 = page.Page(self.site, 'Page', check=False)
		self.assertEqual(p1, p2)
		site2 = wiki.Wiki('https://en.wikipedia.org/w/api.php')
		p3 = page.Page(site2, 'Page')
		self.assertNotEqual(p1, p3)
		p4 = page.Page(self.site, 'Talk:Page')
		self.assertNotEqual(p1, p4)

class TestCategory(unittest.TestCase):

	def setUp(self):
		# requests causes a bunch of unclosed socket warnings
		warnings.filterwarnings("ignore", category=ResourceWarning)
		self.site = wiki.Wiki('http://localhost/w/api.php')

	def tearDown(self):
		api.logging = False
		api.querylog = api.deque()
		api.resultlog = api.deque()

	def test_getAllMembers(self):
		c = category.Category(self.site, 'Test pages')
		api.logging = True
		members = c.getAllMembers()
		self.assertIsInstance(members[0], page.Page)
		log = api.querylog.pop()
		self.assertNotIn('cmnamespace', log)
		members = c.getAllMembers(namespaces=[3,5])
		self.assertEqual(len(members), 0)
		log = api.querylog.pop()
		self.assertIn('cmnamespace', log)

class TestFile(unittest.TestCase):

	def setUp(self):
		# requests causes a bunch of unclosed socket warnings
		warnings.filterwarnings("ignore", category=ResourceWarning)
		self.site = wiki.Wiki('http://localhost/w/api.php')

	def tearDown(self):
		api.logging = False
		api.querylog = api.deque()
		api.resultlog = api.deque()

	def test_getFileHistory(self):
		f1 = wikifile.File(self.site, "File:Test1.jpg")
		api.logging = True
		hist = f1.getFileHistory(exif = False)
		self.assertIs(len(api.querylog), 1)
		log = api.querylog.pop()
		self.assertNotIn('metadata', log['iiprop'])

	def test_getFileHistoryGen(self):
		f1 = wikifile.File(self.site, "File:Test1.jpg")
		api.logging = True
		for rev in f1.getFileHistoryGen():
			pass
		self.assertGreater(len(api.querylog), 1)
		log = api.querylog.pop()
		self.assertIn('metadata', log['iiprop'])

	def test_getUsage(self):
		f1 = wikifile.File(self.site, 'File:Test1.jpg')
		api.logging = True
		usage = f1.getUsage()
		self.assertIsInstance(usage[0], page.Page)
		log = api.querylog.pop()
		self.assertNotIn('iunamespace', log)
		usage = f1.getUsage(namespaces=[3,5])
		self.assertEqual(len(usage), 0)
		log = api.querylog.pop()
		self.assertIn('iunamespace', log)

	def test_download(self):
		f1 = wikifile.File(self.site, 'File:Test1.jpg')
		loc = f1.download(location = 'Temp.jpg')
		self.assertEqual(loc, 'Temp.jpg')
		self.assertGreater(os.stat(loc).st_size, 8000)
		os.remove(loc)

	def test_upload_badfile(self):
		self.site.login('GoodUsername', 'goodpassword')
		f1 = wikifile.File(self.site, 'File:Test2.jpg')
		with self.assertRaises(wikitools.exceptions.UploadError):
			f1.upload(fileobj=io.BytesIO())
		with self.assertRaises(wikitools.exceptions.UploadError):
			f1.upload(fileobj = 'notafile.jpg')

	def test_upload_warning(self):
		self.site.login('GoodUsername', 'goodpassword')
		f1 = wikifile.File(self.site, 'File:Test1.jpg')
		with self.assertWarns(UserWarning):
			f1.upload(fileobj=open('Test1.jpg', 'rb'))

	def test_upload_good(self):
		self.site.login('GoodUsername', 'goodpassword')
		f1 = wikifile.File(self.site, 'File:Test1.jpg')
		res = f1.upload(fileobj=open('Test1.jpg', 'rb'), ignorewarnings=True)
		self.assertEqual(res['upload']['result'], 'Success')

class TestUser(unittest.TestCase):

	def setUp(self):
		# requests causes a bunch of unclosed socket warnings
		warnings.filterwarnings("ignore", category=ResourceWarning)
		self.site = wiki.Wiki('http://localhost/w/api.php')

	def tearDown(self):
		api.logging = False
		api.querylog = api.deque()
		api.resultlog = api.deque()

	def test_constructor_IP(self):
		api.logging = True
		u1 = user.User(self.site, '123.45.67.89')
		self.assertEqual(len(api.querylog), 0)
		u2 = user.User(self.site, '1:2:3:4:5:6:7:8')
		self.assertEqual(len(api.querylog), 0)
		u3 = user.User(self.site, '123')
		self.assertEqual(len(api.querylog), 1)
		u4 = user.User(self.site, '300.1.1.1')
		self.assertEqual(len(api.querylog), 2)
		self.assertTrue(u1.isIP)
		self.assertTrue(u2.isIP)
		self.assertFalse(u3.isIP)
		self.assertFalse(u4.isIP)

	def test_constructor_notexists(self):
		api.logging = True
		u1 = user.User(self.site, "Doesn't exist")
		self.assertEqual(len(api.querylog), 1)
		self.assertFalse(u1.exists)		

	def test_constructor_blocked(self):
		api.logging = True
		u1 = user.User(self.site, "Vandal1")
		self.assertEqual(len(api.querylog), 1)
		self.assertTrue(u1.blocked)	

	def test_isblocked(self):
		api.logging = True
		u1 = user.User(self.site, "Vandal1", check=False)
		self.assertTrue(u1.isBlocked())
		self.assertEqual(len(api.querylog), 1)
		u1 = user.User(self.site, "Vandal1", check=True)
		self.assertTrue(u1.isBlocked())
		self.assertEqual(len(api.querylog), 2)

	def test_block(self):
		self.site.login('GoodUsername', 'goodpassword')
		u1 = user.User(self.site, "Vandal2")
		api.logging = True
		res = u1.block(reason='test_block', autoblock=False, nocreate=False)
		self.assertEqual(res['block']['expiry'], 'infinite')
		log1 = api.querylog.pop()
		self.assertEqual(log1['action'], 'query')
		self.assertEqual(log1['meta'], 'tokens')
		log2 = api.querylog.pop()
		self.assertNotIn('autoblock', log2)
		self.assertNotIn('nocreate', log2)
		self.assertIn('reason', log2)
		res = u1.unblock()
		self.assertIn('unblock', res)
		self.assertEqual(len(api.querylog), 2)

	def test_getContributions(self):
		u1 = user.User(self.site, "GoodUsername")
		api.logging = True
		contribs = u1.getContributions(limit=10)
		self.assertIs(len(api.querylog), 1)
		c1 = api.querylog.pop()
		self.assertEqual(c1['ucdir'], 'older')

	def test_getContributionsGen(self):
		u1 = user.User(self.site, "GoodUsername")
		api.logging = True
		for log in u1.getContributionsGen(limit=5):
			pass
		self.assertGreater(len(api.querylog), 1)

	def test_hash(self):
		u1 = user.User(self.site, 'GoodUsername', check=True)
		d = {u1:'Test'}
		u2 = user.User(self.site, 'GoodUsername', check=False)
		self.assertTrue(u2 in d.keys())

	def test_equality(self):
		u1 = page.Page(self.site, 'GoodUsername', check=True)
		u2 = page.Page(self.site, 'GoodUsername', check=False)
		self.assertEqual(u1, u2)
		site2 = wiki.Wiki('https://en.wikipedia.org/w/api.php')
		u3 = user.User(site2, 'GoodUsername')
		self.assertNotEqual(u1, u3)

class TestPageList(unittest.TestCase):

	def setUp(self):
		# requests causes a bunch of unclosed socket warnings
		warnings.filterwarnings("ignore", category=ResourceWarning)
		self.site = wiki.Wiki('http://localhost/w/api.php')

	def tearDown(self):
		api.logging = False
		api.querylog = api.deque()
		api.resultlog = api.deque()


	def test_listFromQuery(self):
		params = {'action':'query',
			'list':'allpages'
		}
		req = api.APIRequest(self.site, params)
		res = req.query(False)
		api.logging = True
		pages = pagelist.listFromQuery(self.site, res['query']['allpages'])
		for item in pages:
			self.assertIsInstance(item, page.Page)
			self.assertTrue(item.exists)
		self.assertEqual(len(api.querylog), 0)

	def test_listFromTextList_nocheck(self):
		titles = ['Page', 'Page2', 'Page3']
		api.logging = True
		pages = pagelist.listFromTextList(self.site, sequence=titles, datatype='titles', check=False)
		for item in pages:
			self.assertIsInstance(item, page.Page)
			self.assertIs(item.exists, None)
		self.assertEqual(len(api.querylog), 0)

	def test_listFromTextList_pageids(self):
		pageids = [1, 2, 3, 4, 5]
		api.logging = True
		pages = pagelist.listFromTextList(self.site, sequence=pageids, datatype='pageids', check=True)
		for item in pages:
			self.assertIsInstance(item, page.Page)
			self.assertIsNot(item.exists, None)
		self.assertEqual(len(api.querylog), 1)

	def test_listFromTextList_titles(self):
		titles = ['Page', 'Page2', 'Page3']
		api.logging = True
		pages = pagelist.listFromTextList(self.site, sequence=titles, datatype='titles', check=True)
		for item in pages:
			self.assertIsInstance(item, page.Page)
			self.assertIsNot(item.exists, None)
		self.assertEqual(len(api.querylog), 1)

	def test_listFromTextList_dbkeys(self):
		dbkeys = [(0, 'Page'), (1, 'Page2'), (3, 'Page3')]
		api.logging = True
		pages = pagelist.listFromTextList(self.site, sequence=dbkeys, datatype='dbkeys', check=True)
		for item in pages:
			self.assertIsInstance(item, page.Page)
			self.assertIsNot(item.exists, None)
		self.assertEqual(len(api.querylog), 1)

	def test_makePage_invalid(self):
		result = { 'title':'<>|', 'invalid':'' }
		p = pagelist.makePage(result, self.site, False)
		self.assertIs(p, None)

	def test_makePage_exists(self):
		result = { "pageid": 5, "ns": 0, "title": "Foo" }
		p = pagelist.makePage(result, self.site, False)
		self.assertTrue(p.exists)

	def test_makePage_notexists(self):
		result = { "missing": "", "ns": 0, "title": "Foo" }
		p = pagelist.makePage(result, self.site, False)
		self.assertFalse(p.exists)

	def test_makePage_unsure(self):
		result = { "ns": 0, "title": "Foo" }
		p = pagelist.makePage(result, self.site, False)
		self.assertIs(p.exists, None)


if __name__ == '__main__':
    unittest.main()
