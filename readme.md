Copyright &copy; 2011-2014, [Brendan Doms](http://www.bdoms.com/)  
Licensed under the [MIT license](http://www.opensource.org/licenses/MIT)


# Welcome to GAE Scaffold

## Introduction

GAE Scaffold is made so you can simply fill in the blanks to get a new application up and running very quickly.
It "just works" straight out of the box, which includes all tests passing, and no external installations required beyond GAE itself.
To get it running with a production account you'll have to make a few changes described below - these have been minimized as much as possible.
Given that starting point, you can easily modify anything and everything to suit your needs.

## What It Is

GAE Scaffold takes care of a lot of annoying boilerplate so that you write less code.
It provides helper functions to do things like automatically render human readable errors or output JSON.
It also includes a library of Git submodules to handle a wide array of common tasks like deployment, cache-busting, minification, and testing.
GAE Scaffold's included templates use HTML5 with UTF-8 by default.

## What It Isn't

GAE Scaffold does not include a JavaScript or CSS framework.
This is a purposeful decision in order to stay as front-end agnostic as possible.


## Setup

Make sure you have Python and Google App Engine properly installed. Then...

### Get GAE Scaffold

Clone the repository and `--recursive` will get all the required submodules automatically:

```bash
git clone --recursive https://github.com/bdoms/gae_scaffold.git
```

After that to track or save progress to your own repo just change the remote:

```bash
git remote rm origin
git remote add origin http://path.to.you.server/project
```


## Use

### Mandatory Modifications

 * Generate the `secret_key` variable in `website.py` and the `*_PEPPERS` in `config/constants.py` for security
 * Replace `EMAIL_SENDER` in `config/constants.py` with a [valid email address](https://developers.google.com/appengine/docs/python/mail/sendingmail)
 * Replace `your-app-id` in `app.yaml` to upload the application
 * Replace `YOU@YOUR_DOMAIN.com` in `templates/terms.html` for DMCA compliance
 * A sample Terms of Service and Privacy Policy have been provided as examples, but you are solely responsible for their content and how they apply to your site


### Going Forward

 * Escape any untrusted user content you display in templates by using the `|e` filter
 * Add an entry to `templates/sitemap.xml` for each page you want indexed by search engines
 * Modify `config/robots.template.txt` to disallow any pages you don't want crawled (on a per branch basis)
 * Make tests in `tests/test_controllers.py` for new pages
 * Make tests in `tests/test_models.py` for new models
 * After updating production, clear memcache via `/admin` (or the GAE dashboard) in order to ensure that old pages aren't still cached


### Common Commands

#### Run Development Server

```bash
dev_appserver.py --debug .
```

This starts a server running at http://localhost:8080/

#### Run Tests

```bash
python tests
```

#### Deploy to Production

To deploy only the current branch:

```bash
python lib/gae_deploy config/deploy.yaml --oauth2
```

Use the `--branch` (`-b`) option to specify a different branch than the current one to deploy. I.e. `-b master`.

Use the `--list` (`-l`) option to specify a predefined list of branches to deploy all at once. The pre-defined lists are:

 * production
   * master

Note that you must have already created an application on Google App Engine with the matching ID in `app.yaml` for deploying to work.
This then creates a live version of your application at http://your-app-id.appspot.com/

See the readme in `lib/gae_deploy` for more details about deploying.
