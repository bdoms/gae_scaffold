from datetime import datetime

#import cloudstorage as gcs
from lib.gae_validators import validateRequiredString, validateRequiredEmail, validateBool
import httpagentparser
from tornado import web

from config.constants import AUTH_EXPIRES_DAYS
from controllers.base import BaseController, FormController, withoutUser
import model
import helpers

IMAGE_TYPES = ["gif", "jpg", "jpeg", "png"]


class BaseLoginController(FormController):

    def login(self, user, new=False, remember=False):
        ua = self.request.headers.get('User-Agent', '')
        ip = self.request.remote_ip or ''

        # reject a login attempt without a user agent or IP address
        if not ua or not ip:
            self.flash('error', 'Invalid client.')
            return self.redirect("/user/login")

        auth = None
        if not new:
            auth = user.getAuth(ua)

        if auth:
            # note that this triggers the last login auto update
            auth.update(ip=ip)
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
            auth = model.Auth.create(user_agent=ua, os=os, browser=browser, device=device, ip=ip, parent=user.key)
            auth.put()

        expires_days = remember and AUTH_EXPIRES_DAYS or None
        self.set_secure_cookie('auth_key', auth.slug, expires_days=expires_days, httponly=True,
            secure=not helpers.debug())

        self.redirect("/home")


class IndexController(FormController):

    # TODO: need a serving URL for non-image files and this should work in prod
    # self.current_user.pic_url = 'https://' + self.gcs_bucket + '.storage.googleapis.com/' + rel_path

    # this is sometimes called by the blob service, so it won't include the CSRF
    SKIP_CSRF = True

    @web.authenticated
    def get(self):

        self.renderTemplate('user/index.html')

    @web.authenticated
    def post(self):

        # TODO: this needs to be adapted to not use the blob store at all
        if self.get_argument('delete'):
            # this is called directly so we can manually check the CSRF here
            if not self.checkCSRF():
                return self.renderError(412)

            if self.current_user.pic_gcs:
                path = self.current_user.pic_gcs
                if path.startswith('/gs/'):
                    path = path[3:]
                gcs.delete(path)
            if self.current_user.pic_url:
                images.delete_serving_url(self.current_user.pic_blob)
            if self.current_user.pic_blob:
                blobstore.delete(self.current_user.pic_blob)

            self.current_user.pic_gcs = None
            self.current_user.pic_blob = None
            self.current_user.pic_url = None
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

                try:
                    # note that this serving URL supports size and crop query params
                    self.current_user.pic_url = images.get_serving_url(upload, secure_url=True)
                except images.TransformationError:
                    upload.delete()
                    errors = {'corrupt': True}
                    continue

                self.current_user.pic_gcs = upload.gs_object_name
                self.current_user.pic_blob = upload.key()

            if errors:
                return self.redisplay({}, errors)

        self.current_user.put()
        helpers.uncache(self.current_user.slug)
        self.redisplay()


class AuthsController(FormController):

    @web.authenticated
    def get(self):

        auths = self.current_user.auths
        current_auth_key = self.get_secure_cookie('auth_key').decode()

        self.renderTemplate('user/auths.html', auths=auths, current_auth_key=current_auth_key)

    @web.authenticated
    def post(self):

        str_key = self.get_argument('auth_key')
        auth_key = model.Auth.slugToKey(str_key, parent_class=model.User)
        if auth_key.parent != self.current_user.key:
            return self.renderError(403)
        else:
            model.db.delete(auth_key)
            helpers.uncache(str_key)
            self.flash('success', 'Access revoked.')

        self.redisplay()


class EmailController(FormController):

    FIELDS = {"email": validateRequiredEmail, "password": validateRequiredString}

    @web.authenticated
    def get(self):

        self.renderTemplate('user/email.html')

    @web.authenticated
    def post(self):

        form_data, errors, valid_data = self.validate()

        hashed_password = model.User.hashPassword(valid_data["password"], self.current_user.password_salt)
        if hashed_password != self.current_user.hashed_password:
            errors["match"] = True

        # extra validation to make sure that email address isn't already in use
        if not errors:
            # note that emails are supposed to be case sensitive according to RFC 5321
            # however in practice users consistenly expect them to be case insensitive
            email = valid_data["email"].lower()
            user = model.User.getByEmail(email)
            if user:
                errors["exists"] = True

        if errors:
            del form_data["password"] # never send password back for security
            self.redisplay(form_data, errors)
        else:
            self.current_user.update(email=email)
            self.current_user.put()
            helpers.uncache(self.current_user.slug)

            self.flash("success", "Email changed successfully.")
            self.redirect("/user")


class PasswordController(FormController):

    FIELDS = {"password": validateRequiredString, "new_password": validateRequiredString}

    @web.authenticated
    def get(self):

        self.renderTemplate('user/password.html')

    @web.authenticated
    def post(self):

        form_data, errors, valid_data = self.validate()

        if not errors:
            hashed_password = model.User.hashPassword(valid_data["password"], self.current_user.password_salt)
            if hashed_password != self.current_user.hashed_password:
                errors["match"] = True

        if errors:
            del form_data["password"]
            del form_data["new_password"]
            self.redisplay(form_data, errors)
        else:
            password_salt, hashed_password = model.User.changePassword(valid_data["new_password"])

            self.current_user.update(password_salt=password_salt, hashed_password=hashed_password)
            self.current_user.put()
            helpers.uncache(self.current_user.slug)

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
            valid_data["email"] = valid_data["email"].lower()
            user = model.User.getByEmail(valid_data["email"])
            if user:
                errors["exists"] = True

        if errors:
            del form_data["password"] # never send password back for security
            self.redisplay(form_data, errors)
        else:
            password_salt, hashed_password = model.User.changePassword(valid_data["password"])
            del valid_data["password"]
            user = model.User.create(password_salt=password_salt, hashed_password=hashed_password, **valid_data)
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
            user = model.User.getByEmail(valid_data["email"].lower())
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

    @web.authenticated
    def post(self):
        slug = self.get_secure_cookie('auth_key').decode()
        auth_key = model.Auth.slugToKey(slug, parent_class=model.User)
        model.db.delete(auth_key)
        helpers.uncache(slug)

        self.clear_all_cookies()
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
            user = model.User.getByEmail(valid_data["email"].lower())
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
        self.key = self.get_argument("key")
        self.token = self.get_argument("token")
        if self.key and self.token:
            self.current_user = model.getByKey(self.key)
            if self.current_user and self.current_user.token and self.token == self.current_user.token:
                # token is valid for one hour
                if (datetime.utcnow() - self.current_user.token_date).total_seconds() < 3600:
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
            self.current_user.update(password_salt=password_salt, hashed_password=hashed_password,
                token=None, token_date=None)
            self.current_user.put()

            # need to uncache so that changes to the user object get picked up by the cache
            helpers.uncache(self.current_user.slug)
            self.flash("success", "Your password has been changed. You have been logged in with your new password.")
            self.login(self.current_user)
