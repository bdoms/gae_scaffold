
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.join(CURRENT_DIR, 'lib', 'webtest'))
sys.path.append(os.path.join(CURRENT_DIR, 'lib', 'nose'))
sys.path.append(os.path.join(CURRENT_DIR, 'lib', 'nosegae'))

import nose
import nosegae


if __name__ == '__main__':
    nose.run(argv=sys.argv, addplugins=[nosegae.NoseGAE()])

