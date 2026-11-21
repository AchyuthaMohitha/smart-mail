"""
demo_emails.py - DEMO DATA: a small, made-up inbox of a university student.

*** Every email in this file is DEMO DATA written for the SmartMail project. ***
*** None of them are real Gmail messages. The dashboard marks them "DEMO".  ***

All people, companies and addresses are invented. Addresses use the reserved
".example" domain (it can never belong to a real person or company).

How the demo works:
  Each demo email below is turned into a real email message (MIME format, the same
  format Gmail gives us) by build_raw_email(), and then read by email_parser.py,
  exactly like a Gmail message. Some demo emails have an HTML version, emoji or
  "₹" in the subject, an attachment, or are broken on purpose, so that every part
  of the email reader is used.

"human_label" = the category WE (the project team) think fits the email.
The app NEVER reads it. The classifier decides the category on its own.
It is only used by "python demo_emails.py" to compare the model with our opinion.
"""

from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime

IST = timezone(timedelta(hours=5, minutes=30))   # Indian Standard Time
DEMO_STUDENT = "Demo Student <demo.student@university.example>"


def ist(year, month, day, hour, minute):
    """Date header text for a time in India, e.g. 'Mon, 26 Oct 2026 07:45:00 +0530'."""
    return format_datetime(datetime(year, month, day, hour, minute, tzinfo=IST))


DEMO_EMAILS = [
    # ------------------------------------------------------------ professor announcement
    {
        "id": "demo-01",
        "human_label": "Urgent",
        "from": "Dr. K. Srinivasa Rao <ksrao@cse.university.example>",
        "to": "CSE-B 2nd Year <cse-b-2027@lists.university.example>",
        "date": ist(2026, 10, 26, 7, 45),
        "subject": "CN Lab internal moved to tomorrow (Tue) 9:30 AM – Lab 3",
        "body": """Dear all,

Because of the power shutdown in Block C on Wednesday, the Computer Networks lab internal has been moved to tomorrow, Tuesday 27 October, at 9:30 AM in Lab 3.

Please bring your observation notebook signed up to Experiment 8. Students without a signed record will not be allowed to write the internal.

The question pool is the same as announced (Experiments 1 to 10). Duration is 90 minutes.

Regards,
Dr. K. Srinivasa Rao
Department of CSE""",
    },
    # ------------------------------------------------------------ assignment deadline (automated)
    {
        "id": "demo-02",
        "human_label": "Urgent",
        "from": "University LMS <no-reply@lms.university.example>",
        "date": ist(2026, 10, 26, 8, 0),
        "subject": "Reminder: DBMS Assignment 3 is due today at 11:59 PM",
        "body": """Hi Demo Student,

This is a reminder that the following assignment is due soon:

Course: CS2203 Database Management Systems
Assignment: Assignment 3 - Normalization and SQL Queries
Due: Today, 26 October 2026, 11:59 PM

You have not submitted this assignment yet. Late submissions are accepted for 24 hours with a 20% penalty.

View the assignment: https://lms.university.example/mod/assign/view.php?id=4471

You are receiving this email because you are enrolled in CS2203.""",
    },
    # ------------------------------------------------------------ placement interview (HTML + text)
    {
        "id": "demo-03",
        "human_label": "Urgent",
        "from": "Training & Placement Cell <placements@university.example>",
        "date": ist(2026, 10, 26, 10, 15),
        "subject": "Shortlisted: TechNova Systems technical interview on Wed, 28 Oct",
        "body": """Dear Student,

Congratulations! You have been shortlisted for the technical interview round of TechNova Systems (On-campus Drive 2026-27).

Date: Wednesday, 28 October 2026
Reporting time: 8:30 AM
Venue: Placement Block, Room 204

Please carry two printed copies of your resume, your college ID card and a laptop with your project code.

Confirm your attendance through the placement portal before 6 PM today: https://placements.university.example/drives/technova/confirm
Students who do not confirm will not be allotted an interview slot.

All the best,
Training & Placement Cell""",
        "html": """<html><body style="font-family:Arial">
<p>Dear Student,</p>
<p><b>Congratulations!</b> You have been shortlisted for the technical interview round of
<b>TechNova Systems</b> (On-campus Drive 2026-27).</p>
<table border="1" cellpadding="6">
<tr><td>Date</td><td>Wednesday, 28 October 2026</td></tr>
<tr><td>Reporting time</td><td>8:30 AM</td></tr>
<tr><td>Venue</td><td>Placement Block, Room 204</td></tr>
</table>
<p>Please carry two printed copies of your resume, your college ID card and a laptop with your project code.</p>
<p><a href="https://placements.university.example/drives/technova/confirm">Confirm attendance</a> before 6 PM today.
Students who do not confirm will not be allotted an interview slot.</p>
<p>All the best,<br>Training &amp; Placement Cell</p>
</body></html>""",
    },
    # ------------------------------------------------------------ exam schedule with attachment
    {
        "id": "demo-04",
        "human_label": "Important",
        "from": "Controller of Examinations <coe@university.example>",
        "to": "All UG Students <ug-students@lists.university.example>",
        "date": ist(2026, 10, 24, 16, 30),
        "subject": "End Semester Examinations, November 2026 – timetable",
        "body": """Dear Students,

The timetable for the End Semester Examinations (November 2026) is attached.

- Examinations begin on Monday, 16 November 2026.
- Forenoon session: 9:30 AM to 12:30 PM. Afternoon session: 2:00 PM to 5:00 PM.
- Hall tickets can be downloaded from the student portal from 10 November.
- Students with less than 75% attendance in a course must meet their HoD before 6 November.

Office of the Controller of Examinations""",
        "attachments": [("ESE_Timetable_Nov2026.pdf", "application", "pdf",
                         b"%PDF-1.4\n% DEMO DATA - placeholder file, not a real timetable\n")],
    },
    # ------------------------------------------------------------ internship opportunity (forwarded)
    {
        "id": "demo-05",
        "human_label": "Important",
        "from": "Dr. Anitha Krishnan <anitha.k@cse.university.example>",
        "date": ist(2026, 10, 23, 18, 5),
        "subject": "Fwd: Summer Research Fellowship 2027 – applications open",
        "body": """Dear students,

Forwarding this for those interested in research internships. It is a good opportunity, especially for 2nd and 3rd years. Feel free to ask me if you need a recommendation letter - please send your request at least a week before the deadline.

Anitha

---------- Forwarded message ---------
From: Research Fellowships Office <fellowships@institute.example>
Subject: Summer Research Fellowship 2027 - applications open

The Summer Research Fellowship 2027 invites applications from undergraduate students in engineering and science.
Selected students work for eight weeks (May-July 2027) with a faculty mentor and receive a monthly stipend.
Last date to apply: 15 November 2026.
Details and online application: https://fellowships.institute.example/srf-2027""",
    },
    # ------------------------------------------------------------ project meeting (teammate)
    {
        "id": "demo-06",
        "human_label": "Important",
        "from": "Rahul Varma <rahul.varma@mail.example>",
        "date": ist(2026, 10, 25, 21, 40),
        "subject": "mini project - meet tomorrow evening?",
        "body": """hey,

Ma'am wants to see a demo of the login module on Friday. can we meet tomorrow around 6 in the library discussion room? we still need to fix the session bug and finish the ER diagram.

if 6 doesn't work for you, 7 is also fine. let me know

- Rahul""",
    },
    # ------------------------------------------------------------ college fees
    {
        "id": "demo-07",
        "human_label": "Important",
        "from": "Accounts Section <accounts@university.example>",
        "date": ist(2026, 10, 22, 11, 0),
        "subject": "Reminder: Odd semester 2026 fee – last date 5 November",
        "body": """Dear Student,

This is a reminder that the tuition fee for the odd semester 2026 has not yet been received for your account.

Amount due: ₹1,12,500
Last date without fine: Thursday, 5 November 2026
A late fee of ₹100 per day applies after the last date.

You can pay online through the student portal (Fees > Pay Now) or at the bank counter in the Admin Block. Please ignore this email if you have paid in the last 48 hours.

Accounts Section""",
    },
    # ------------------------------------------------------------ classmate asks for notes
    {
        "id": "demo-08",
        "human_label": "Routine",
        "from": "Sneha Reddy <sneha.reddy@mail.example>",
        "date": ist(2026, 10, 24, 19, 5),
        "subject": "OS notes from Friday?",
        "body": """Hi!

I couldn't come on Friday, had a fever 🤒 Could you share the OS notes when you get a chance? Especially the page replacement part, Sir said it'll come in the quiz.

Thanks a ton!
Sneha""",
    },
    # ------------------------------------------------------------ club announcement (HTML + text, emoji subject)
    {
        "id": "demo-09",
        "human_label": "Routine",
        "from": "Music Club <musicclub@clubs.university.example>",
        "date": ist(2026, 10, 26, 12, 30),
        "subject": "🎸 Open Mic Night – this Friday, 6 PM at the Amphitheatre",
        "body": """Hey music lovers!

Open Mic Night is back this Friday at 6 PM at the Amphitheatre. Sing, play, do stand-up, recite poetry - anything goes. Each slot is 5 minutes.

Want to perform? Add your name to the sign-up sheet: https://clubs.university.example/music/openmic
Just want to listen? Bring your friends, there will be chai and samosas.

See you there,
Music Club""",
        "html": """<html><body>
<h2>🎸 Open Mic Night is back!</h2>
<p>This <b>Friday at 6 PM</b> at the <b>Amphitheatre</b>. Sing, play, do stand-up, recite poetry - anything goes.
Each slot is 5 minutes.</p>
<p><a href="https://clubs.university.example/music/openmic">Sign up to perform</a></p>
<p>Just want to listen? Bring your friends, there will be chai and samosas.</p>
<p>See you there,<br>Music Club</p>
<img src="https://clubs.university.example/track/open.gif" width="1" height="1">
</body></html>""",
    },
    # ------------------------------------------------------------ club newsletter with a real public link
    {
        "id": "demo-10",
        "human_label": "Routine",
        "from": "Coding Club <codingclub@clubs.university.example>",
        "date": ist(2026, 10, 25, 9, 0),
        "subject": "Weekly Byte #14: contest results and this week's read",
        "body": """Hi everyone,

Thanks to the 64 people who took part in Saturday's contest! Results are on the club notice board, and the top three get club T-shirts.

This week's read is about the protocol you keep meeting in your Computer Networks course - how TCP sets up a connection with the three-way handshake:
https://en.wikipedia.org/wiki/Transmission_Control_Protocol

Next session: Thursday, 5:30 PM, Lab 2 - intro to Git branching.

Happy coding,
Coding Club""",
    },
    # ------------------------------------------------------------ personal message from family
    {
        "id": "demo-11",
        "human_label": "Routine",
        "from": "Amma <lakshmi.devi@mail.example>",
        "date": ist(2026, 10, 25, 13, 20),
        "subject": "Deepavali",
        "body": """Kanna,

Are you coming home for Deepavali? Nanna wants to book the bus tickets this week before the prices go up. Tell me which day your exams finish.

Eat properly and don't skip breakfast. Call me tonight if you are free.

Amma""",
    },
    # ------------------------------------------------------------ library notice (automated)
    {
        "id": "demo-12",
        "human_label": "Routine",
        "from": "Central Library <library-noreply@university.example>",
        "date": ist(2026, 10, 26, 9, 10),
        "subject": "Book due in 3 days",
        "body": """Dear Demo Student,

The following item issued to you is due for return on Thursday, 29 October 2026:

Computer Networking: A Top-Down Approach (Kurose & Ross)
Accession no. 48211

You can renew the book once from the library portal if no one has reserved it. A fine of ₹2 per day is charged for late returns.

Central Library""",
    },
    # ------------------------------------------------------------ promotional spam (HTML only)
    {
        "id": "demo-13",
        "human_label": "Spam",
        "from": "ShopKart Deals <offers@shopkart-deals.example>",
        "date": ist(2026, 10, 26, 6, 2),
        "subject": "₹1 FLASH SALE 🔥 Wireless earbuds for ₹1 – today only!",
        "html": """<html><head><style>.btn{background:red;color:white}</style></head><body>
<h1>MEGA FLASH SALE</h1>
<p>Wireless earbuds for just <b>₹1</b>! Smartwatches at 90% OFF! Free delivery on every order.</p>
<p>Hurry - only 100 units. Offer ends at midnight.</p>
<p><a class="btn" href="https://shopkart-deals.example/flash?utm=email">SHOP NOW</a></p>
<p style="font-size:10px">You are receiving this because you subscribed to ShopKart offers.
<a href="https://shopkart-deals.example/unsubscribe">Unsubscribe</a></p>
<script>alert("this script must never run inside SmartMail")</script>
</body></html>""",
    },
    # ------------------------------------------------------------ phishing spam (HTML only)
    {
        "id": "demo-14",
        "human_label": "Spam",
        "from": "Account Security Team <kyc-update@secure-verify-alert.example>",
        "date": ist(2026, 10, 25, 23, 48),
        "subject": "KYC pending: your bank account will be blocked in 24 hours",
        "html": """<html><body>
<p>Dear Customer,</p>
<p>Your KYC verification is pending. Your account will be <b>BLOCKED</b> within 24 hours.</p>
<p>To avoid suspension, verify your account now and enter your debit card number and OTP:</p>
<p><a href="http://secure-verify-alert.example/kyc/login">VERIFY NOW</a></p>
<p>Regards,<br>Account Security Team</p>
</body></html>""",
    },
    # ------------------------------------------------------------ fake internship scam
    {
        "id": "demo-15",
        "human_label": "Spam",
        "from": "HR Desk <careers.hr.desk@jobs-hiring-now.example>",
        "date": ist(2026, 10, 23, 14, 12),
        "subject": "Congratulations! Selected for paid work-from-home internship",
        "body": """Dear Candidate,

Congratulations!!! Your profile has been selected for a PAID work-from-home internship. Earn ₹25,000 to ₹40,000 per month by working just 2 hours a day. No interview required.

To confirm your seat, pay the one-time registration fee of ₹999 within 24 hours using the link below. Seats are limited!

https://jobs-hiring-now.example/register-pay

HR Desk""",
    },
]

# A broken email, written directly in raw format on purpose: no Subject header,
# an invalid Date, only an email address as sender, and a link to a website that
# does not exist. It shows that SmartMail does not crash on bad data.
BROKEN_DEMO_EMAIL = {
    "id": "demo-16",
    "human_label": "Routine",
    "raw": (
        b"From: unknown.sender@mail.example\r\n"
        b"To: demo.student@university.example\r\n"
        b"Date: sometime last week\r\n"
        b"Message-ID: <demo-16@demo.smartmail>\r\n"
        b"X-SmartMail-Demo: true\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"pls check the file i sent on whatsapp. also see http://this-site-does-not-exist.example/report\r\n"
    ),
}

ALL_DEMO_EMAILS = DEMO_EMAILS + [BROKEN_DEMO_EMAIL]


def build_raw_email(demo):
    """Turn one demo email into a real email message (bytes), like the ones Gmail stores."""
    if "raw" in demo:
        return demo["raw"]

    message = EmailMessage()
    message["From"] = demo["from"]
    message["To"] = demo.get("to", DEMO_STUDENT)
    message["Subject"] = demo["subject"]
    message["Date"] = demo["date"]
    message["Message-ID"] = f"<{demo['id']}@demo.smartmail>"
    message["X-SmartMail-Demo"] = "true"   # marks the message as demo data

    if demo.get("body"):
        message.set_content(demo["body"])                     # plain-text version
        if demo.get("html"):
            message.add_alternative(demo["html"], subtype="html")   # + HTML version
    else:
        message.set_content(demo["html"], subtype="html")     # HTML-only email

    for filename, main_type, sub_type, data in demo.get("attachments", []):
        message.add_attachment(data, maintype=main_type, subtype=sub_type, filename=filename)
    return message.as_bytes()


def get_demo_ids():
    return [demo["id"] for demo in ALL_DEMO_EMAILS]


def get_demo_raw(demo_id):
    """Return the raw message for one demo email, or None if the id does not exist."""
    for demo in ALL_DEMO_EMAILS:
        if demo["id"] == demo_id:
            return build_raw_email(demo)
    return None


# Compare the classifier with our own opinion:  python demo_emails.py
if __name__ == "__main__":
    from email_classifier import classify_email
    from email_parser import parse_raw_email

    agree = 0
    print("DEMO DATA check: model prediction vs. our own label (human_label)\n")
    for demo in ALL_DEMO_EMAILS:
        email = parse_raw_email(build_raw_email(demo))
        category, confidence = classify_email(email["subject"], email["body"])
        same = category == demo["human_label"]
        agree += same
        print(f"{demo['id']}  model={category:<10} ({confidence:4.0%})  ours={demo['human_label']:<10}"
              f" {'OK ' if same else 'DIFF'}  {email['subject'][:55] or '(no subject)'}")
    print(f"\nModel agrees with our label on {agree} of {len(ALL_DEMO_EMAILS)} demo emails.")
