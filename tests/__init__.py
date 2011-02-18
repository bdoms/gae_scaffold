import os


def setUp():
    """ setup for all tests """

    # this is necessary until NoseGAE fixes the fact that they're not figured out dynamically (their issue #20 or #32)
    os.environ['SERVER_NAME'] = 'localhost'
    os.environ['SERVER_PORT'] = '80'

    # this is for detecting the debug state during testing
    os.environ['SERVER_SOFTWARE'] = 'DevelopmentTesting'

def tearDown():
    """ teardown for all tests """

    pass

