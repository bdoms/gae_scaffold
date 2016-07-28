# templates
import os

APP_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TEMPLATES_PATH = os.path.join(APP_PATH, 'templates')
LIB_PATH = os.path.join(APP_PATH, 'lib')

SENDER_EMAIL = 'replace.sender@yourdomain.com'
SUPPORT_EMAIL = 'replace.support@yourdomain.com'

PASSWORD_PEPPER = 'replace with the output from os.urandom(64)'
RESET_PEPPER = 'replace with the output from os.urandom(64)'
