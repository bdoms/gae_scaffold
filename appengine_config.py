import os

from google.appengine.ext import vendor

from config.constants import LIB_PATH

vendor.add(LIB_PATH)
vendor.add(os.path.join(LIB_PATH, 'python-http-client'))
vendor.add(os.path.join(LIB_PATH, 'sendgrid-python'))
vendor.add(os.path.join(LIB_PATH, 'httpagentparser'))
vendor.add(os.path.join(LIB_PATH, 'gcs', 'python', 'src'))

# uncomment this to make each version use its own namespace (which segregates the datastore)
# called only if the current namespace is not set
# def namespace_manager_default_namespace_for_request():
#     # versions for things we name are like "name.1234567890"
#     # default versions are in the format YYYYMMDDtHHMMSS
#     version = os.environ.get('CURRENT_VERSION_ID', '1').split('.')[0]
#     if version[0].isdigit() or version == 'None':
#         # the latter None case happens on local development
#         return ''
#     else:
#         return version
