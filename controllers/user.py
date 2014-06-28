import os

from base import BaseController, withUser, withoutUser

import model

from lib.gae_validators import validateRequiredString, validateEmail


class SignupController(BaseController):

    @withoutUser
    def get(self):

        self.renderTemplate('signup.html')

    @withoutUser
    def post(self):
        
        first_name = self.request.get("first_name")
        last_name = self.request.get("last_name")
        email = self.request.get("email")
        password = self.request.get("password")

        form_data = {"first_name": first_name, "last_name": last_name, "email": email}
        errors = {}

        valid, first_name = validateRequiredString(first_name)
        if not valid:
            errors["first_name"] = True

        valid, last_name = validateRequiredString(last_name)
        if not valid:
            errors["last_name"] = True

        valid, email = validateEmail(email)
        if not valid:
            errors["email"] = True

        valid, password = validateRequiredString(password)
        if not valid:
            errors["password"] = True

        if not errors:
            user = model.User.query(model.User.email == email).get()
            if user:
                errors["exists"] = True

        if errors:
            self.session["form"] = form_data
            self.session["errors"] = errors
            self.redirect("/signup")
        else:
            auth_pepper = os.urandom(64).encode("base64")
            password_pepper = os.urandom(64).encode("base64")
            hashed_password = model.User.hashPassword(password, password_pepper)
            user = model.User(first_name=first_name, last_name=last_name, email=email, auth_pepper=auth_pepper,
                password_pepper=password_pepper, hashed_password=hashed_password)
            user_key = user.put()
            self.session["user_key"] = user_key.urlsafe()
            self.session["user_auth"] = user.getAuth(self.request.remote_addr or os.environ["REMOTE_ADDR"])
            self.redirect("/home")


class LoginController(BaseController):

    @withoutUser
    def get(self):

        self.renderTemplate('login.html')

    @withoutUser
    def post(self):
        
        email = self.request.get("email")
        password = self.request.get("password")

        form_data = {"email": email}
        errors = {}

        valid, email = validateEmail(email)
        if not valid:
            errors["email"] = True

        valid, password = validateRequiredString(password)
        if not valid:
            errors["password"] = True

        user = None
        if not errors:
            user = model.User.query(model.User.email == email).get()
            if user:
                hashed_password = model.User.hashPassword(password, user.password_pepper)
                if hashed_password != user.hashed_password:
                    errors["match"] = True
            else:
                errors["match"] = True

        if errors:
            self.session["form"] = form_data
            self.session["errors"] = errors
            self.redirect("/login")
        else:
            str_key = user.key.urlsafe()
            self.session["user_key"] = str_key
            self.session["user_auth"] = user.getAuth(self.request.remote_addr or os.environ["REMOTE_ADDR"])
            self.redirect("/home")


class LogoutController(BaseController):

    @withUser
    def get(self):
        self.session.clear()
        self.redirect("/")
