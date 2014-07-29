from datetime import datetime, timedelta

from base import BaseController, FormController, withUser, withoutUser

import model

from lib.gae_validators import validateRequiredString, validateEmail


class BaseLoginController(FormController):

    def login(self, user):
        self.session["user_key"] = user.key.urlsafe()
        self.session["user_auth"] = user.getAuth()
        self.redirect("/home")


class IndexController(FormController):

    @withUser
    def get(self):

        self.renderTemplate('user/index.html')


class ChangeEmailController(FormController):

    FIELDS = {"email": validateEmail, "password": validateRequiredString}

    @withUser
    def get(self):

        self.renderTemplate('user/change_email.html')

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
            self.redisplay(form_data, errors, "/changeemail")
        else:
            self.user.email = valid_data["email"]
            self.user.put()
            self.uncache(self.user.key.urlsafe())

            self.flash("success", "Email changed successfully.")
            self.redirect("/settings")


class ChangePasswordController(FormController):

    FIELDS = {"password": validateRequiredString, "new_password": validateRequiredString}

    @withUser
    def get(self):

        self.renderTemplate('user/change_password.html')

    @withUser
    def post(self):
        
        form_data, errors, valid_data = self.validate()

        hashed_password = model.User.hashPassword(valid_data["password"], self.user.password_salt)
        if hashed_password != self.user.hashed_password:
            errors["match"] = True

        if errors:
            del form_data["password"]
            del form_data["new_password"]
            self.redisplay(form_data, errors, "/changepassword")
        else:
            password_salt, hashed_password = model.User.changePassword(valid_data["new_password"])
            
            self.user.populate(password_salt=password_salt, hashed_password=hashed_password)
            self.user.put()
            self.uncache(self.user.key.urlsafe())

            # must re-auth the user because their password has changed and the auth depends on that
            self.session["user_auth"] = self.user.getAuth()

            self.flash("success", "Password changed successfully.")
            self.redirect("/settings")


class SignupController(BaseLoginController):

    FIELDS = {
        "first_name": validateRequiredString,
        "last_name": validateRequiredString,
        "email": validateEmail,
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
            self.redisplay(form_data, errors, "/signup")
        else:
            password_salt, hashed_password = model.User.changePassword(valid_data["password"])
            del valid_data["password"]
            user = model.User(password_salt=password_salt, hashed_password=hashed_password, **valid_data)
            user.put()
            self.flash("success", "Thank you for signing up!")
            self.login(user)


class LoginController(BaseLoginController):

    FIELDS = {"email": validateEmail, "password": validateRequiredString}

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
            self.redisplay(form_data, errors, "/login")
        else:
            self.login(user)


class LogoutController(BaseController):

    @withUser
    def get(self):
        self.session.clear()
        self.redirect("/")


class ForgotPasswordController(FormController):

    FIELDS = {"email": validateEmail}

    @withoutUser
    def get(self):

        self.renderTemplate('user/forgot_password.html')

    @withoutUser
    def post(self):
        
        form_data, errors, valid_data = self.validate()

        # for security, don't alert them if the user doesn't exist
        user = None
        if not errors:
            user = model.User.getByEmail(valid_data["email"])
            if user:
                self.deferEmail(user.email, "Reset Password", "reset_password.html",
                    key=user.key.urlsafe(), token=user.resetPasswordToken())

        if errors:
            self.redisplay(form_data, errors, "/forgotpassword")
        else:
            message = "Your password reset email has been sent. "
            message += "For security purposes it will expire in about an hour."
            self.flash("success", message)
            self.redirect("/forgotpassword")


class ResetPasswordController(BaseLoginController):

    FIELDS = {"key": validateRequiredString, "token": validateRequiredString, "password": validateRequiredString}

    @withoutUser
    def before(self):
        is_valid = False
        self.key = self.request.get("key")
        self.token = self.request.get("token")
        if self.key and self.token:
            self.user = model.getByKey(self.key)
            if self.user:
                # try this hour and the previous one to validate
                # this gives the link a valid time ranging between 60 and 120 minutes depending on when it is created
                if self.token == self.user.resetPasswordToken():
                    is_valid = True
                else:
                    hour_ago = datetime.utcnow() - timedelta(hours=1)
                    if self.token == self.user.resetPasswordToken(timestamp=hour_ago):
                        is_valid = True

        if not is_valid:
            self.flash("error", "That reset password link has expired.")
            self.redirect("/forgotpassword")

    def get(self):

        self.renderTemplate('user/reset_password.html', key=self.key, token=self.token)

    def post(self):
        
        form_data, errors, valid_data = self.validate()

        if errors:
            self.redisplay(form_data, errors, "/resetpassword?key=" + self.key + "&token=" + self.token)
        else:
            password_salt, hashed_password = model.User.changePassword(valid_data["password"])
            del valid_data["password"]
            self.user.password_salt = password_salt
            self.user.hashed_password = hashed_password
            self.user.put()

            # need to uncache so that changes to the user object get picked up by memcache
            self.uncache(self.key)
            self.flash("success", "Your password has been changed. You have been logged in with your new password.")
            self.login(self.user)
