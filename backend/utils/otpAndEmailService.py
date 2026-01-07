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
@csrf_exempt
def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def get_otp_email_message(otp)->str:
    """Generate the email message with OTP"""
    html_message = f"""
            <html>
              <body style="font-family: 'Segoe UI', sans-serif; background-color: #f9f9f9; padding: 20px; color: #333;">
                <div style="max-width: 600px; margin: auto; background-color: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                  <h2 style="color: #2E8B57; border-bottom: 1px solid #eee; padding-bottom: 10px;">Farmo Security Notification</h2>

                  <p>Hello,</p>
                  <p>We received a request to reset your Farmo account password.</p>

                  <p style="font-size: 18px; margin: 20px 0;">
                    <strong>Your OTP code:</strong><br>
                    <span style="font-size: 28px; font-weight: bold; color: #2E8B57;">{otp}</span><br>
                    <em>(Expires in 10 minutes)</em>
                  </p>

                  <p>If you did not request this, please ignore the message or contact support immediately.</p>

                  <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">

                  <p style="font-size: 0.9em; color: #777;">
                    Farmo will never ask for your password or financial details via email. If you receive suspicious messages, do not click any links and report them to our support team.
                  </p>
                </div>
              </body>
            </html>
            """,
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