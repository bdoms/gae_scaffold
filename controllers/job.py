import base64
from datetime import datetime, timedelta
import json
import logging
import urllib2

from google.appengine.api import mail

from base import BaseController
from config.constants import SENDGRID_API_KEY, SENDER_EMAIL
import model
import helpers

import sendgrid
from sendgrid.helpers import mail as sgmail


class AuthsController(BaseController):

    MAX_DAYS = 14

    def get(self):

        days_ago = datetime.utcnow() - timedelta(self.MAX_DAYS)
        auths = model.Auth.query(model.Auth.last_login < days_ago).fetch(keys_only=True)
        model.ndb.delete_multi(auths)

        logging.info('Removed ' + str(len(auths)) + ' old auths.')

        self.render('OK')


class EmailController(BaseController):

    # called internally
    SKIP_CSRF = True

    SENDGRID = sendgrid.SendGridAPIClient(apikey=SENDGRID_API_KEY)

    def post(self):

        to = self.request.get_all('to')
        subject = self.request.get('subject')
        html = self.request.get('html')
        attachments_json = self.request.get('attachments')
        reply_to = self.request.get('reply_to')

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
            except urllib2.HTTPError, e:
                logging.error(e.read())
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
                    mail_attachment = mail.Attachment(data['filename'], base64.b64decode(data['content']),
                        content_id=data['content_id'])
                    mail_attachments.append(mail_attachment)
                kwargs['attachments'] = mail_attachments

            if reply_to:
                kwargs['reply_to'] = reply_to

            for to_email in to:
                kwargs['to'] = to_email
                mail.send_mail(**kwargs)

        self.render('OK')
