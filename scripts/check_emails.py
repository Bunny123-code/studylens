import os
import sys
import time
import pickle
import base64
import re
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

from backend.models import db, PaymentRequest, User
from backend.app import create_app

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    token_path = 'token.pickle'
    creds_path = 'credentials.json'

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def extract_payment_info(email_body, account_number):
    # Extract amount (e.g., "PKR 500" or "Rs. 500")
    amount_match = re.search(r'(?:PKR|Rs\.?)\s*([\d,]+\.?\d*)', email_body, re.IGNORECASE)
    amount = None
    if amount_match:
        amount = float(amount_match.group(1).replace(',', ''))

    # Extract reference code (e.g., "Reference: SL-ABC123")
    ref_match = re.search(r'Reference:\s*([A-Z0-9\-]+)', email_body, re.IGNORECASE)
    reference = ref_match.group(1) if ref_match else None

    # Optional: verify account number appears in email
    if account_number and account_number not in email_body.replace('-', '').replace(' ', ''):
        return None, None

    return amount, reference

def process_emails():
    app = create_app()
    with app.app_context():
        service = get_gmail_service()
        account_number = os.getenv('ACCOUNT_NUMBER', '').replace('-', '').replace(' ', '')

        # Query unread emails from Meezan Bank alerts (adjust sender if needed)
        query = f'from:alerts@meezanbank.com is:unread after:{int((datetime.now() - timedelta(minutes=10)).timestamp())}'
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])

        for msg in messages:
            message = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            payload = message['payload']
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode()
                        break
            else:
                data = payload['body']['data']
                body = base64.urlsafe_b64decode(data).decode()

            amount, ref = extract_payment_info(body, account_number)
            if amount and ref:
                pending = PaymentRequest.query.filter_by(reference_code=ref, amount=amount, status='pending').first()
                if pending:
                    pending.status = 'completed'
                    pending.completed_at = datetime.utcnow()
                    user = User.query.get(pending.user_id)
                    if user:
                        user.is_premium = True
                        if pending.plan == 'monthly':
                            user.subscription_expiry = datetime.utcnow() + timedelta(days=30)
                        else:
                            user.subscription_expiry = datetime.utcnow() + timedelta(days=365)
                    db.session.commit()
                    print(f"✅ Activated user {pending.user_id} for plan {pending.plan}")

            # Mark email as read
            service.users().messages().modify(userId='me', id=msg['id'], body={'removeLabelIds': ['UNREAD']}).execute()

if __name__ == '__main__':
    while True:
        try:
            process_emails()
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(120)  # Check every 2 minutes
