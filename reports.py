import datetime
import logging
import re

import webapp2

from google.appengine.api import mail

from models import Link
import configuration
import headers

def link_detail(link_data):
	return "  Anchor text: {anchor_text}\n  Link: {link}\n\n".format(anchor_text=link_data.link_text.encode('utf-8'),link=link_data.link_url.encode('utf-8'))

def display_date(ds):
	logging.info(ds)
	if not ds:
		return None
	return datetime.datetime(*map(int, re.split('[^\d]', ds)[:-1])).strftime('%d/%m/%Y')

class NoFollow(webapp2.RequestHandler):
	def get(self):
		now = datetime.datetime.now()
		last_24_hours = now - datetime.timedelta(days = 1)

		error_query = Link.query(Link.invalid == True, Link.commercial == True, Link.last_checked >= last_24_hours).order(-Link.last_checked)

		no_follow_errors = [error for error in error_query if error.no_follow_fail]

		content = "No nofollow errors found"

		errors_present = len(no_follow_errors) > 0

		if errors_present:
			source_urls = set([e.key.parent().get().web_url for e in no_follow_errors])
			lines = ["Summary: {total_errors} nofollow errors found from {source_no} sources\n\n".format(total_errors=len(no_follow_errors), source_no=len(source_urls))]

			for source_url in source_urls:
				lines.append("Source: {source}\n".format(source=source_url))
				errors = [e for e in no_follow_errors if source_url == e.key.parent().get().web_url]
				content = errors[0].key.parent().get()

				if content and content.published_timestamp and content.modified_timestamp:
					lines.append("  Publication date: {pub_date}; last updated: {last_updated}\n".format(pub_date=display_date(content.published_timestamp), last_updated=display_date(content.modified_timestamp)))

				error_details = map(link_detail, errors)
				lines.append("  Contains {error_total} errors\n\n".format(error_total=len(error_details)))
				lines.extend(error_details)

			lines.append("\n")

			content = "".join(lines)

		report_recipients = configuration.lookup("REPORT_EMAILS").split(",")

		if errors_present:
			message = mail.EmailMessage(sender="robert.rees@guardian.co.uk",
				subject="No follow report for {date}".format(date=now.strftime("%d %b %Y")),
				to=report_recipients,
				body=content,)
			message.send()

		headers.text(self.response)
		self.response.write(content)

class BadLinks(webapp2.RequestHandler):
	def get(self):
		now = datetime.datetime.now()
		last_hour = now - datetime.timedelta(hours = 1)

		error_query = Link.query(Link.actionable == True, Link.last_checked >= last_hour).order(-Link.last_checked)

		errors = [error for error in error_query]
		#logging.info(errors)

		content = "No bad link errors found"

		errors_present = len(errors) > 0

		if errors_present:
			source_urls = set([e.key.parent().get().web_url for e in errors])
			lines = ["Summary: {total_errors}  errors found from {source_no} pieces of content\n\n".format(total_errors=len(errors), source_no=len(source_urls))]

			for source_url in source_urls:
				lines.append("Source: {source}\n".format(source=source_url))
				errors_for_url = [link_detail(e) for e in errors if source_url == e.key.parent().get().web_url]
				lines.append("    Contains {error_total} errors\n\n".format(error_total=len(errors_for_url)))
				lines.extend(errors_for_url)

			lines.append("\n")

			content = "".join(lines)

		report_recipients = configuration.lookup("BAD_CONTENT_EMAILS").split(",")

		if errors_present:
			message = mail.EmailMessage(sender="robert.rees@guardian.co.uk",
				subject="Bad link report for {date}".format(date=now.strftime("%d %b %Y %H:%m")),
				to=report_recipients,
				body=content,)
			message.send()

		headers.text(self.response)
		self.response.write(content)
