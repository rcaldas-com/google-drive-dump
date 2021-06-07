from os import getenv
import ssl
from smtplib import SMTP

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# from jinja2 import Environment, FileSystemLoader

TITLE = getenv('TITLE') or 'Drivedump'
MAIL_DEFAULT_SENDER = f"{TITLE} <{getenv('MAIL_USERNAME')}>"

MAIL_SERVER = getenv('MAIL_SERVER')
MAIL_USERNAME = getenv('MAIL_USERNAME')
MAIL_PASSWORD = getenv('MAIL_PASSWORD')
MAIL_PORT = int(getenv('MAIL_PORT') or 587)
MAIL_USE_TLS = getenv('MAIL_USE_TLS') or True

def send_mail(recipient, subject, text, html=None):
    msg = MIMEMultipart()
    msg['To'] = recipient
    msg['Subject'] = subject
    msg['From'] = MAIL_DEFAULT_SENDER
    msg.attach(MIMEText(text, 'plain'))

    # # Open file in binary mode using read() method
    # attachment = open(filename, “rb”)
    # part = MIMEBase(“application”, “octet-stream”)
    # part.set_payload(attachment.read())
    # encoders.encode_base64(part)
    # part.add_header('Content-Disposition', 'attachment', filename=filename)
    # msg.attach(part)

    if html:
        msg.attach(MIMEText(html, 'html'))

    CONTEXT = ssl.create_default_context()
    try:
        server = SMTP(MAIL_SERVER, MAIL_PORT)
        server.starttls(context=CONTEXT)
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_USERNAME, recipient, msg.as_string())

    except Exception as e:
        print(e)
    finally:
        server.quit()

