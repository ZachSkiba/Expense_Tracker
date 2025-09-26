# debug_email_test.py - Enhanced email testing with more debugging

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv(dotenv_path='.env.dev')

def debug_email_test():
    """Enhanced email test with debugging"""
    
    # Get email settings
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    from_email = os.getenv('FROM_EMAIL', smtp_username)
    from_name = os.getenv('FROM_NAME', 'Expense Tracker')
    
    print("🔧 DEBUGGING EMAIL CONFIGURATION")
    print("=" * 50)
    print(f"SMTP Server: {smtp_server}")
    print(f"SMTP Port: {smtp_port}")
    print(f"Username: {smtp_username}")
    print(f"From Email: {from_email}")
    print(f"From Name: {from_name}")
    print(f"Password Length: {len(smtp_password) if smtp_password else 0} characters")
    print(f"Password Format: {'Has spaces' if smtp_password and ' ' in smtp_password else 'No spaces'}")
    print()
    
    # Check for common issues
    issues = []
    
    if smtp_server == 'smtp.gmail.com':
        print("📧 GMAIL DETECTED - Requirements:")
        print("✓ 2-Factor Authentication must be enabled")
        print("✓ App Password must be generated from Gmail settings")
        print("✓ App Password should be 16 characters, no spaces")
        if smtp_password and ' ' in smtp_password:
            issues.append("Password contains spaces - remove them!")
        if smtp_password and len(smtp_password.replace(' ', '').replace('-', '')) != 16:
            issues.append(f"App password should be 16 characters (yours is {len(smtp_password.replace(' ', '').replace('-', ''))})")
    
    if issues:
        print("\n⚠️ POTENTIAL ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
        print()
    
    # Test different email addresses
    test_emails = []
    
    # Ask for primary test email
    primary_email = input("Enter your primary email to test: ").strip()
    if primary_email:
        test_emails.append(primary_email)
    
    # Suggest testing Gmail as well
    if smtp_username and smtp_username not in test_emails:
        use_gmail = input(f"Also test sending to your Gmail ({smtp_username})? (y/n): ").strip().lower()
        if use_gmail == 'y':
            test_emails.append(smtp_username)
    
    if not test_emails:
        print("❌ No test emails provided")
        return
    
    # Test each email
    for test_email in test_emails:
        print(f"\n📨 Testing email to: {test_email}")
        print("-" * 40)
        
        try:
            # Create simple test email
            msg = MIMEText(f"""
🧪 EMAIL TEST - {time.strftime('%Y-%m-%d %H:%M:%S')}

Hello! This is a test email from your Expense Tracker app.

Configuration tested:
- SMTP Server: {smtp_server}
- From: {from_email}
- To: {test_email}
- Time: {time.strftime('%Y-%m-%d %H:%M:%S')}

If you received this email, your configuration is working!

Check your spam folder if this email seems delayed.

Best regards,
Expense Tracker Test System
            """)
            
            msg['Subject'] = f"🧪 Email Test - {time.strftime('%H:%M:%S')}"
            msg['From'] = f"{from_name} <{from_email}>"
            msg['To'] = test_email
            
            print("📤 Connecting to SMTP server...")
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                # Enable debug output
                server.set_debuglevel(1)
                
                print("🔐 Starting TLS...")
                server.starttls()
                
                print("🔑 Authenticating...")
                # Clean password (remove spaces)
                clean_password = smtp_password.replace(' ', '').replace('-', '')
                server.login(smtp_username, clean_password)
                
                print("📨 Sending email...")
                result = server.send_message(msg)
                
                print(f"✅ Email sent to {test_email}")
                if result:
                    print(f"⚠️ Some recipients failed: {result}")
                else:
                    print("✅ All recipients successful")
                
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ Authentication failed for {test_email}")
            print(f"Error: {e}")
            print("\n🔧 GMAIL TROUBLESHOOTING:")
            print("1. Go to https://myaccount.google.com/apppasswords")
            print("2. Generate a new app password")
            print("3. Use the 16-character password (no spaces)")
            print("4. Make sure 2FA is enabled")
            
        except smtplib.SMTPRecipientsRefused as e:
            print(f"❌ Recipient {test_email} was refused")
            print(f"Error: {e}")
            print("This might be due to:")
            print("- Invalid email address")
            print("- Recipient's email server blocking")
            print("- University email filters")
            
        except Exception as e:
            print(f"❌ Error sending to {test_email}: {e}")
    
    print("\n" + "="*50)
    print("🔍 EMAIL DELIVERY TIPS:")
    print("1. Check spam/junk folders")
    print("2. University emails often have strict filters")
    print("3. Try sending to your Gmail account first")
    print("4. Wait a few minutes - some servers are slow")
    print("5. Check Gmail 'Sent' folder to confirm sending")

if __name__ == "__main__":
    print("🚀 EMAIL DEBUGGING TOOL")
    print("=" * 30)
    
    choice = input("Choose option:\n1. Debug email test: ").strip()
    
    if choice == "1":
        debug_email_test()
    else:
        print("Invalid choice")