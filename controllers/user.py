from datetime import datetime, timedelta

from google.appengine.api import images
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

from base import BaseController, FormController, withUser, withoutUser, testDispatch
import model

import cloudstorage as gcs
from gae_validators import validateRequiredString, validateRequiredEmail, validateBool
import httpagentparser

IMAGE_TYPES = ["gif", "jpg", "jpeg", "png"]
SESSION_MAX_AGE = 86400 * 14 # two weeks in seconds


class BaseLoginController(FormController):

    def login(self, user, new=False, remember=False):
        ua = self.request.headers.get('User-Agent', '')
        ip = self.request.remote_addr or ''

        # reject a login attempt without a user agent or IP address
        if not ua or not ip:
            self.flash('error', 'Invalid client.')
            return self.redirect("/user/login")

        auth = None
        if not new:
            auth = user.getAuth(ua)

        if auth:
            # note that this triggers the last login auto update
            auth.ip = ip
            auth.put()
        else:
            parsed = httpagentparser.detect(ua)
            os = browser = device = ''
            if 'os' in parsed:
                # shows up as Linux for Android, Mac OS for iOS
                os = parsed['os']['name']
            if 'browser' in parsed:
                browser = parsed['browser']['name']
            if 'dist' in parsed:
                # "dist" stands for "distribution" - like Android, iOS
                device = parsed['dist']['name']
            auth = model.Auth(user_agent=ua, os=os, browser=browser, device=device, ip=ip, parent=user.key)
            auth.put()

        cookie_args = self.session_store.config['cookie_args']
        if remember:
            cookie_args['max_age'] = SESSION_MAX_AGE
        else:
            # this may seem redundant but the other setting can persist so we must explicitly set this
            cookie_args['max_age'] = None
        self.session.setdefault('cookie_args', cookie_args)

        self.session['auth_key'] = auth.key.urlsafe()
        self.redirect("/home")


class IndexController(blobstore_handlers.BlobstoreUploadHandler, FormController):

    # TODO: need a serving URL for non-image files and this should work in prod
    #self.user.pic_url = 'https://' + self.gcs_bucket + '.storage.googleapis.com/' + rel_path

    @testDispatch
    @withUser
    def get(self):

        self.renderTemplate('user/index.html')

    @testDispatch
    @withUser
    def post(self):

        if self.request.get('delete'):
            if self.user.pic_gcs:
                path = self.user.pic_gcs
                if path.startswith('/gs/'):
                    path = path[3:]
                gcs.delete(path)
            if self.user.pic_blob:
                blobstore.delete(self.user.pic_blob)
            if self.user.pic_url:
                images.delete_serving_url(self.user.pic_url)
            
            self.user.pic_gcs = None
            self.user.pic_blob = None
            self.user.pic_url = None
        else:
            errors = {}
            uploads = self.get_uploads()
            for upload in uploads:
                # enforce file type based on extension
                name, ext = upload.filename.rsplit(".", 1)
                ext = ext.lower()
                if ext not in IMAGE_TYPES:
                    upload.delete()
                    errors = {'type': True}
                    continue

                # note that this serving URL supports size and crop query params
                self.user.pic_gcs = upload.gs_object_name
                self.user.pic_blob = upload.key()
                self.user.pic_url = images.get_serving_url(upload, secure_url=True)
        
            if errors:
                return self.redisplay({}, errors)

        self.user.put()
        self.uncache(self.user.slug)
        self.redisplay()


class AuthsController(FormController):

    @withUser
    def get(self):

        auths = self.user.auths
        current_auth_key = self.session['auth_key']

        self.renderTemplate('user/auths.html', auths=auths, current_auth_key=current_auth_key)

    @withUser
    def post(self):

        str_key = self.request.get('auth_key')

        try:
            auth_key = model.ndb.Key(urlsafe=str_key)
        except:
            self.flash('error', 'Invalid session.')
        else:
            if auth_key.parent() != self.user.key:
                return self.renderError(403)
            else:
                self.uncache(str_key)
                auth_key.delete()
                self.flash('success', 'Access revoked.')

        self.redisplay()


class EmailController(FormController):

    FIELDS = {"email": validateRequiredEmail, "password": validateRequiredString}

    @withUser
    def get(self):

        self.renderTemplate('user/email.html')

    @withUser
    def post(self):
        
        form_data, errors, valid_data = self.validate()

        hashed_password = model.User.hashPassword(valid_data["password"], self.user.password_salt)
        if hashed_password != self.user.hashed_password:
            errors["match"] = True

        # extra validation to make sure that email address isn't already in use
        if not errors:
            user = model.User.getByEmail(valid_data["email"])
            if user:
                errors["exists"] = True

        if errors:
            del form_data["password"] # never send password back for security
            self.redisplay(form_data, errors)
        else:
            self.user.email = valid_data["email"]
            self.user.put()
            self.uncache(self.user.slug)

            self.flash("success", "Email changed successfully.")
            self.redirect("/user")


class PasswordController(FormController):

    FIELDS = {"password": validateRequiredString, "new_password": validateRequiredString}

    @withUser
    def get(self):

        self.renderTemplate('user/password.html')

    @withUser
    def post(self):
        
        form_data, errors, valid_data = self.validate()

        hashed_password = model.User.hashPassword(valid_data["password"], self.user.password_salt)
        if hashed_password != self.user.hashed_password:
            errors["match"] = True

        if errors:
            del form_data["password"]
            del form_data["new_password"]
            self.redisplay(form_data, errors)
        else:
            password_salt, hashed_password = model.User.changePassword(valid_data["new_password"])
            
            self.user.populate(password_salt=password_salt, hashed_password=hashed_password)
            self.user.put()
            self.uncache(self.user.slug)

            self.flash("success", "Password changed successfully.")
            self.redirect("/user")


class SignupController(BaseLoginController):

    FIELDS = {
        "first_name": validateRequiredString,
        "last_name": validateRequiredString,
        "email": validateRequiredEmail,
        "password": validateRequiredString
    }

    @withoutUser
    def get(self):

        self.renderTemplate('user/signup.html')

    @withoutUser
    def post(self):
        
        form_data, errors, valid_data = self.validate()

        # extra validation to make sure that email address isn't already in use
        if not errors:
            user = model.User.getByEmail(valid_data["email"])
            if user:
                errors["exists"] = True

        if errors:
            del form_data["password"] # never send password back for security
            self.redisplay(form_data, errors)
        else:
            password_salt, hashed_password = model.User.changePassword(valid_data["password"])
            del valid_data["password"]
            user = model.User(password_salt=password_salt, hashed_password=hashed_password, **valid_data)
            user.put()
            self.flash("success", "Thank you for signing up!")
            self.login(user, new=True)


class LoginController(BaseLoginController):

    FIELDS = {"email": validateRequiredEmail, "password": validateRequiredString, "remember": validateBool}

    @withoutUser
    def get(self):

        self.renderTemplate('user/login.html')

    @withoutUser
    def post(self):
        
        form_data, errors, valid_data = self.validate()

        # check that the user exists and the password matches
        user = None
        if not errors:
            user = model.User.getByEmail(valid_data["email"])
            if user:
                hashed_password = model.User.hashPassword(valid_data["password"], user.password_salt)
                if hashed_password != user.hashed_password:
                    # note that to dissuade brute force attempts the error for not finding the user
                    # and not matching the password should be the same
                    errors["match"] = True
            else:
                errors["match"] = True

        if errors:
            del form_data["password"] # never send password back for security
            self.redisplay(form_data, errors)
        else:
            self.login(user, remember=valid_data["remember"])


class LogoutController(BaseController):

    @withUser
    def post(self):
        str_key = self.session['auth_key']
        try:
            auth_key = model.ndb.Key(urlsafe=str_key)
        except:
            pass
        else:
            self.uncache(str_key)
            auth_key.delete()
        self.session.clear()
        self.redirect("/")


class ForgotPasswordController(FormController):

    FIELDS = {"email": validateRequiredEmail}

    @withoutUser
    def get(self):

        self.renderTemplate('user/forgot_password.html')

    @withoutUser
    def post(self):
        
        form_data, errors, valid_data = self.validate()

        if errors:
            self.redisplay(form_data, errors)
        else:
            # for security, don't alert them if the user doesn't exist
            user = model.User.getByEmail(valid_data["email"])
            if user:
                user = user.resetPassword()
                self.deferEmail([user.email], "Reset Password", "reset_password.html",
                    key=user.slug, token=user.token)

            message = "Your password reset email has been sent. "
            message += "For security purposes it will expire in one hour."
            self.flash("success", message)
            self.redisplay()


class ResetPasswordController(BaseLoginController):

    FIELDS = {"key": validateRequiredString, "token": validateRequiredString, "password": validateRequiredString}

    @withoutUser
    def before(self):
        is_valid = False
        self.key = self.request.get("key")
        self.token = self.request.get("token")
        if self.key and self.token:
            self.user = model.getByKey(self.key)
            if self.user and self.user.token and self.token == self.user.token:
                # token is valid for one hour
                if (datetime.utcnow() - self.user.token_date).total_seconds() < 3600:
                    is_valid = True

        if not is_valid:
            self.flash("error", "That reset password link has expired.")
            self.redirect("/user/forgotpassword")

    def get(self):

        self.renderTemplate('user/reset_password.html', key=self.key, token=self.token)

    def post(self):
        
        form_data, errors, valid_data = self.validate()

        if errors:
            self.redisplay(form_data, errors, "/user/resetpassword?key=" + self.key + "&token=" + self.token)
        else:
            password_salt, hashed_password = model.User.changePassword(valid_data["password"])
            del valid_data["password"]
            self.user.password_salt = password_salt
            self.user.hashed_password = hashed_password
            self.user.token = None
            self.user.token_date = None
            self.user.put()

            # need to uncache so that changes to the user object get picked up by memcache
            self.uncache(self.key)
            self.flash("success", "Your password has been changed. You have been logged in with your new password.")
            self.login(self.user)
