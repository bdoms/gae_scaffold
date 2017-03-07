import os

APP_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
VIEW_PATH = os.path.join(APP_PATH, 'views')
LIB_PATH = os.path.join(APP_PATH, 'lib')

# replace this with your own SendGrid API Key
# without it you'll be limited to the App Engine quota (https://cloud.google.com/appengine/docs/quotas#Mail)
# which is only 10 messages per day for free apps or 100 for paid
SENDGRID_API_KEY = ''
SENDER_EMAIL = 'replace.sender@yourdomain.com'
SUPPORT_EMAIL = 'replace.support@yourdomain.com'

PASSWORD_PEPPER = 'replace with the output from os.urandom(64).encode("base64")'
