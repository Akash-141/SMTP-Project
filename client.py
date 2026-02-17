# client_gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import smtplib
from email.message import EmailMessage
import os

INBOX_DIR = "inbox"  # same as server

class SMTPApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SMTP Lab - GUI Client")
        self.geometry("800x600")
        self.attachments = []

        # Top frame: inputs
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=False)

        ttk.Label(frm, text="Sender:").grid(row=0, column=0, sticky=tk.W)
        self.sender_entry = ttk.Entry(frm, width=40)
        self.sender_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(frm, text="Recipients (comma-separated):").grid(row=1, column=0, sticky=tk.W)
        self.rec_entry = ttk.Entry(frm, width=60)
        self.rec_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2, columnspan=2)

        ttk.Label(frm, text="Subject:").grid(row=2, column=0, sticky=tk.W)
        self.subj_entry = ttk.Entry(frm, width=60)
        self.subj_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2, columnspan=2)

        ttk.Label(frm, text="Body:").grid(row=3, column=0, sticky=tk.NW)
        self.body_text = tk.Text(frm, width=70, height=12)
        self.body_text.grid(row=3, column=1, padx=5, pady=2, columnspan=2)

        # attachments
        self.attach_label = ttk.Label(frm, text="Attachments: (0)")
        self.attach_label.grid(row=4, column=1, sticky=tk.W, padx=5)
        ttk.Button(frm, text="Add Attachment", command=self.add_attachment).grid(row=4, column=2, sticky=tk.W)

        # action buttons
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Send", command=self.send_email).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="View Inbox", command=self.open_inbox_viewer).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear", command=self.clear_form).pack(side=tk.LEFT, padx=5)

        # status area
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def add_attachment(self):
        files = filedialog.askopenfilenames(title="Select attachments")
        if files:
            self.attachments.extend(files)
            self.attach_label.config(text=f"Attachments: ({len(self.attachments)})")

    def clear_form(self):
        self.sender_entry.delete(0, tk.END)
        self.rec_entry.delete(0, tk.END)
        self.subj_entry.delete(0, tk.END)
        self.body_text.delete("1.0", tk.END)
        self.attachments = []
        self.attach_label.config(text="Attachments: (0)")
        self.status_var.set("Cleared form")

    def send_email(self):
        sender = self.sender_entry.get().strip()
        recs = [r.strip() for r in self.rec_entry.get().split(",") if r.strip()]
        subject = self.subj_entry.get().strip()
        body = self.body_text.get("1.0", tk.END).strip()

        if not sender or not recs:
            messagebox.showwarning("Missing", "Sender and at least one recipient are required.")
            return

        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = ", ".join(recs)
        msg["Subject"] = subject
        msg.set_content(body if body else "")

        # Attach files
        for path in self.attachments:
            try:
                with open(path, "rb") as f:
                    data = f.read()
                maintype = "application"
                # try to guess a subtype from extension (simple)
                ext = os.path.splitext(path)[1].lower().replace(".", "")
                subtype = ext if ext else "octet-stream"
                fname = os.path.basename(path)
                msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=fname)
            except Exception as e:
                print("Attachment error:", e)

        self.status_var.set("Connecting to server...")
        try:
            # connect to local test SMTP server (port 2525)
            with smtplib.SMTP("localhost", 2525, timeout=10) as smtp:
                smtp.send_message(msg)
            self.status_var.set("✅ Email has been sent!")
            messagebox.showinfo("Success", "Email sent successfully!")
        except Exception as e:
            self.status_var.set("❌ Problem occurs: " + str(e))
            messagebox.showerror("Error", f"Failed to send email:\n{e}")

    def open_inbox_viewer(self):
        InboxViewer(self)

class InboxViewer(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Inbox Viewer")
        self.geometry("900x600")

        left = ttk.Frame(self, padding=8)
        left.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(left, text="Recipients (folders):").pack(anchor=tk.W)
        self.listbox = tk.Listbox(left, width=40, height=30)
        self.listbox.pack(fill=tk.Y)
        self.listbox.bind("<<ListboxSelect>>", self.on_select_recipient)

        middle = ttk.Frame(self, padding=8)
        middle.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(middle, text="Mails:").pack(anchor=tk.W)
        self.mail_list = tk.Listbox(middle, width=50, height=30)
        self.mail_list.pack()
        self.mail_list.bind("<<ListboxSelect>>", self.on_select_mail)

        right = ttk.Frame(self, padding=8)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(right, text="Content:").pack(anchor=tk.W)
        self.content_text = tk.Text(right, wrap=tk.WORD)
        self.content_text.pack(fill=tk.BOTH, expand=True)

        self.load_recipients()

    def load_recipients(self):
        self.listbox.delete(0, tk.END)
        if not os.path.isdir(INBOX_DIR):
            return
        for name in sorted(os.listdir(INBOX_DIR)):
            path = os.path.join(INBOX_DIR, name)
            if os.path.isdir(path):
                self.listbox.insert(tk.END, name)

    def on_select_recipient(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        name = self.listbox.get(sel[0])
        rec_folder = os.path.join(INBOX_DIR, name)
        files = sorted(os.listdir(rec_folder))
        self.mail_list.delete(0, tk.END)
        # show only body or eml files
        for f in files:
            self.mail_list.insert(tk.END, f)

    def on_select_mail(self, event):
        sel = self.listbox.curselection()
        mail_sel = self.mail_list.curselection()
        if not sel or not mail_sel:
            return
        rec = self.listbox.get(sel[0])
        fname = self.mail_list.get(mail_sel[0])
        path = os.path.join(INBOX_DIR, rec, fname)
        try:
            # if binary (attachment), show info
            with open(path, "rb") as f:
                data = f.read()
            # try decode as utf-8
            try:
                text = data.decode("utf-8")
            except Exception:
                text = f"[Binary file: {fname}] ({len(data)} bytes)\n\nFile path:\n{path}"
            self.content_text.delete("1.0", tk.END)
            self.content_text.insert(tk.END, text)
        except Exception as e:
            self.content_text.delete("1.0", tk.END)
            self.content_text.insert(tk.END, f"Cannot open file: {e}")

if __name__ == "__main__":
    app = SMTPApp()
    app.mainloop()

