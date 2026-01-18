import random
import string
from django.core.mail import EmailMessage
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render


##########################################################################################
#                            OTP for forget Password
##########################################################################################

def generate_otp():
    """Generate a 6-digit OTP"""

    return ''.join(random.choices(string.digits, k=6))

def get_otp_email_message(otp)->str:
    """Generate the email message with OTP"""
    html_message = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f4f4f4;
                margin: 0;
                padding: 0;
                -webkit-font-smoothing: antialiased;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background-color: #ffffff;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            }}
            .content {{
                padding: 40px;
                color: #333333;
                line-height: 1.6;
            }}
            .header-title {{
                color: #2E8B57;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
                border-bottom: 2px solid #f0f0f0;
                padding-bottom: 10px;
            }}
            .otp-container {{
                background-color: #f9f9f9;
                border: 1px dashed #2E8B57;
                border-radius: 6px;
                padding: 20px;
                margin: 25px 0;
                text-align: center;
            }}
            .otp-code {{
                font-size: 36px;
                font-weight: bold;
                color: #2E8B57;
                letter-spacing: 5px;
                display: block;
            }}
            .expiry-text {{
                font-size: 14px;
                color: #777777;
                font-style: italic;
            }}
            .footer {{
                background-color: #fafafa;
                padding: 20px 40px;
                font-size: 12px;
                color: #999999;
                border-top: 1px solid #eeeeee;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="content">
                <div class="header-title">Farmo Security Notification</div>
                
                <p>Hello,</p>
                <p>We received a request to reset your Farmo account password. Please use the following One-Time Password (OTP) to proceed:</p>
                
                <div class="otp-container">
                    <span class="otp-code">{otp}</span>
                    <span class="expiry-text">(This code expires in 10 minutes)</span>
                </div>
                
                <p>If you did not request this password reset, you can safely ignore this email. Your password will remain unchanged.</p>
            </div>
            
            <div class="footer">
                Farmo will never ask for your password or financial details via email. 
                If you receive suspicious messages, do not click any links and report them to our support team.
                <br><br>
                &copy; 2026 Farmo Inc.
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_message


# Send otp to email 
def send_otp_to_email(email):
    """Send OTP to the specified email"""
    otp = generate_otp()
    
    try:
        email_obj = EmailMessage(
        subject = "Farmo OTP Verification",
        body=get_otp_email_message(otp),
        from_email=settings.EMAIL_HOST_USER,
        to=[email]
        )
        email_obj.content_subtype = 'html'
        email_obj.send()
        return [True, otp]
    except Exception as e:
        return [False, str(e)]

##########################################################################################
#                            OTP for forget Password
##########################################################################################