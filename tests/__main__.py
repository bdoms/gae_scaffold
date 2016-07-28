import os
import sys
import unittest

try:
    import dev_appserver
except ImportError, e:
    raise ImportError, "App Engine must be in PYTHONPATH."
    sys.exit()

dev_appserver.fix_sys_path()

# fix_sys_path removes the current working directory, so we add it back in
sys.path.append('.')

# import and run config so this env matches the normal one
import appengine_config
(appengine_config)

test_path = sys.argv[-1]
loader = unittest.loader.TestLoader()
if test_path.endswith('.py'):
    # support testing only a single file, called like `python tests path/to/test.py`
    suite = loader.loadTestsFromName(test_path.replace(os.sep, '.').replace('.py', ''))
else:
    suite = loader.discover(test_path)

unittest.TextTestRunner(verbosity=2).run(suite)
