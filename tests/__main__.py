
import os
import sys
import unittest

os.environ["SERVER_SOFTWARE"] = "DevelopmentTesting"

test_path = sys.argv[0]
sdk_path = sys.argv[1]

sys.path.insert(0, sdk_path)
import dev_appserver
dev_appserver.fix_sys_path()

# fix_sys_path removes the current working directory, so we add it back in
sys.path.append('.')

# needed to be able to import the third party libraries
from config.constants import LIB_PATH
sys.path.append(LIB_PATH)
sys.path.append(os.path.join(LIB_PATH, 'webtest'))

suite = unittest.loader.TestLoader().discover(test_path)
unittest.TextTestRunner(verbosity=2).run(suite)
