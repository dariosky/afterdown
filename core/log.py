from email.mime.text import MIMEText
import logging
from logging.handlers import BufferingHandler
import smtplib

# code based on this gist by Viany Sajip: https://gist.github.com/anonymous/1379446


class BufferedSmtpHandler(BufferingHandler):
    """ This is a memoryhandler buffer, that never flush with big capacity (just to split MB emails)
    that will
    """

    def __init__(self, mailfrom, mailto, subject,
                 smtp_username=None, smtp_password=None,
                 smtp_host="localhost", smtp_port=smtplib.SMTP_PORT, capacity=1024 * 10):
        super(BufferedSmtpHandler, self).__init__(capacity)

        self.mailfrom = mailfrom
        self.mailto = mailto
        self.subject = subject

        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_host = smtp_host
        self.smtp_port = int(smtp_port)
        self.setFormatter(logging.Formatter("%(message)s"))

    def flush(self):
        if len(self.buffer) > 0:
            try:
                port = self.smtp_port
                recipients = self.mailto.split(",")
                print "Sending mail to %s" % recipients

                msg = MIMEText("\r\n".join(map(self.format, self.buffer)), _charset="utf-8")
                msg["From"] = self.mailfrom
                msg["To"] = recipients[0]
                msg["Subject"] = self.subject

                smtp = smtplib.SMTP(self.smtp_host, port)
                if self.smtp_username and self.smtp_password:
                    smtp.login(self.smtp_username, self.smtp_password)
                smtp.sendmail(self.mailfrom, recipients, msg.as_string())
                smtp.quit()
            except Exception as e:
                raise e
            self.buffer = []
