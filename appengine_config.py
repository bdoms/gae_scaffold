import os

from google.appengine.api import namespace_manager
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
#    version = os.environ.get('CURRENT_VERSION_ID', '').split(".")[0]
#    if version == "None":
#        return ""
#    else:
#        return version
