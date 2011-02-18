
= Welcome to GAE Scaffold =

== Introduction ==
    GAE Scaffold is made so you can simply fill in the blanks to get a new application up and running very quickly.
    It "just works" straight out of the box, which includes all tests passing, and no external installations required.
    To get it running with a production account you'll have to make a few changes described below - these have been minimized as much as possible.
    Given that starting point, you can easily modify anything and everything to suit your needs.


== What It Is ==
    GAE Scaffold takes care of a lot of annoying boilerplate so that you write less code.
    It provides helper functions to do things like automatically render human readable errors or output JSON.
    It also includes a library of Git submodules to handle a wide array of common tasks like sessions, cache-busting, minification, and testing.
    GAE Scaffold's included templates use HTML5 with UTF-8 by default.


== What It Isn't ==
    GAE Scaffold does not include a JavaScript or CSS framework.
    This is a purposeful decision in order to stay as front-end agnostic as possible.



= Setup =

== Get Google App Engine ==
    Download: http://code.google.com/appengine/downloads.html
    Extract it somewhere memorable


== Mandatory Modifications ==

 * Generate `COOKIE_KEY` variable in `appengine_config.py` for session security
 * Replace `your-app-id` in `app.yaml` to upload the application
 * Set `debug=False` in `website.py` when done with development to disable front-end error reporting
 * Replace `YOU@YOUR_DOMAIN.com` in `templates/terms.html` for DMCA compliance
 * A sample Terms of Service and Privacy Policy have been provided as examples, but you are solely responsible for their content and how they apply to your site


== Continued Use ==

 * Add an entry to `templates/sitemap.xml` for each page you want indexed by search engines
 * Modify `static/robots.txt` to disallow any pages you don't want crawled
 * Make tests in `tests/test_controllers.py` for new pages
 * Make tests in `tests/test_models.py` for new models
 * After updating production, clear memcache via /admin in order to ensure that old pages aren't still cached


== Common Commands ==

=== Run Development Server ===
    python /path/to/gae/dev_appserver.py --debug .
    Local URL: http://localhost:8080/

=== Deploy to Production ===
    python lib/gae_deploy rel=static static/c static/j
    Live URL: http://YOUR_APP_ID.appspot.com/

=== Run Tests ===
    python nosetests --with-gae --gae-lib-root=/path/to/gae --tests=tests/



== Setup Development Environment (Linux) ==
    Add the extracted GAE path to PATH var with these lines in .bashrc file:
        export PATH=${PATH}:/path/to/google_appengine/
        export PYTHONPATH=${PYTHONPATH}:/path/to/google_appengine/
    Install nose and webtest (for testing): sudo easy_install nose nosegae webtest

