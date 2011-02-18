from base import BaseController
from lib.gaesessions import delete_expired_sessions


class SessionsController(BaseController):
    def get(self):
        while not delete_expired_sessions():
            pass
        self.response.set_status(200)
        self.response.out.write("OK")

