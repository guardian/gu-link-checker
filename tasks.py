import os
import logging
import json
import datetime

from urlparse import urlparse

import webapp2
import jinja2

import configuration
from urllib import quote, urlencode
from google.appengine.api import urlfetch

from google.appengine.ext import ndb


from models import Content, Link, IncomprehensibleLink

from bs4 import BeautifulSoup
from validate_email import validate_email

import reports

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")))

def is_commercial(item):
	return "tone/sponsoredfeatures" in map(lambda p: p["id"], item["tags"])

class CheckRecentContent(webapp2.RequestHandler):
    def get(self):
    	query = {
    		"page-size" : "50",
    		"date-id" : "date/today",
    		"show-fields" : "body",
    		"show-tags" : "all",
    		"use-date" : "last-modified",
    	}

    	api_key = configuration.lookup('CONTENT_API_KEY')

    	if not api_key:
    		self.response.write("No content API key defined")
    		return

    	query['api-key'] = api_key

    	response = urlfetch.fetch('http://content.guardianapis.com/search?%s' % urlencode(query), deadline=7)

    	if response.status_code == 200:
    		payload = json.loads(response.content)
    		if not "ok" in payload.get("response", {}).get("status", "notfound"):
    			self.response.write("Content API did not return a result")
    			return

    		for item in payload["response"].get("results", []):
    			if not 'fields' in item or not 'body' in item['fields']:
    				continue

    			#logging.info(item['fields']['body'])
				
    			lookup_key = ndb.Key('Content', item["id"])
    			content_entry = lookup_key.get()

    			if content_entry:
    				content_entry.body = item['fields']['body']
    				content_entry.commercial = is_commercial(item)
    				content_entry.checked = False
    				content_entry.parse_failed = False
    				content_entry.links_extracted = False

    				for current_link in Link.query(ancestor=content_entry.key):
    					current_link.key.delete()

    				content_entry.put()
    			else:
    				Content(id=item['id'], web_url=item['webUrl'], body= item['fields']['body'], commercial=is_commercial(item)).put()
        self.response.write('Content checked')

class ExtractLinks(webapp2.RequestHandler):
	def get(self):
		template = jinja_environment.get_template('tasks/link-extracting.html')

		unchecked_content = Content.query(Content.links_extracted == False)

		template_values = {
			"unparseable_content" : [],
			"links_extracted" : [],
		}

		def parse_body(item):
			try:
				soup = BeautifulSoup(item.body, "html5lib")
				return soup
			except:
				logging.fatal("Could not parse {0}".format(item.web_url))

			return None

		for item in unchecked_content:
				soup = parse_body(item)
				if not soup:
					template_values["unparseable_content"].append(item)
					item.parse_failed = True
					item.links_extracted = True
					item.put()
					continue

				for link in soup.find_all('a'):
					link_raw_text = str(link)

					href = link.get("href")
					#logging.info(href)

					if not href or len(href) >= 500 or len(link_raw_text) > 500:
						IncomprehensibleLink(parent=item.key, content_url=item.web_url, raw_text=unicode(link.string)).put()
						continue

					template_values['links_extracted'].append(href)
					if href:
						link_record = Link(parent=item.key, link_url=href, raw_text=link_raw_text, commercial=item.commercial, link_text=unicode(link.string))

						link_record.put()

				item.links_extracted = True
				item.put()

		self.response.write(template.render(template_values))

def check_commercial_link(link, parsed_url):

	if "mailto" == parsed_url.scheme:
		return link

	if parsed_url.hostname:
		for internal_host in ["theguardian.com", "guim.co.uk"]:
			if internal_host in parsed_url.hostname:
				return link

	parsed_link = BeautifulSoup(link.raw_text.encode('utf-8'), "html5lib").find('a')
	if link.commercial:
		if not "rel" in parsed_link.attrs.keys() or not "nofollow" in parsed_link.attrs["rel"]:
			link.invalid = True
			parsed_link["rel"] = "nofollow"
			#logging.info(unicode(parsed_link))
			link.fix = "Link should be: {corrected_link}".format(corrected_link=unicode(parsed_link))
			link.error = "Nofollow not applied to sponsored feature link"
			link.no_follow_fail = True
	return link

class CheckLinks(webapp2.RequestHandler):
	def get(self):
		def check_url(url):
			try:
				link_check_result = urlfetch.fetch(url, deadline=9)
				return (200 <= link_check_result.status_code < 400, "Status code {0}".format(link_check_result.status_code), link_check_result.status_code)
			except Exception, e:
				logging.warn(e)
				return (False, "Failed to read the url: {0}".format(e), None)

			return (False, None, None)

		template = jinja_environment.get_template('tasks/link-checking.html')
		template_values = {}

		links_query = Link.query(Link.checked == False, Link.invalid == False)
		links_to_check = links_query.fetch(limit=50)

		valid_links = 0
		invalid_links = 0

		for link in links_to_check:
			#logging.info(link)

			parsed_url = None
			try:
				parsed_url = urlparse(link.link_url)
			except ValueError, ve:
				link.invalid = True
				link.error = "URL had an invalid format"
				link.put()
				continue

			if parsed_url.hostname and "guardian.co.uk" in parsed_url.hostname:
				link.invalid = True
				link.error = "Internal link references the old domain"
				link.fix = "Is there an an alternative location on the new domain?"
				link.put()
				continue

			if link.commercial:
				check_commercial_link(link, parsed_url)

				if link.invalid:
					link.put()
					continue

			if parsed_url.scheme in ["http", "https"]:

				url_to_check = link.link_url

				if "#" in url_to_check:
					url_to_check = url_to_check.split("#")[0]

				(link_status, error_message, link_status_code) = check_url(link.link_url)

				if link_status:
					valid_links += 1
				else:
					invalid_links += 1


				link.checked = True
				link.invalid = not link_status

				if link_status_code:
					link.status_code = link_status_code

				if not link_status: 
					link.error = "Link did not resolve correctly: " + error_message

			if parsed_url.scheme == 'mailto':
				email_valid = validate_email(link.link_url[7:])

				if not email_valid:
					link.invalid = True
					link.error = "Email address did not have a valid structure"


			link.checked = True
			link.put()


		template_values['valid_links'] = valid_links
		template_values['invalid_links'] = invalid_links

		self.response.write(template.render(template_values))


app = webapp2.WSGIApplication([
    ('/tasks/check-recent', CheckRecentContent),
    ('/tasks/extract-links', ExtractLinks),
    ('/tasks/check-links', CheckLinks),
    ('/tasks/reports/email/no-follow', reports.NoFollow),
], debug=True)
