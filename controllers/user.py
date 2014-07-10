import os

from base import BaseController, FormController, withUser, withoutUser

import model

from lib.gae_validators import validateRequiredString, validateEmail


class BaseLoginController(FormController):

    def login(self, user):
        self.session["user_key"] = user.key.urlsafe()
        self.session["user_auth"] = user.getAuth()
        self.redirect("/home")


class SignupController(BaseLoginController):

    FIELDS = {
        "first_name": validateRequiredString,
        "last_name": validateRequiredString,
        "email": validateEmail,
        "password": validateRequiredString
    }

    @withoutUser
    def get(self):

        self.renderTemplate('signup.html')

    @withoutUser
    def post(self):
        
        form_data, errors, valid_data = self.validate()

        # extra validation to make sure that email address isn't already in use
        if not errors:
            user = model.User.query(model.User.email == valid_data["email"]).get()
            if user:
                errors["exists"] = True

        if errors:
            del form_data["password"] # never send password back for security
            self.redisplay(form_data, errors, "/signup")
        else:
            password_salt = os.urandom(64).encode("base64")
            hashed_password = model.User.hashPassword(valid_data["password"], password_salt)
            del valid_data["password"]
            user = model.User(password_salt=password_salt, hashed_password=hashed_password, **valid_data)
            user.put()
            self.flash("success", "Thank you for signing up!")
            self.login(user)


class LoginController(BaseLoginController):

    FIELDS = {"email": validateEmail, "password": validateRequiredString}

    @withoutUser
    def get(self):

        self.renderTemplate('login.html')

    @withoutUser
    def post(self):
        
        form_data, errors, valid_data = self.validate()

        # check that the user exists and the password matches
        user = None
        if not errors:
            user = model.User.query(model.User.email == valid_data["email"]).get()
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
