from google.appengine.ext import ndb

class Configuration(ndb.Model):
	key = ndb.StringProperty()
	value = ndb.StringProperty()

class Content(ndb.Model):
	web_url = ndb.StringProperty(required=True)
	body = ndb.TextProperty(required=True)
	commercial = ndb.BooleanProperty(required=True, default=False)
	date_seen = ndb.DateTimeProperty(auto_now=True)
	checked = ndb.BooleanProperty(default=False)
	links_extracted = ndb.BooleanProperty(default=False)
	parse_failed = ndb.BooleanProperty(default=False)

class Link(ndb.Model):
	link_url = ndb.StringProperty(required=True)
	checked = ndb.BooleanProperty(default=False)
	last_checked = ndb.DateTimeProperty(auto_now=True)
	invalid = ndb.BooleanProperty(default=False)
	error = ndb.StringProperty()
	commercial = ndb.BooleanProperty(default=False)
	raw_text = ndb.StringProperty()
	link_text = ndb.StringProperty()
	status_code = ndb.IntegerProperty()
	fix = ndb.StringProperty()
	fix_text = ndb.TextProperty()
	no_follow_fail = ndb.BooleanProperty(default=False)
	actionable = ndb.BooleanProperty(default=False)

class IncomprehensibleLink(ndb.Model):
	content_url = ndb.StringProperty(required=True)
	raw_text = ndb.TextProperty(required=True)