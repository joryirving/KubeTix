"""
KubeTix Backend API
FastAPI-based REST API for KubeTix
"""

import secrets
import sqlite3
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import create_engine, Column, String, Boolean, Text, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import func

# Configuration
SECRET_KEY = os.environ.get("KUBETIX_SECRET_KEY") or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Database
DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///./kubetix.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI app
app = FastAPI(
    title="KubeTix API",
    description="Temporary Kubernetes Access Manager",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=secrets.token_urlsafe(16))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # NULL for SSO users
    full_name = Column(String(255))
    is_admin = Column(Boolean, default=False)
    sso_provider = Column(String(50), nullable=True)  # google, github, okta, etc.
    sso_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


class Team(Base):
    __tablename__ = "teams"
    
    id = Column(String(36), primary_key=True, default=secrets.token_urlsafe(16))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


class TeamMember(Base):
    __tablename__ = "team_members"
    
    id = Column(String(36), primary_key=True, default=secrets.token_urlsafe(16))
    team_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    role = Column(String(50), nullable=False)  # owner, admin, member
    joined_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    __table_args__ = (
        # Unique constraint: one role per user per team
        db.UniqueConstraint('team_id', 'user_id', name='uq_team_user'),
    )


class Grant(Base):
    __tablename__ = "grants"
    
    id = Column(String(36), primary_key=True, default=secrets.token_urlsafe(16))
    user_id = Column(String(36), nullable=False)
    cluster_name = Column(String(255), nullable=False)
    namespace = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False)
    encrypted_kubeconfig = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(String(36), primary_key=True, default=secrets.token_urlsafe(16))
    user_id = Column(String(36), nullable=False)
    grant_id = Column(String(36), nullable=True)
    action = Column(String(50), nullable=False)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


# Pydantic Models
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class GrantCreate(BaseModel):
    cluster_name: str
    namespace: Optional[str] = None
    role: str = "view"
    expiry_hours: int = 4


class GrantResponse(BaseModel):
    id: str
    cluster_name: str
    namespace: Optional[str] = None
    role: str
    expires_at: datetime
    revoked: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class GrantWithKubeconfig(BaseModel):
    id: str
    cluster_name: str
    namespace: Optional[str] = None
    role: str
    expires_at: datetime
    kubeconfig: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# Team Models
class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TeamResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class TeamMemberCreate(BaseModel):
    email: str
    role: str = "member"  # owner, admin, member


class TeamMemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    full_name: Optional[str] = None
    role: str
    joined_at: datetime
    
    class Config:
        from_attributes = True


# Database Functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)


# Authentication Functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(lambda: None),
    db: Session = Depends(get_db)
):
    # Extract token from header
    if token and token.startswith("Bearer "):
        token = token[7:]
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


# API Endpoints
@app.on_event("startup")
async def startup_event():
    init_db()
    # Create admin user if not exists
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@kubetix.local").first()
        if not admin:
            admin = User(
                id=secrets.token_urlsafe(16),
                email="admin@kubetix.local",
                hashed_password=get_password_hash("admin123"),
                full_name="Admin User",
                is_admin=True
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        id=secrets.token_urlsafe(16),
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_admin=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@app.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@app.get("/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/grants", response_model=List[GrantResponse])
async def list_grants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    grants = db.query(Grant).filter(
        Grant.user_id == current_user.id,
        Grant.revoked == False,
        Grant.expires_at > datetime.now(timezone.utc)
    ).order_by(Grant.created_at.desc()).all()
    
    return grants


@app.post("/grants", response_model=GrantResponse, status_code=status.HTTP_201_CREATED)
async def create_grant(
    grant_data: GrantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate role
    if grant_data.role not in ["view", "edit", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be view, edit, or admin"
        )
    
    # Validate expiry
    if grant_data.expiry_hours < 1 or grant_data.expiry_hours > 720:  # 1 hour to 30 days
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expiry must be between 1 and 720 hours"
        )
    
    # Get kubeconfig
    kubeconfig_path = os.environ.get("KUBECONFIG", Path.home() / ".kube" / "config")
    
    if not os.path.exists(kubeconfig_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Kubeconfig not found at {kubeconfig_path}"
        )
    
    with open(kubeconfig_path) as f:
        kubeconfig = f.read()
    
    # Encrypt kubeconfig (simple base64 for demo, use Fernet in production)
    import base64
    encrypted_kubeconfig = base64.b64encode(kubeconfig.encode()).decode()
    
    # Create grant
    expires_at = datetime.now(timezone.utc) + timedelta(hours=grant_data.expiry_hours)
    
    new_grant = Grant(
        id=secrets.token_urlsafe(16),
        user_id=current_user.id,
        cluster_name=grant_data.cluster_name,
        namespace=grant_data.namespace,
        role=grant_data.role,
        encrypted_kubeconfig=encrypted_kubeconfig,
        expires_at=expires_at
    )
    
    db.add(new_grant)
    
    # Log audit
    audit = AuditLog(
        user_id=current_user.id,
        grant_id=new_grant.id,
        action="created",
        details=f"Created grant for {grant_data.cluster_name}"
    )
    db.add(audit)
    
    db.commit()
    db.refresh(new_grant)
    
    return new_grant


@app.get("/grants/{grant_id}/download", response_model=GrantWithKubeconfig)
async def download_grant(
    grant_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    grant = db.query(Grant).filter(Grant.id == grant_id).first()
    
    if not grant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grant not found"
        )
    
    if grant.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this grant"
        )
    
    if grant.revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grant has been revoked"
        )
    
    if datetime.now(timezone.utc) > grant.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grant has expired"
        )
    
    # Decrypt kubeconfig
    import base64
    kubeconfig = base64.b64decode(grant.encrypted_kubeconfig).decode()
    
    return {
        "id": grant.id,
        "cluster_name": grant.cluster_name,
        "namespace": grant.namespace,
        "role": grant.role,
        "expires_at": grant.expires_at,
        "kubeconfig": kubeconfig
    }


@app.delete("/grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_grant(
    grant_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    grant = db.query(Grant).filter(Grant.id == grant_id).first()
    
    if not grant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grant not found"
        )
    
    # Only owner or admin can revoke
    if grant.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to revoke this grant"
        )
    
    grant.revoked = True
    db.commit()
    
    # Log audit
    audit = AuditLog(
        user_id=current_user.id,
        grant_id=grant_id,
        action="revoked",
        details="Manually revoked"
    )
    db.add(audit)
    db.commit()


@app.get("/audit", response_model=List[dict])
async def get_audit_log(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Admins see all logs, users see their own
    if current_user.is_admin:
        logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    else:
        logs = db.query(AuditLog).filter(
            AuditLog.user_id == current_user.id
        ).order_by(AuditLog.created_at.desc()).limit(100).all()
    
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "grant_id": log.grant_id,
            "action": log.action,
            "details": log.details,
            "created_at": log.created_at
        }
        for log in logs
    ]


# Team Endpoints
@app.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_team = Team(
        id=secrets.token_urlsafe(16),
        name=team_data.name,
        description=team_data.description,
        created_by=current_user.id
    )
    
    db.add(new_team)
    
    # Add creator as owner
    member = TeamMember(
        id=secrets.token_urlsafe(16),
        team_id=new_team.id,
        user_id=current_user.id,
        role="owner"
    )
    db.add(member)
    
    db.commit()
    db.refresh(new_team)
    
    return new_team


@app.get("/teams", response_model=List[TeamResponse])
async def list_teams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get all teams user is a member of
    from sqlalchemy import and_
    
    team_ids = db.query(TeamMember.team_id).filter(
        TeamMember.user_id == current_user.id
    ).subquery()
    
    teams = db.query(Team).filter(
        Team.id.in_(team_ids)
    ).order_by(Team.created_at.desc()).all()
    
    return teams


@app.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    team = db.query(Team).filter(Team.id == team_id).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Check if user is member
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this team"
        )
    
    return team


@app.post("/teams/{team_id}/members", response_model=TeamMemberResponse)
async def add_team_member(
    team_id: str,
    member_data: TeamMemberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user is owner or admin of team
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id
    ).first()
    
    if not member or member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team owners and admins can add members"
        )
    
    # Find user by email
    target_user = db.query(User).filter(User.email == member_data.email).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already a member
    existing = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == target_user.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this team"
        )
    
    # Add member
    new_member = TeamMember(
        id=secrets.token_urlsafe(16),
        team_id=team_id,
        user_id=target_user.id,
        role=member_data.role
    )
    
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    
    return new_member


@app.delete("/teams/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user is owner of team
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id
    ).first()
    
    if not member or member.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team owners can remove members"
        )
    
    # Can't remove yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the team"
        )
    
    # Remove member
    db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id
    ).delete()
    
    db.commit()


@app.get("/teams/{team_id}/members", response_model=List[TeamMemberResponse])
async def list_team_members(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user is member
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this team"
        )
    
    members = db.query(TeamMember).filter(
        TeamMember.team_id == team_id
    ).join(User, TeamMember.user_id == User.id).all()
    
    return members


# SSO/Authentik/OIDC Endpoints
@app.post("/auth/sso/callback")
async def sso_callback(
    provider: str,
    code: str,
    db: Session = Depends(get_db)
):
    """
    Handle SSO callback from OAuth/OIDC provider.
    Supports: Google, GitHub, Okta, Azure AD, Authentik
    """
    # This endpoint receives the OAuth code and exchanges it for tokens
    # In production, integrate with provider's OAuth/OIDC endpoint
    
    return {
        "message": f"SSO callback from {provider}",
        "supported_providers": ["google", "github", "okta", "azure-ad", "authentik"]
    }


@app.get("/auth/sso/{provider}/login")
async def sso_login(provider: str):
    """
    Initiate SSO login flow.
    Returns the OAuth authorization URL to redirect the user to.
    """
    providers = {
        "google": "https://accounts.google.com/o/oauth2/v2/auth",
        "github": "https://github.com/login/oauth/authorize",
        "okta": "{your-okta-domain}/oauth2/v1/authorize",
        "azure-ad": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
        "authentik": "https://authentik.yourdomain.com/application/o/authorize/"
    }
    
    if provider not in providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider. Supported: {list(providers.keys())}"
        )
    
    return {
        "provider": provider,
        "auth_url": providers[provider],
        "message": "Redirect user to auth_url"
    }


@app.post("/auth/oidc/callback")
async def oidc_callback(
    code: str,
    db: Session = Depends(get_db)
):
    """
    Generic OIDC callback endpoint.
    Works with any OIDC provider (Authentik, Keycloak, Okta, etc.)
    """
    # Get OIDC configuration from environment
    oidc_issuer = os.environ.get("OIDC_ISSUER", "")
    oidc_client_id = os.environ.get("OIDC_CLIENT_ID", "")
    oidc_client_secret = os.environ.get("OIDC_CLIENT_SECRET", "")
    
    if not all([oidc_issuer, oidc_client_id, oidc_client_secret]):
        raise HTTPException(
            status_code=status.HTTP_500_BAD_REQUEST,
            detail="OIDC not configured. Set OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET"
        )
    
    # In production:
    # 1. Exchange code for tokens at {issuer}/oauth/token
    # 2. Get user info from {issuer}/oauth/userinfo
    # 3. Create or update user in database
    # 4. Return JWT token
    
    return {
        "message": "OIDC callback received",
        "issuer": oidc_issuer,
        "client_id": oidc_client_id
    }


@app.get("/auth/oidc/login")
async def oidc_login():
    """
    Initiate OIDC login with configured provider.
    Redirects to the OIDC provider's authorization endpoint.
    """
    oidc_issuer = os.environ.get("OIDC_ISSUER", "")
    oidc_client_id = os.environ.get("OIDC_CLIENT_ID", "")
    
    if not oidc_issuer or not oidc_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_BAD_REQUEST,
            detail="OIDC not configured"
        )
    
    # Build authorization URL
    auth_url = f"{oidc_issuer}/application/o/authorize/"
    params = {
        "client_id": oidc_client_id,
        "redirect_uri": os.environ.get("OIDC_REDIRECT_URI", "http://localhost:8000/auth/oidc/callback"),
        "response_type": "code",
        "scope": "openid profile email",
    }
    
    import urllib.parse
    full_url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    
    return {
        "auth_url": full_url,
        "message": "Redirect user to auth_url"
    }


@app.get("/auth/oidc/userinfo")
async def oidc_userinfo(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user info with OIDC attributes.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "sso_provider": current_user.sso_provider,
        "is_admin": current_user.is_admin
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}
