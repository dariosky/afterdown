# coding=utf-8
import base64
from email import Charset
from email.mime.text import MIMEText
import mimetypes
import os
import smtplib
import textwrap

__author__ = 'Dario Varotto'
# we are sending email, so inline all css
MAIL_CSS = dict(
    move="background-color: #c4eec8; color: #550",
    unrecognized="padding: 0; background-color: #ffedf8",
    createfolder="padding: 0; background-color: #cde3fd",
    deleted="color: #111; font-size: smaller",
    download="background-color: #528aff; color: #fff",
)
MAIL_TEMPLATE = textwrap.dedent("""
<!DOCTYPE html>
<html>
<head lang="en">
	<meta charset="UTF-8">
</head>
<body style='color: #4e009f'>
<h1 id="header" style="font-family: 'Georgia', serif; text-align: center;">
	<img src="data:{logo_mimetype};base64,{logo_b64}" alt="" style="vertical-align: middle"/>
	Afterdown report
</h1>
<table style='width: 100%; text-align:center;'>
{rows}
</table>
<div style="margin: 1em; text-align: right;">{summary}</div>
</body>
</html>
""")
LOGO_FILENAME = os.path.join(os.path.dirname(__file__), "assets", "logo.png")


class AfterMailReport(object):
    """ A mailer with nice formatting to be used for afterdown status mail
        Use the same initializer parameters of BufferedSmtpHandler
    """

    def __init__(self, mailfrom, mailto, subject,
                 smtp_username=None, smtp_password=None,
                 smtp_host="localhost", smtp_port=None,
                 send_mail=False,  # usually the mail will be sent no matter what
                 DEBUG=False,  # in the DEBUG mode, no mail will be sent
                 ):
        self.subject = subject
        self.mailto = mailto
        self.mailfrom = mailfrom
        self.DEBUG = DEBUG
        self.smtp_port = int(smtp_port) if smtp_port else smtplib.SMTP_PORT
        self.smtp_host = smtp_host
        self.smtp_password = smtp_password
        self.smtp_username = smtp_username
        self.send_mail = send_mail  # there is need to send mail?

        self.html_body = ""  # the html mail body
        self.rows = []
        self.summary = ""
        self.max_tokens = 0

    def add_row(self, apply_result, tokens=None, className=None, important=None):
        """ Add the nice row to the HTML, taking tokens and formatting from an ApplyResult instance
            eventually you can force some of the parameters
        """
        if tokens is None:
            tokens = apply_result.tokens
        if className is None:
            className = apply_result.className
        if important is None:
            important = apply_result.important

        if important:
            self.send_mail = True
        self.rows.append(dict(
            tokens=tokens,
            className=className
        ))
        self.max_tokens = max(self.max_tokens, len(tokens))

    def set_summary(self, summary):
        self.summary = summary

    def send(self):
        """
        Send pretty report mail in html if needed.
        Return True when mail is sent

        :rtype : bool
        """
        if not self.send_mail:
            return False
        port = self.smtp_port
        recipients = self.mailto.split(",")
        print ("Sending report mail" if not self.DEBUG else "Would send mail") + " to %s" % recipients
        Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')

        context = {"summary": self.summary}
        if os.path.isfile(LOGO_FILENAME):
            with file(LOGO_FILENAME, "rb") as f:
                # TODO: Base64 inline images are not supported by many webmail, use mime alternative related
                logo_b64 = base64.b64encode(f.read())
                logo_mimetype = mimetypes.guess_type(LOGO_FILENAME)[0]
                context.update(dict(logo_b64=logo_b64, logo_mimetype=logo_mimetype))
        context['rows'] = "\n".join(["<tr{styleattr}>\n{cells}\n</tr>".format(
            styleattr=" style='%s'" % MAIL_CSS.get(row['className']) if row['className'] and MAIL_CSS.get(
                row['className']) else '',
            cells="\n".join(["\t<td style='padding: 10px 10px'>%s</td>" % cell for cell in row['tokens']])
        ) for row in self.rows])
        # I cant use "format" to parse template cause the css is parsed, so I use a simpler replace for var in context
        html = MAIL_TEMPLATE
        for key in context:
            html = html.replace("{%s}" % key, context[key])

        msg = MIMEText(html, _subtype='html', _charset='utf-8')
        msg["From"] = self.mailfrom
        msg["To"] = recipients[0]
        msg["Subject"] = self.subject
        msg["X-MC-Track"] = "no,no" # if you are using Mandrill as SMPT, set it as don't track

        if not self.DEBUG:
            smtp = smtplib.SMTP(self.smtp_host, port)
            if self.smtp_username and self.smtp_password:
                smtp.login(self.smtp_username, self.smtp_password)
            smtp.sendmail(self.mailfrom, recipients, msg.as_string())
            smtp.quit()
            return True
        else:
            print "In DEBUG mode no mails are sent."
            # file(os.path.join(os.path.dirname(__file__), "mail_output.html"), "w").write(html)
            # print msg.as_string()
