import os

APP_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
VIEWS_PATH = os.path.join(APP_PATH, 'views')
LIB_PATH = os.path.join(APP_PATH, 'lib')

# Auth
PASSWORD_PEPPER = os.environ.get('PASSWORD_PEPPER', 'replace with the output from os.urandom(64).encode("base64")')
SESSION_KEY = os.environ.get('SESSION_KEY', 'replace with the output from os.urandom(64).encode("base64")')

# SendGrid
# replace this with your own SendGrid API Key
# without it you'll be limited to the App Engine quota (https://cloud.google.com/appengine/docs/quotas#Mail)
# which is only 10 messages per day for free apps or 100 for paid
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'replace.sender@yourdomain.com')
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'replace.support@yourdomain.com')
