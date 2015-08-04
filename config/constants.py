# templates
import os

CURRENT_DIR = os.getcwd()
TEMPLATES_PATH = os.path.join(CURRENT_DIR, 'templates')
LIB_PATH = os.path.join(CURRENT_DIR, 'lib')

SENDER_EMAIL = 'replace.sender@yourdomain.com'
SUPPORT_EMAIL = 'replace.support@yourdomain.com'

PASSWORD_PEPPER = 'replace with the output from os.urandom(64)'
RESET_PEPPER = 'replace with the output from os.urandom(64)'
