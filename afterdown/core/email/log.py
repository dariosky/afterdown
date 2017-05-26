from __future__ import print_function
import logging
import smtplib
from email.mime.text import MIMEText
from logging.handlers import BufferingHandler


# code based on this gist by Viany Sajip: https://gist.github.com/anonymous/1379446
class BufferedSmtpHandler(BufferingHandler):
    """ This is a memoryhandler buffer, that never flush with big capacity (just to split MB emails)
        that will send a mail using configured smtp at the end
    """

    def __init__(self, mailfrom, mailto, subject,
                 smtp_username=None, smtp_password=None,
                 smtp_host="localhost", smtp_port=None,
                 send_mail=True,  # usually the mail will be sent no matter what
                 DEBUG=False,  # in the DEBUG mode, no mail will be sent
                 capacity=1024 * 10, ):
        super(BufferedSmtpHandler, self).__init__(capacity)

        self.DEBUG = DEBUG
        self.mailfrom = mailfrom
        self.mailto = mailto
        self.subject = subject
        self.send_mail = send_mail
        self._default_send_mail = send_mail  # the send_mail status after a flush

        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_host = smtp_host
        self.smtp_port = int(smtp_port) if smtp_port else smtplib.SMTP_PORT
        self.setFormatter(logging.Formatter("%(message)s"))

    def flush(self):
        if len(self.buffer) > 0:
            if self.send_mail:
                try:
                    port = self.smtp_port
                    recipients = self.mailto.split(",")
                    print(("Sending mail" if not self.DEBUG else "Would send mail") +
                          " to %s" % recipients)
                    msg = MIMEText("\r\n".join(map(self.format, self.buffer)), _charset="utf-8")
                    msg["From"] = self.mailfrom
                    msg["To"] = recipients[0]
                    msg["Subject"] = self.subject

                    if not self.DEBUG:
                        smtp = smtplib.SMTP(self.smtp_host, port)
                        if self.smtp_username and self.smtp_password:
                            smtp.login(self.smtp_username, self.smtp_password)
                        smtp.sendmail(self.mailfrom, recipients, msg.as_string())
                        smtp.quit()
                    else:
                        print("in DEBUG no mail will be sent.")
                except Exception as e:
                    print(e)
                    raise e
            self.buffer = []
            self.send_mail = self._default_send_mail
