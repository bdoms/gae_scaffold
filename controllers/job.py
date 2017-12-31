import logging
from datetime import datetime, timedelta

from base import BaseController
import model


class AuthsController(BaseController):

    MAX_DAYS = 14

    def get(self):

        days_ago = datetime.utcnow() - timedelta(self.MAX_DAYS)
        auths = model.Auth.query(model.Auth.last_login < days_ago).fetch(keys_only=True)
        model.ndb.delete_multi(auths)

        logging.info('Removed ' + str(len(auths)) + ' old auths.')

        self.render('OK')
