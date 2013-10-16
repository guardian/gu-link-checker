import webapp2
import jinja2
import os
import json
import logging
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
	def get(self, category="all"):
		template = jinja_environment.get_template('errors.html')
		
		template_values = {"heading_text" : "Link errors"}

		error_query = Link.query(Link.invalid == True).order(-Link.last_checked)

		def process_link(link):
			content = link.key.parent().get()
			if content:
				link.origin_url = content.web_url

			return link


		template_values['error_links'] = [process_link(e) for e in error_query.fetch()]

		self.response.out.write(template.render(template_values))

app = webapp2.WSGIApplication([
	('/', MainPage),
	('/invalid-links', DisplayInvalidLinksPage),
	('/invalid-links/(\w+)', DisplayInvalidLinksPage),
	],
	debug=True)