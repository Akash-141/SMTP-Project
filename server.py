# server.py
import os
import time
from datetime import datetime
from email import policy
from email.parser import BytesParser

# Use aiosmtpd for Python 3.12+ (smtpd removed in 3.12)
from aiosmtpd.controller import Controller

MAILBOX_DIR = "inbox"  # ensure this folder exists

class SMTPHandler:
    async def handle_DATA(self, server, session, envelope):
        """Handle incoming DATA from a client (envelope.content is bytes)."""
        print("📩 নতুন মেইল এসেছে:", datetime.now().isoformat())
        raw = envelope.content
        try:
            msg = BytesParser(policy=policy.default).parsebytes(raw)

            for rcpt in envelope.rcpt_tos:
                safe_rcpt = rcpt.replace("@", "_at_").replace(".", "_")
                rec_folder = os.path.join(MAILBOX_DIR, safe_rcpt)
                os.makedirs(rec_folder, exist_ok=True)

                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                eml_path = os.path.join(rec_folder, f"mail_{ts}.eml")
                with open(eml_path, "wb") as f:
                    f.write(raw)

                body_path = os.path.join(rec_folder, f"body_{ts}.txt")
                with open(body_path, "w", encoding="utf-8") as f:
                    f.write(f"From: {envelope.mail_from}\n")
                    f.write(f"To: {', '.join(envelope.rcpt_tos)}\n")
                    subj = msg.get('subject', '')
                    f.write(f"Subject: {subj}\n\n")

                    text = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            ctype = part.get_content_type()
                            if ctype == "text/plain" and part.get_content_disposition() is None:
                                try:
                                    text += part.get_content()
                                except Exception:
                                    pass
                    else:
                        try:
                            text = msg.get_content()
                        except Exception:
                            text = ""

                    f.write(text if text else "[No plain text body]\n")

                for part in msg.iter_attachments():
                    filename = part.get_filename()
                    if not filename:
                        filename = f"attachment_{ts}"
                    att_path = os.path.join(rec_folder, f"{ts}__{filename}")
                    content = part.get_content()
                    if isinstance(content, str):
                        content = content.encode("utf-8")
                    with open(att_path, "wb") as af:
                        af.write(content)

            print("✅ সেভ হয়েছে inbox ফোল্ডারে।")
        except Exception as e:
            print("❌ প্রসেসিংয়ে সমস্যা:", e)

        return '250 Message accepted for delivery'

if __name__ == "__main__":
    os.makedirs(MAILBOX_DIR, exist_ok=True)
    handler = SMTPHandler()
    # Use port 2525 to avoid conflicts with privileged or system services
    controller = Controller(handler, hostname="localhost", port=2525)
    controller.start()
    print("📡 SMTP Server চালু হয়েছে — localhost:2525")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()
        print("\n🛑 Server বন্ধ করা হয়েছে।")
