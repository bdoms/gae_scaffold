
= Welcome to GAE Scaffold =

== Introduction ==
    GAE Scaffold is made so you can simply fill in the blanks to get a new application up and running very quickly.
    It "just works" straight out of the box, which includes all tests passing, and no external installations required beyond GAE itself.
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

== Get Python ==
    You need something in the 2.X line, and at least 2.5.
    Download and install: http://www.python.org/download/


== Get Google App Engine ==
    Download: http://code.google.com/appengine/downloads.html
    Extract it somewhere memorable. And you probably want to add its location to your path:
        export PATH=${PATH}:/path/to/google_appengine/
        export PYTHONPATH=${PYTHONPATH}:/path/to/google_appengine/


== Get GAE Scaffold ==

    === Option 1: Download ===
        You can simply download the source code from GitHub, but none of the submodules will be included and you'll have to manually download and extract them to the proper directories.

    === Option 2: Clone ===
        Using Git (http://git-scm.com/download) you can clone the repository and --recursive will get all the required submodules automatically:
            git clone --recursive https://github.com/bdoms/gae_scaffold.git

        After that, if you want to track or save progress to your own server, then just change the remote:
            git remote rm origin
            git remote add origin http://path.to.you.server/project

        This is the simplest and easiest method, but requires that GAE Scaffold be used as the basis for a new project, which is its intended use.

    === Option 3: Subtree Merge
        If you already have an existing Git repository and you want to integrate this into the same project, then you should do what's called a subtree merge:

            git remote add -f gae_scaffold https://github.com/bdoms/gae_scaffold.git
            git merge --squash -s ours --no-commit gae_scaffold/master
            git read-tree --prefix=YOUR_SUBDIRECTORY/ -u gae_scaffold/master
            git commit -m "Merged subtree from gae_scaffold."

        You now have to do some manual editing to get the submodules to work correctly.
        First, copy (or integrate into the existing) .gitmodules file to the top level directory, as it won't work anywhere else:

            git cp YOUR_SUBDIRECTORY/.gitmodules .gitmodules

        Then edit the paths in it to properly reference the subdirectory:

            [submodule "lib/submodule"] -> [submodule "YOUR_SUBDIRECTORY/lib/submodule"]
            	path = lib/submodule -> path = YOUR_SUBDIRECTORY/lib/submodule

        Now you can safely get the submodules up and running:

            git submodule init
            git submodule update
            git commit -m "Added submodules from gae_scaffold."

        Finally, to get updates that are pushed to GAE Scaffold, you can run this:

            git pull --squash -s subtree gae_scaffold master

    === As a Submodule ===
        Using GAE Scaffold itself as a submodule directly is NOT recommended, as you are required to make changes that will never be pushed back to the original remote.
        However, cloning into a new repository (as in Option 2) and then using that as a submodule should work as intended.


= Use =

== Mandatory Modifications ==

 * Generate `COOKIE_KEY` variable in `appengine_config.py` for session security
 * Replace `your-app-id` in `app.yaml` to upload the application
 * Set `debug=False` in `website.py` when done with development to disable front-end error reporting
 * Replace `YOU@YOUR_DOMAIN.com` in `templates/terms.html` for DMCA compliance
 * A sample Terms of Service and Privacy Policy have been provided as examples, but you are solely responsible for their content and how they apply to your site


== Going Forward ==

 * Add an entry to `templates/sitemap.xml` for each page you want indexed by search engines
 * Modify `static/robots.txt` to disallow any pages you don't want crawled
 * Make tests in `tests/test_controllers.py` for new pages
 * Make tests in `tests/test_models.py` for new models
 * After updating production, clear memcache via /admin in order to ensure that old pages aren't still cached


== Common Commands ==

=== Run Development Server ===
    dev_appserver.py --debug .
    Local URL: http://localhost:8080/

=== Deploy to Production ===
    python lib/gae_deploy rel=static static/c static/j
    Live URL: http://YOUR_APP_ID.appspot.com/

=== Run Tests ===
    python test.py --with-gae --gae-lib-root=/path/to/gae --tests=tests/

