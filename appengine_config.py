from google.appengine.ext import vendor
from config.constants import LIB_PATH, PHC_PATH, SENDGRID_PATH, HAP_PATH

vendor.add(LIB_PATH)
vendor.add(PHC_PATH)
vendor.add(SENDGRID_PATH)
vendor.add(HAP_PATH)
