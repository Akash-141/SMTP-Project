# web_server.py - WebSocket server for web-based SMTP client
import asyncio
import websockets
import json
import smtplib
import os
from email.message import EmailMessage
from datetime import datetime
import base64

INBOX_DIR = "inbox"
SMTP_HOST = "localhost"
SMTP_PORT = 2525

class WebSMTPHandler:
    def __init__(self):
        self.connected_clients = set()
    
    async def handle_client(self, websocket):
        """Handle WebSocket connections from web clients"""
        self.connected_clients.add(websocket)
        print(f"📱 New web client connected. Total: {len(self.connected_clients)}")
        
        try:
            await websocket.send(json.dumps({
                'type': 'connected',
                'message': 'Connected to SMTP Web Server'
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    if data['type'] == 'send_email':
                        await self.send_email(websocket, data)
                    
                    elif data['type'] == 'get_inbox':
                        await self.get_inbox(websocket)
                    
                    elif data['type'] == 'get_recipients':
                        await self.get_recipients(websocket)
                    
                    elif data['type'] == 'get_emails':
                        await self.get_emails(websocket, data['recipient'])
                    
                    elif data['type'] == 'get_email_content':
                        await self.get_email_content(websocket, data['recipient'], data['filename'])
                    
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Invalid JSON format'
                    }))
                except Exception as e:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': f'Error: {str(e)}'
                    }))
        
        except websockets.exceptions.ConnectionClosed:
            print("📱 Web client disconnected")
        finally:
            self.connected_clients.discard(websocket)
    
    async def send_email(self, websocket, data):
        """Send email via SMTP"""
        try:
            sender = data.get('sender', '').strip()
            recipients = [r.strip() for r in data.get('recipients', []) if r.strip()]
            subject = data.get('subject', '').strip()
            body = data.get('body', '').strip()
            attachments = data.get('attachments', [])
            
            if not sender or not recipients:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Sender and at least one recipient are required'
                }))
                return
            
            # Create email message
            msg = EmailMessage()
            msg["From"] = sender
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            msg.set_content(body if body else "")
            
            # Add attachments
            for attachment in attachments:
                try:
                    filename = attachment['name']
                    # Decode base64 content
                    file_data = base64.b64decode(attachment['data'].split(',')[1])
                    
                    # Determine MIME type
                    ext = os.path.splitext(filename)[1].lower().replace(".", "")
                    maintype = "application"
                    subtype = ext if ext else "octet-stream"
                    
                    msg.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=filename)
                except Exception as e:
                    print(f"Attachment error: {e}")
            
            # Send email
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
                smtp.send_message(msg)
            
            await websocket.send(json.dumps({
                'type': 'send_success',
                'message': '✅ Email sent successfully!',
                'timestamp': datetime.now().isoformat()
            }))
            
            # Broadcast to all clients that inbox updated
            await self.broadcast_inbox_update()
            
        except Exception as e:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Failed to send email: {str(e)}'
            }))
    
    async def get_recipients(self, websocket):
        """Get list of recipient folders"""
        try:
            if not os.path.isdir(INBOX_DIR):
                os.makedirs(INBOX_DIR, exist_ok=True)
            
            recipients = []
            for name in sorted(os.listdir(INBOX_DIR)):
                path = os.path.join(INBOX_DIR, name)
                if os.path.isdir(path):
                    # Count emails in folder
                    files = [f for f in os.listdir(path) if f.endswith('.txt') or f.endswith('.eml')]
                    recipients.append({
                        'name': name,
                        'count': len([f for f in files if f.endswith('.txt')])
                    })
            
            await websocket.send(json.dumps({
                'type': 'recipients',
                'data': recipients
            }))
        except Exception as e:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Error loading recipients: {str(e)}'
            }))
    
    async def get_emails(self, websocket, recipient):
        """Get list of emails for a recipient"""
        try:
            rec_folder = os.path.join(INBOX_DIR, recipient)
            if not os.path.isdir(rec_folder):
                await websocket.send(json.dumps({
                    'type': 'emails',
                    'recipient': recipient,
                    'data': []
                }))
                return
            
            files = sorted(os.listdir(rec_folder), reverse=True)
            email_list = []
            
            for f in files:
                if f.endswith('.txt') or f.endswith('.eml'):
                    # Extract timestamp from filename
                    timestamp = f.split('_')[1:4]
                    email_list.append({
                        'filename': f,
                        'display': f,
                        'isAttachment': False
                    })
                elif not f.startswith('body_') and not f.startswith('mail_'):
                    # It's an attachment
                    email_list.append({
                        'filename': f,
                        'display': f,
                        'isAttachment': True
                    })
            
            await websocket.send(json.dumps({
                'type': 'emails',
                'recipient': recipient,
                'data': email_list
            }))
        except Exception as e:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Error loading emails: {str(e)}'
            }))
    
    async def get_email_content(self, websocket, recipient, filename):
        """Get content of a specific email"""
        try:
            filepath = os.path.join(INBOX_DIR, recipient, filename)
            
            with open(filepath, 'rb') as f:
                data = f.read()
            
            # Try to decode as text
            try:
                content = data.decode('utf-8')
                is_binary = False
            except:
                content = f"[Binary file: {filename}]\nSize: {len(data)} bytes\n\nDownload path: {filepath}"
                is_binary = True
            
            await websocket.send(json.dumps({
                'type': 'email_content',
                'recipient': recipient,
                'filename': filename,
                'content': content,
                'is_binary': is_binary
            }))
        except Exception as e:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Error loading email content: {str(e)}'
            }))
    
    async def get_inbox(self, websocket):
        """Get full inbox overview"""
        await self.get_recipients(websocket)
    
    async def broadcast_inbox_update(self):
        """Notify all clients that inbox has been updated"""
        if self.connected_clients:
            message = json.dumps({
                'type': 'inbox_updated',
                'message': 'New email received'
            })
            await asyncio.gather(
                *[client.send(message) for client in self.connected_clients],
                return_exceptions=True
            )

async def main():
    handler = WebSMTPHandler()
    
    print("🌐 WebSocket SMTP Server starting on ws://localhost:8787")
    print("📧 Connecting to SMTP server at localhost:2525")
    print("📂 Inbox directory: inbox/")
    
    async with websockets.serve(handler.handle_client, "localhost", 8787):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Web server stopped")
