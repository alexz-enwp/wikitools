#!/usr/bin/python
# -*- coding: utf-8 -*-

from wikitools import *
import inspect
import settings
import os
import os.path
import sys

wikiurl = sys.argv[1]

print "Testing wiki"
site = wiki.Wiki(wikiurl)
print "Site:", str(site), repr(site)
print "Login:", site.login(settings.test, settings.testpass)
print "Login check:", site.isLoggedIn(settings.test)
print "Change maxlag:", site.setMaxlag(7)
print "Change UA:", site.setUserAgent('python-wikitools/test')
for thing in dir(site):
	if not inspect.ismethod(eval("site."+thing)):
		exec("print "+repr(thing+':')+", site."+thing)
		
print "\nTesting page"
p = page.Page(site, title="Wikitools test page")
print "Page: ", str(p), repr(p)
print "Subpage check:", p.canHaveSubpages()
print "Redirect check:", p.isRedir()
print "Talk check:", p.isTalk()
print "Talk page:", p.toggleTalk()
print "Wikitext:", p.getWikiText()
print "Links:", p.getLinks()
print "Protection:", p.getProtection()
print "Templates:", p.getTemplates()
print "Edit token:", p.getToken('edit')
print "Changing section:", p.setSection(section="Test section")
print "Wikitext II:", p.getWikiText()
print "Changing namespace:", p.setNamespace(4)
print "Wikitext III:", p.getWikiText()
print "Links II", p.getLinks()
for thing in dir(p):
	if not inspect.ismethod(eval("p."+thing)):
		exec("print "+repr(thing+':')+", p."+thing)
		
print "\nTesting category"
c = category.Category(site, "Category:Wikitools test page")
print "Category: ", str(c), repr(c)
print "Members I:", c.getAllMembers(namespaces=[4])
print "Members II:", c.getAllMembers()
print "Members III:", c.getAllMembers(namespaces=[4])	
for thing in dir(c):
	if not inspect.ismethod(eval("c."+thing)):
		exec("print "+repr(thing+':')+", c."+thing)
		
print "\nTesting file"
f = wikifile.File(site, "Wikitools test file.jpg")
print "File: ", str(f), repr(f)
print "Usage I:", f.getUsage(namespaces=[4])
print "Usage II:", f.getUsage()
print "Usage III:", f.getUsage(namespaces=[4])
loc = f.download(width=50)
print "Downloaded file thumbnail:", loc
print "File size:", os.path.getsize(loc)
os.remove(loc)
for thing in dir(f):
	if not inspect.ismethod(eval("f."+thing)):
		exec("print "+repr(thing+':')+", f."+thing)

print "\nTesting user"	
u = user.User(site, "Wikitools test")
print "User: ", str(u), repr(u)
for thing in dir(u):
	if not inspect.ismethod(eval("u."+thing)):
		exec("print "+repr(thing+':')+", u."+thing)
		
