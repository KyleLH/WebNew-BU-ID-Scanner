#!/usr/bin/env python

# by HIROKI OSAME developed with Python v2.7.5

from bs4 import BeautifulSoup

import sys, re, getpass, urllib, urllib2, cookielib, json

class WebNewBUIDScanner:

	def __init__(self):

		try:
			"""
			Try to get credentials from .auth -- expected format of this file is:

			```
			username
			password
			```
			"""
			f = open(".auth", "r")
			self.buUn = f.readline().rstrip()
			self.buPw = f.readline().rstrip()
		except IOError:
			#Inquire Credentials
			self.buUn = urllib.quote_plus(raw_input("BU TA Username: "))
			self.buPw = urllib.quote_plus(getpass.getpass("BU TA Password: "))

		#Prepare Session
		self.cj = cookielib.MozillaCookieJar()

		#Login
		self.login()

		# Wait for input
		while True:

			# get BUID
			raw = getpass.getpass("Please swipe card, or type 'quit' to exit")
			if raw in [ "quit", "" ]:
				break

			match = re.search(r";1([^\^]*)", raw)
			if match:

				BUID =  "U" + match.groups()[0]

				# Lookup BUID
				profile = self.lookupBUID(BUID)

				# Prompt for approval
				if profile != False and raw_input("Approve (y/n): ") == "y":
					self.approveBUID(BUID)

	def login(self):
		print "Logging in...",
		getSession = self.httpReq("https://www.bu.edu/login")
		attempt =	self.httpReq(
						"https://weblogin.bu.edu//web@login3?jsv=1.5p&br=un&fl=0",
						"https://weblogin.bu.edu//web@login3?jsv=1.5p&br=un&fl=0",
						"p=&act=up&js=yes&jserror=&c2f=&r2f=&user="+self.buUn+"&pw="+self.buPw
					)

		if re.search("Weblogin complete; waiting for application.", attempt):

			# Parse Auth Token
			self.auth = next((i.value for i in self.cj if i.name == 'weblogin3'), 0)

			print "Success!"

		else:
			sys.exit("Error: Login Failed")


	def lookupBUID(self, BUID):
		req = urllib.urlencode({
			"_authref": self.auth,
			"template_extension": "useradm",
			"_hostname": "ph",
			"query_string": "template_extension=useradm",
			"_next_f": "bulogin_approve::handle_approve",
			"_current_f": "bulogin_approve::output_approve",
			"_acls": "approve=cs",
			"_bu_id": BUID,
			"submit_button": "Continue"
		})

		print "Looking up %s ... "%BUID,

		response = self.httpReq("https://weblogin.bu.edu/accounts/bulogin-approve", False, req)

		table = BeautifulSoup(response).table.contents[9].table

		form = table.find('table', attrs={'align':'center'})

		if form == None:
			print "Doesn't exist!"
			return False

		print "Found!"

		# Parse Profile and print
		profile = { i.font.text.strip()[:-1] : i.strong.text for i in form.findAll('tr') }
		print json.dumps(profile, sort_keys=True, indent=4)

		# Check pending Approval
		if re.search("Pending approval data not found for", response):
			print "No pending approval data found for %s"%BUID
			return False

		# Approvable
		if table.find('input', attrs={'name':'approve_button'}) == None:
			print "Unapprovable"
			return False

		return True


	def approveBUID(self, BUID):

		req = urllib.urlencode({
			"_authref": self.auth,
			"template_extension": "useradm",
			"_hostname": "ph",
			"query_string": "template_extension=useradm",
			"_next_f": "bulogin_approve::handle_approve",
			"_current_f": "bulogin_approve::output_approve",
			"_acls": "approve=cs",
			"_bu_id": BUID,
			"cs_cs-ad-cs": "yes",
			"approve_button": "Approve"
		})

		print "Approving %s ... "%BUID,

		response = self.httpReq("https://weblogin.bu.edu/accounts/bulogin-approve", False, req)

		if re.search("Approve completed successfully", response): print "Approved!"
		else: print "Failed!", response


	def httpReq(self, url, referer=False, post=None):

		handlers = [
			urllib2.HTTPHandler(),
			urllib2.HTTPSHandler(),
			urllib2.HTTPCookieProcessor(self.cj),
		]

		opener = urllib2.build_opener(*handlers)
		urllib2.install_opener(opener)

		#Build Request
		req = urllib2.Request(url, post)

		#Set User Agent
		req.add_header('User-Agent', "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:22.0) Gecko/20100101 Firefox/22.0")

		#Add Referer
		if referer!=False:
			req.add_header('Referer', referer)

		#Add Post
		if post!=None:
			req.add_header('Connection', 'keep-alive')
			req.add_header('Content-type', 'application/x-www-form-urlencoded')

		handle = None

		try:
			handle = urllib2.urlopen(req)
		except IOError, e:
			print 'We failed to open "%s".' % url
			if hasattr(e, 'code'):
				print 'Error code - %s.' % e.code
		else:
			if 'handle' != None:
				try:
					source = handle.read()
				except Exception as e:
					print("Error! "+str(e))
				else:
					return source


WebNewBUIDScanner()
