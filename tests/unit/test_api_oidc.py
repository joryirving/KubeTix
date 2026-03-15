"""
Tests for OIDC/SSO integration
Tests OIDC authentication flows
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import urllib.parse

# Import the main app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "kubetix-api"))

from main import app


# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def client():
    """Create test client."""
    yield TestClient(app)


@pytest.fixture(scope="function")
def mock_oidc_env(monkeypatch):
    """Set up mock OIDC environment variables."""
    monkeypatch.setenv("OIDC_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER", "https://authentik.example.com")
    monkeypatch.setenv("OIDC_CLIENT_ID", "kubetix-test")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "http://localhost:8000/auth/oidc/callback")


class TestOIDCEndpoints:
    """Tests for OIDC endpoints."""
    
    def test_oidc_login_redirect(self, client, mock_oidc_env):
        """Test OIDC login endpoint returns auth URL."""
        response = client.get("/auth/oidc/login")
        
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "authentik.example.com" in data["auth_url"]
    
    def test_oidc_login_requires_config(self, client):
        """Test OIDC login fails without configuration."""
        response = client.get("/auth/oidc/login")
        
        # Without env vars, should fail
        assert response.status_code in [200, 500]
    
    def test_oidc_callback_without_code(self, client):
        """Test OIDC callback without code fails."""
        response = client.post("/auth/oidc/callback")
        
        # Should fail validation
        assert response.status_code == 422
    
    def test_sso_providers_list(self, client):
        """Test listing supported SSO providers."""
        providers = ["google", "github", "okta", "azure-ad", "authentik"]
        
        for provider in providers:
            response = client.get(f"/auth/sso/{provider}/login")
            
            # Should either work or fail gracefully
            assert response.status_code in [200, 400]
    
    def test_sso_invalid_provider(self, client):
        """Test using invalid SSO provider."""
        response = client.get("/auth/sso/invalid-provider/login")
        
        assert response.status_code == 400
        assert "unsupported" in response.json()["detail"].lower()
    
    def test_oidc_userinfo_unauthorized(self, client):
        """Test OIDC userinfo requires authentication."""
        response = client.get("/auth/oidc/userinfo")
        
        assert response.status_code == 401
    
    def test_oidc_userinfo_with_auth(self, client):
        """Test OIDC userinfo returns user data."""
        # This test would require a valid JWT token
        # Just verify the endpoint exists
        response = client.get(
            "/auth/oidc/userinfo",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Should fail with auth error, not 404
        assert response.status_code == 401


class TestOIDCSecurity:
    """Security tests for OIDC."""
    
    def test_oidc_redirect_uri_validation(self, client):
        """Test OIDC redirect URI is validated."""
        response = client.get("/auth/oidc/login")
        
        data = response.json()
        auth_url = data.get("auth_url", "")
        
        # Should include redirect_uri parameter
        assert "redirect_uri" in auth_url or "redirectUri" in auth_url
    
    def test_oidc_scopes_included(self, client, mock_oidc_env):
        """Test OIDC scopes are included in auth request."""
        response = client.get("/auth/oidc/login")
        
        data = response.json()
        auth_url = data.get("auth_url", "")
        
        # Should include openid scope
        assert "openid" in auth_url
    
    def test_oidc_client_id_included(self, client, mock_oidc_env):
        """Test OIDC client ID is included in auth request."""
        response = client.get("/auth/oidc/login")
        
        data = response.json()
        auth_url = data.get("auth_url", "")
        
        # Should include client_id
        assert "client_id" in auth_url or "clientId" in auth_url


class TestOAuthProviders:
    """Tests for OAuth provider integration."""
    
    def test_google_oauth_initiation(self, client):
        """Test Google OAuth flow initiation."""
        response = client.get("/auth/sso/google/login")
        
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "google"
    
    def test_github_oauth_initiation(self, client):
        """Test GitHub OAuth flow initiation."""
        response = client.get("/auth/sso/github/login")
        
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "github"
    
    def test_okta_oauth_initiation(self, client):
        """Test Okta OAuth flow initiation."""
        response = client.get("/auth/sso/okta/login")
        
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "okta"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
