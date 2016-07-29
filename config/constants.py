# templates
import os

APP_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TEMPLATES_PATH = os.path.join(APP_PATH, 'templates')
LIB_PATH = os.path.join(APP_PATH, 'lib')
PHC_PATH = os.path.join(LIB_PATH, 'python-http-client')
SENDGRID_PATH = os.path.join(LIB_PATH, 'sendgrid-python')
HAP_PATH = os.path.join(LIB_PATH, 'httpagentparser')

# replace this with your own SendGrid API Key
# without it you'll be limited to the App Engine quota (https://cloud.google.com/appengine/docs/quotas#Mail)
# which is only 10 messages per day for free apps or 100 for paid
SENDGRID_API_KEY = ''
SENDER_EMAIL = 'replace.sender@yourdomain.com'
SUPPORT_EMAIL = 'replace.support@yourdomain.com'

PASSWORD_PEPPER = 'replace with the output from os.urandom(64)'
RESET_PEPPER = 'replace with the output from os.urandom(64)'
