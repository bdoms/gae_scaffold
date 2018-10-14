import argparse
import os
import sys
import unittest

try:
    import dev_appserver
except ImportError as e:
    raise ImportError('App Engine must be in PYTHONPATH.')
    sys.exit()

dev_appserver.fix_sys_path()

# fix_sys_path removes the current working directory, so we add it back in
sys.path.append('.')
sys.path.append(os.path.join('lib', 'testing', 'webtest'))

# import and run config so this env matches the normal one
import appengine_config # NOQA: E402
(appengine_config)

# this needs to be added to the virtualenv like a vendor in order to be found
appengine_config.vendor.add(os.path.join('lib', 'testing'))

# must come after pip is added above
from flake8.main import application # NOQA: E402


def lint():
    # cli options at http://flake8.pycqa.org/en/latest/user/options.html
    # error code definitions at https://pep8.readthedocs.io/en/latest/intro.html
    print 'Running linter...'
    app = application.Application()
    app.run([
        '--exclude=.git,lib,static,views',
        '--ignore=E128,E261,W503',
        '--max-line-length=120',
        '.',
    ])
    print 'Linting complete.'


def unit():
    test_path = sys.argv[-1]
    loader = unittest.loader.TestLoader()
    if test_path.endswith('.py'):
        # support testing only a single file, called like `python tests path/to/test.py`
        suite = loader.loadTestsFromName(test_path.replace(os.sep, '.').replace('.py', ''))
    else:
        suite = loader.discover('tests')

    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
    # parse command line arguments
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-l', '--lint', action='store_true', help='only run the linter')
    group.add_argument('-u', '--unit', action='store_true', help='only run unit tests')
    args = parser.parse_args()

    if args.lint:
        lint()
    elif args.unit:
        unit()
    else:
        lint()
        unit()
