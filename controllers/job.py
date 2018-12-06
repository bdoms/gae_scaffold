import base64
from datetime import datetime, timedelta
import json
import urllib.error

from controllers.base import BaseController
from config.constants import SENDGRID_API_KEY, SENDER_EMAIL
import model
import helpers

import sendgrid
from sendgrid.helpers import mail as sgmail


class AuthsController(BaseController):

    MAX_DAYS = 30

    def check_xsrf_cookie(self):
        pass

    def get(self):

        days_ago = datetime.utcnow() - timedelta(self.MAX_DAYS)
        auths = model.Auth.query(model.Auth.last_login < days_ago).fetch(keys_only=True)
        model.db.delete_multi([auth.key for auth in auths])

        self.logger.info('Removed ' + str(len(auths)) + ' old auths.')

        self.render('OK')


class EmailController(BaseController):

    SENDGRID = sendgrid.SendGridAPIClient(apikey=SENDGRID_API_KEY)

    # called internally
    def check_xsrf_cookie(self):
        pass

    def post(self):

        to = self.get_arguments('to')
        subject = self.get_argument('subject')
        html = self.get_argument('html')
        attachments_json = self.get_argument('attachments')
        reply_to = self.get_argument('reply_to')

        body = helpers.strip_html(html)

        # attachments had to be encoded to send properly, so we decode them here
        attachments = attachments_json and json.loads(attachments_json) or None

        if SENDGRID_API_KEY and not helpers.testing():
            message = sgmail.Mail()
            message.from_email = sgmail.Email(SENDER_EMAIL)
            message.subject = subject

            if attachments:
                for data in attachments:
                    attachment = sgmail.Attachment()
                    attachment.content = base64.b64decode(data['content'])
                    attachment.content_id = data['content_id']
                    attachment.disposition = data.get('disposition', 'inline') # 'attachment' for non-embedded
                    attachment.filename = data['filename']
                    attachment.type = data['type']
                    message.add_attachment(attachment)

            # NOTE that plain must come first
            message.add_content(sgmail.Content('text/plain', body))
            message.add_content(sgmail.Content('text/html', html))

            personalization = sgmail.Personalization()
            for to_email in to:
                personalization.add_to(sgmail.Email(to_email))
            message.add_personalization(personalization)

            if reply_to:
                message.reply_to(sgmail.Email(reply_to))

            # an error here logs the status code but not the message
            # which is way more helpful, so we get it manually
            try:
                self.SENDGRID.client.mail.send.post(request_body=message.get())
            except urllib.error.HTTPError:
                self.logger.error(e.read())
        else:
            kwargs = {
                'sender': SENDER_EMAIL,
                'subject': subject,
                'body': body,
                'html': html
            }

            if attachments:
                mail_attachments = []
                for data in attachments:
                    mail_attachment = [data['filename'], base64.b64decode(data['content']), data['content_id']]
                    mail_attachments.append(mail_attachment)
                kwargs['attachments'] = mail_attachments

            if reply_to:
                kwargs['reply_to'] = reply_to

            for to_email in to:
                kwargs['to'] = to_email

            self.logger.info(kwargs)

        self.render('OK')
