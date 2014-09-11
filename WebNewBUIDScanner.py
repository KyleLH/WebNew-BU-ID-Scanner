#!/usr/bin/env python

# by HIROKI OSAME developed with Python v2.7.5

# sudo easy_install beautifulsoup4
from bs4 import BeautifulSoup

# brew install opencv
import cv2.cv as cv

# sudo easy_install https://bitbucket.org/3togo/python-tesseract/downloads/python-tesseract_0.8-3.0-py2.7_macosx-10.9-intel.egg
import tesseract

import sys, re, getpass, urllib, urllib2, cookielib, json

class WebNewBUIDScanner:

	def __init__(self):

		# Setup Tesseract
		self.setUpTesseract()

		#Inquire Credentials
		self.buUn = urllib.quote_plus(raw_input("BU TA Username: "))
		self.buPw = urllib.quote_plus(getpass.getpass("BU TA Password: "))

		#Prepare Session
		self.cj = cookielib.MozillaCookieJar()
		
		#Login
		self.login()


		# Setup OpenCV
		self.setUpOpenCV()

		# Start capture
		while True:

			# Fetch
			img = cv.CreateImage((640, 480), cv.IPL_DEPTH_8U, 1)

			# Gray
			cv.CvtColor(cv.QueryFrame(self.capture), img, cv.CV_BGR2GRAY)

			# Threshold
			# cv.AdaptiveThreshold(img, img, 255, cv.CV_ADAPTIVE_THRESH_MEAN_C, cv.CV_THRESH_BINARY, 11, 6)
			cv.AdaptiveThreshold(img, img, 255, cv.CV_ADAPTIVE_THRESH_MEAN_C, cv.CV_THRESH_BINARY, 9, 7)

			# Display
			cv.ShowImage("Camera", img)

			# OCR
			tesseract.SetCvImage(img, self.api)

			match = re.search(r"(U\d{8})", self.api.GetUTF8Text())
			if match:

				BUID = match.groups()[0]

				print

				# Lookup BUID
				profile = self.lookupBUID(BUID)

				# Prompt for approval
				if profile != False and raw_input("Approve (y/n): ") == "y":
					self.approveBUID(BUID)

			# If Esc is pressed, quit
			if cv.WaitKey(100) == 27: break


	def setUpTesseract(self):
		self.api = tesseract.TessBaseAPI()
		self.api.Init("/usr/local/Cellar/tesseract/3.03-rc1/share", "eng", tesseract.OEM_DEFAULT)
		self.api.SetVariable("tessedit_char_whitelist", "U0123456789")
		self.api.SetPageSegMode(tesseract.PSM_AUTO)


	def setUpOpenCV(self):
		# Setup OpenCV Window
		cv.NamedWindow("Camera", 1)
		self.capture = cv.CreateCameraCapture(0)

		# Width
		cv.SetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_WIDTH, 640)    

		# Height
		cv.SetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_HEIGHT, 480)


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
		if re.search(r'Pending approval data not found for', response):
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

		if re.search(r'Approve completed successfully', response): print "Approved!"
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