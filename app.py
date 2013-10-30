import webapp2
import jinja2
import os
import json
import logging
import datetime

from urllib import quote, urlencode
from google.appengine.api import urlfetch

from models import Link

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")))

class MainPage(webapp2.RequestHandler):
	def get(self):
		template = jinja_environment.get_template('index.html')
		
		template_values = {}

		self.response.out.write(template.render(template_values))

class DisplayInvalidLinksPage(webapp2.RequestHandler):
	def get(self, category="all", when="today"):
		template = jinja_environment.get_template('errors.html')
		
		template_values = {
			"heading_text" : "Link errors",
			"today" : True}

		last_24_hours = datetime.datetime.now() - datetime.timedelta(days = 1)

		error_query = Link.query(Link.invalid == True, Link.last_checked >= last_24_hours).order(-Link.last_checked)


		if not when == "today":
			start_date = datetime.datetime.strptime(when, "%Y-%m-%d")
			next_day = datetime.timedelta(days=1)
			end_date = start_date + next_day

			error_query = Link.query(Link.invalid == True, Link.last_checked >= start_date, Link.last_checked <= end_date).order(-Link.last_checked)

			template_values["today"] = False

		if category == "commercial":
			error_query = error_query.filter(Link.commercial == True)

		def process_link(link):
			content = link.key.parent().get()
			if content:
				link.origin_url = content.web_url
				link.edit_url = content.web_url.replace("www.theguardian.com", "www.guprod.gnl")

			if link.last_checked:
				link.last_checked_text = link.last_checked.strftime('%Y-%m-%d %H:%M:%S')

			return link


		template_values['error_links'] = [process_link(e) for e in error_query.fetch()]

		self.response.out.write(template.render(template_values))

app = webapp2.WSGIApplication([
	('/', MainPage),
	('/invalid-links', DisplayInvalidLinksPage),
	('/invalid-links/(\w+)', DisplayInvalidLinksPage),
	('/invalid-links/(\w+)/(\d{4}-\d{2}-\d{2})', DisplayInvalidLinksPage),
	],
	debug=True)