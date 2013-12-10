import datetime
import logging

import webapp2

from google.appengine.api import mail

from models import Link
import configuration
import headers

def link_detail(link_data):
	return "  Anchor text: {anchor_text}\n  Link: {link}\n\n".format(anchor_text=link_data.link_text,link=link_data.link_url)

class NoFollow(webapp2.RequestHandler):
	def get(self):
		now = datetime.datetime.now()
		last_24_hours = now - datetime.timedelta(days = 1)

		error_query = Link.query(Link.invalid == True, Link.commercial == True, Link.last_checked >= last_24_hours).order(-Link.last_checked)

		no_follow_errors = [error for error in error_query if "nofollow" in error.error.lower()]

		content = "No nofollow errors found"

		errors_present = len(no_follow_errors) > 0

		if errors_present:
			source_urls = set([e.key.parent().get().web_url for e in no_follow_errors])
			lines = ["Summary: {total_errors} nofollow errors found from {source_no} sources\n\n".format(total_errors=len(no_follow_errors), source_no=len(source_urls))]

			for source_url in source_urls:
				lines.append("Source: {source}\n".format(source=source_url))
				errors = [link_detail(e) for e in no_follow_errors if source_url == e.key.parent().get().web_url]
				lines.append("  Contains {error_total} errors\n\n".format(error_total=len(errors)))
				lines.extend(errors)

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
