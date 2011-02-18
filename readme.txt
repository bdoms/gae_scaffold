
= Setup GAE Scaffold =

== Things You MUST Modify ==

 * Generate COOKIE_KEY variable in appengine_config.py
 * Replace YOUR_APP_ID in app.yaml
 * Set debug=False in website.py when done with development to disable front-end error reporting
 * Replace YOU@YOUR_DOMAIN.com in templates/terms.html
 * A sample Terms of Service and Privacy Policy have been provided as examples, but you are solely responsible for their content and how they apply to your site


= Continued Use =

 * Add an entry to templates/sitemap.xml for each page you want indexed by search engines
 * Modify static/robots.txt to disallow any pages you don't want crawled
 * Make tests in tests/test_controllers.py for new pages
 * Make tests in tests/test_models.py for new models
 * After updating production, clear memcache via /admin in order to ensure that old pages aren't still cached


= Testing =
    nosetests --with-gae --gae-lib-root=/path/to/gae --tests=tests/


= Using Google App Engine =

== Setup Development Environment (Linux) ==
    Download: http://code.google.com/appengine/downloads.html
    Add the extracted path to PATH var with these lines in .bashrc file:
        export PATH=${PATH}:/path/to/google_appengine/
        export PYTHONPATH=${PYTHONPATH}:/path/to/google_appengine/
    Install nose and webtest (for testing): sudo easy_install nose nosegae webtest

== Run Development Server ==
    dev_appserver.py --debug .
    Local URL: http://localhost:8080/

== Deploy to Production ==
    python lib.gae_deploy rel=static static/c static/j
    Root URL: http://YOUR_APP_ID.appspot.com/

