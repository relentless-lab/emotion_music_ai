"""Email service for sending verification codes."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings


def send_verification_code_email(to_email: str, code: str) -> bool:
    """
    Send verification code email using QQ邮箱 SMTP.
    
    Args:
        to_email: Recipient email address
        code: Verification code to send
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # QQ邮箱SMTP配置
        smtp_server = "smtp.qq.com"
        smtp_port = 587
        
        # 从配置获取发送邮箱和授权码
        from_email = settings.QQ_EMAIL
        password = settings.QQ_EMAIL_AUTH_CODE
        
        if not from_email or not password:
            return False
        
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = "注册验证码"
        
        # 邮件正文
        body = f"""
        您好！
        
        您的注册验证码是：{code}
        
        验证码有效期为10分钟，请勿泄露给他人。
        
        如果这不是您的操作，请忽略此邮件。
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 发送邮件
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # 启用TLS加密
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


