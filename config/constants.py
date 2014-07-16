# templates
import os

CURRENT_DIR = os.getcwd()
TEMPLATES_PATH = os.path.join(CURRENT_DIR, 'templates')
LIB_PATH = os.path.join(CURRENT_DIR, 'lib')

EMAIL_SENDER = 'replace@yourdomain.com'
AUTH_PEPPER = 'replace with the output from os.urandom(64)'
PASSWORD_PEPPER = 'replace with the output from os.urandom(64)'
RESET_PEPPER = 'replace with the output from os.urandom(64)'
