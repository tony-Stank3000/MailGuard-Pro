from flask import Flask, render_template, request
import smtplib
from email.mime.text import MIMEText
import validate_email
import dns.resolver
import socket
import random

app = Flask(__name__)

def is_catch_all(email):
    domain = email.split("@")[1] if "@" in email else ""
    if not domain:
        return False  # No domain found in the email

    catchall_dnspython = is_catch_all_dnspython(domain)
    if catchall_dnspython:
        return True

    test_addresses = generate_test_addresses(domain, email)

    try:
        catchall_smtplib = is_catch_all_smtplib(email, test_addresses)
        catchall_bounce = is_catch_all_bounce(test_addresses)

        return catchall_smtplib or catchall_bounce

    except (smtplib.SMTPConnectError, smtplib.SMTPResponseException, dns.resolver.NXDOMAIN):
        return False

def is_catch_all_bounce(test_addresses):
    try:
        for address in test_addresses:
            with smtplib.SMTP(address.split("@")[1]) as smtp:
                status, _ = smtp.sendmail(address, "verify@example.com", "Test message")
                if status != 250:
                    return False

        return True  # It's a catch-all

    except smtplib.SMTPConnectError:
        return False


def is_catch_all_dnspython(domain):
    try:
        answers = dns.resolver.query(domain, 'MX')
        for rdata in answers:
            if rdata.exchange.to_text() == "0.0.0.0":
                return True
        return False
    except dns.resolver.NXDOMAIN:
        return False


def generate_similar_test_addresses(email):
    username, domain = email.split("@")
    test_addresses = []
    for i in range(10):
        test_username = f"{username}{i}"
        test_addresses.append(f"{test_username}@{domain}")
    return test_addresses

def generate_test_addresses(domain, email):
    # Generate test addresses with a mix of similar and random addresses
    similar_addresses = generate_similar_test_addresses(email)
    random_addresses = [f"test{random.randint(100, 999)}@{domain}" for _ in range(10)]
    return similar_addresses + random_addresses

def is_catch_all_smtplib(email, test_addresses):
    try:
        domain = email.split("@")[1]
        # Connect to the domain's SMTP server
        smtp = smtplib.SMTP(domain)
        smtp.set_debuglevel(1)  # Set this to 0 for no debugging

        for test_address in test_addresses:
            # Send a test email
            msg = MIMEText("This is a test email.")
            msg["Subject"] = "Test"
            msg["From"] = email
            msg["To"] = test_address

            smtp.sendmail(email, [test_address], msg.as_string())

        # Check if any test email was accepted
        responses = [smtp.noop() for _ in test_addresses]
        smtp.quit()

        if any(response[0] == 250 for response in responses):
            return False  # It's not a catch-all
        else:
            return True  # It's a catch-all

    except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, smtplib.SMTPResponseException, socket.timeout):
        return False  # Handle the exception gracefully

# ... (Other functions remain the same)

@app.route("/", methods=["GET", "POST"])
def index():
    result = []
    if request.method == "POST":
        email_list = request.form["email_list"].split("\n")
        for email in email_list:
            email = email.strip()
            if email:
                is_valid = validate_email.validate_email(email)  # Use a sophisticated email validation library
                is_catchall = is_catch_all(email)
                result.append((email, is_valid, is_catchall))

    return render_template("index.html", result=result)

if __name__ == "__main__":
    app.run(debug=True)
