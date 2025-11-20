import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_telegram_message(token, chat_id, message):
    """
    Sends a message to a Telegram chat.
    """
    if not token or not chat_id:
        return False, "Missing Token or Chat ID"
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return True, "Message sent successfully"
        else:
            return False, f"Failed to send: {response.text}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def send_email(smtp_server, port, sender_email, password, receiver_email, subject, body):
    """
    Sends an email using SMTP.
    """
    if not sender_email or not password or not receiver_email:
        return False, "Missing Email Credentials"
        
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        
        return True, "Email sent successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"

def format_setup_message(setup):
    """
    Formats a trade setup dictionary into a readable message.
    """
    icon = "🟢" if setup['Type'] == 'LONG' else "🔴"
    
    msg = f"{icon} *Trade Setup: {setup['Symbol']}*\n\n"
    msg += f"*Signal:* {setup['Signal']}\n"
    msg += f"*Price:* ${setup['Price']:.5f}\n"
    msg += f"*Entry:* ${setup['Entry']:.5f}\n"
    msg += f"*Stop Loss:* ${setup['Stop Loss']:.5f}\n"
    msg += f"*Take Profit:* ${setup['Take Profit']:.5f}\n\n"
    
    msg += "*DCA Levels:*\n"
    msg += f"1. ${setup['DCA 1']:.5f}\n"
    msg += f"2. ${setup['DCA 2']:.5f}\n"
    msg += f"3. ${setup['DCA 3']:.5f}\n\n"
    
    msg += f"*Confidence:* {setup['Confidence']:.1f}%\n"
    msg += f"_Reasons: {setup['Reasons']}_"
    
    return msg
