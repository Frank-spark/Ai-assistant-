"""User authentication and onboarding for SaaS platform."""

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.storage.db import get_db_session
from src.saas.models import User, Invitation
from src.config import get_settings

router = APIRouter(prefix="/auth", tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


class AuthService:
    """Service for user authentication and management."""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
    
    def create_user(self, email: str, password: str, first_name: str, last_name: str,
                   company_name: Optional[str] = None, role: Optional[str] = None,
                   invitation_token: Optional[str] = None) -> User:
        """Create a new user account."""
        
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Hash password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        # Create user
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
            role=role,
            is_active=True,
            is_verified=False,
            subscription_status="trial",
            plan_type="free"
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Process invitation if provided
        if invitation_token:
            self._process_invitation(user, invitation_token)
        
        # Send verification email
        self.send_verification_email(user)
        
        return user
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        
        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash):
            return None
        
        if not user.is_active:
            return None
        
        # Update last activity
        user.last_activity_at = datetime.utcnow()
        self.db.commit()
        
        return user
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token for user."""
        
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "exp": datetime.utcnow() + timedelta(days=7)
        }
        
        return jwt.encode(payload, self.settings.jwt_secret, algorithm="HS256")
    
    def verify_token(self, token: str) -> Optional[User]:
        """Verify JWT token and return user."""
        
        try:
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=["HS256"])
            user_id = payload.get("sub")
            if user_id is None:
                return None
            
            user = self.db.query(User).filter(User.id == int(user_id)).first()
            return user
            
        except jwt.PyJWTError:
            return None
    
    def send_verification_email(self, user: User) -> bool:
        """Send email verification link to user."""
        
        token = self._create_verification_token(user)
        verification_url = f"{self.settings.webhook_base_url}/auth/verify/{token}"
        
        subject = "Verify your Reflex AI Assistant account"
        body = f"""
        <html>
        <body>
            <h2>Welcome to Reflex AI Assistant!</h2>
            <p>Hi {user.first_name},</p>
            <p>Thank you for signing up for Reflex AI Assistant. To complete your registration, please verify your email address by clicking the link below:</p>
            <p><a href="{verification_url}" style="background-color: #4CAF50; color: white; padding: 14px 20px; text-decoration: none; border-radius: 4px;">Verify Email Address</a></p>
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p>{verification_url}</p>
            <p>This link will expire in 24 hours.</p>
            <p>Best regards,<br>The Reflex Team</p>
        </body>
        </html>
        """
        
        return self._send_email(user.email, subject, body)
    
    def send_password_reset_email(self, email: str) -> bool:
        """Send password reset email to user."""
        
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return False
        
        token = self._create_password_reset_token(user)
        reset_url = f"{self.settings.webhook_base_url}/auth/reset-password/{token}"
        
        subject = "Reset your Reflex AI Assistant password"
        body = f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>Hi {user.first_name},</p>
            <p>We received a request to reset your password for your Reflex AI Assistant account. Click the link below to create a new password:</p>
            <p><a href="{reset_url}" style="background-color: #4CAF50; color: white; padding: 14px 20px; text-decoration: none; border-radius: 4px;">Reset Password</a></p>
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p>{reset_url}</p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this password reset, you can safely ignore this email.</p>
            <p>Best regards,<br>The Reflex Team</p>
        </body>
        </html>
        """
        
        return self._send_email(user.email, subject, body)
    
    def verify_email_token(self, token: str) -> bool:
        """Verify email verification token."""
        
        try:
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=["HS256"])
            user_id = payload.get("user_id")
            token_type = payload.get("type")
            
            if token_type != "email_verification":
                return False
            
            user = self.db.query(User).filter(User.id == int(user_id)).first()
            if not user:
                return False
            
            user.is_verified = True
            user.email_verified_at = datetime.utcnow()
            self.db.commit()
            
            return True
            
        except jwt.PyJWTError:
            return False
    
    def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Reset password using reset token."""
        
        try:
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=["HS256"])
            user_id = payload.get("user_id")
            token_type = payload.get("type")
            
            if token_type != "password_reset":
                return False
            
            user = self.db.query(User).filter(User.id == int(user_id)).first()
            if not user:
                return False
            
            # Hash new password
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), salt)
            user.password_hash = hashed_password
            
            self.db.commit()
            return True
            
        except jwt.PyJWTError:
            return False
    
    def _create_verification_token(self, user: User) -> str:
        """Create email verification token."""
        
        payload = {
            "user_id": str(user.id),
            "type": "email_verification",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        
        return jwt.encode(payload, self.settings.jwt_secret, algorithm="HS256")
    
    def _create_password_reset_token(self, user: User) -> str:
        """Create password reset token."""
        
        payload = {
            "user_id": str(user.id),
            "type": "password_reset",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        return jwt.encode(payload, self.settings.jwt_secret, algorithm="HS256")
    
    def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email using configured SMTP settings."""
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.settings.smtp_username
            msg['To'] = to_email
            
            html_part = MIMEText(body, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                if self.settings.smtp_use_tls:
                    server.starttls()
                server.login(self.settings.smtp_username, self.settings.smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
    
    def _process_invitation(self, user: User, invitation_token: str) -> bool:
        """Process team invitation for new user."""
        
        invitation = self.db.query(Invitation).filter(
            Invitation.token == invitation_token,
            Invitation.is_accepted == False,
            Invitation.expires_at > datetime.utcnow()
        ).first()
        
        if not invitation:
            return False
        
        # Add user to team
        team_member = TeamMember(
            team_id=invitation.team_id,
            user_id=user.id,
            role=invitation.role
        )
        
        self.db.add(team_member)
        
        # Mark invitation as accepted
        invitation.is_accepted = True
        invitation.accepted_at = datetime.utcnow()
        
        self.db.commit()
        return True


# FastAPI routes
@router.post("/register")
async def register_user(
    email: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    company_name: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    invitation_token: Optional[str] = Form(None),
    db: Session = Depends(get_db_session)
):
    """Register a new user account."""
    
    auth_service = AuthService(db)
    
    try:
        user = auth_service.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
            role=role,
            invitation_token=invitation_token
        )
        
        return {
            "message": "Account created successfully. Please check your email to verify your account.",
            "user_id": user.id
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db_session)
):
    """Login user and return access token."""
    
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.is_verified:
        raise HTTPException(status_code=401, detail="Please verify your email address first")
    
    access_token = auth_service.create_access_token(user)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "company_name": user.company_name,
            "plan_type": user.plan_type
        }
    }


@router.get("/verify/{token}")
async def verify_email(token: str, db: Session = Depends(get_db_session)):
    """Verify email address with token."""
    
    auth_service = AuthService(db)
    
    if auth_service.verify_email_token(token):
        return RedirectResponse(url="/dashboard?verified=true")
    else:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")


@router.post("/forgot-password")
async def forgot_password(
    email: str = Form(...),
    db: Session = Depends(get_db_session)
):
    """Send password reset email."""
    
    auth_service = AuthService(db)
    
    if auth_service.send_password_reset_email(email):
        return {"message": "Password reset email sent successfully"}
    else:
        return {"message": "If an account with this email exists, a password reset email has been sent"}


@router.post("/reset-password/{token}")
async def reset_password(
    token: str,
    new_password: str = Form(...),
    db: Session = Depends(get_db_session)
):
    """Reset password with token."""
    
    auth_service = AuthService(db)
    
    if auth_service.reset_password_with_token(token, new_password):
        return {"message": "Password reset successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "company_name": current_user.company_name,
        "role": current_user.role,
        "plan_type": current_user.plan_type,
        "subscription_status": current_user.subscription_status,
        "is_verified": current_user.is_verified
    }


@router.post("/logout")
async def logout_user():
    """Logout user (client-side token removal)."""
    
    return {"message": "Logged out successfully"}


# Helper function for dependency injection
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db_session)
) -> User:
    """Get current authenticated user."""
    
    auth_service = AuthService(db)
    user = auth_service.verify_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is deactivated")
    
    return user 