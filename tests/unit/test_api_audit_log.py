"""
Unit tests for KubeTix API - Audit Log endpoint
Tests the /audit endpoint and audit log entries created by grant operations
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import secrets
import os
import tempfile

# Import the main app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "kubetix-api"))

from main import app, Base, get_db, User, Grant, AuditLog, get_password_hash


# Test database (in-memory SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """Create test client with fresh database."""
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create database session for tests."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def auth_token(client, db_session):
    """Create user and return auth token."""
    user = User(
        id=secrets.token_urlsafe(16),
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123")
    )
    db_session.add(user)
    db_session.commit()
    
    response = client.post(
        "/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def auth_headers(auth_token):
    """Return authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="function")
def admin_user(db_session):
    """Create an admin user."""
    user = User(
        id=secrets.token_urlsafe(16),
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        is_admin=True,
        full_name="Admin User"
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture(scope="function")
def admin_token(client, db_session, admin_user):
    """Create token for the admin user."""
    response = client.post(
        "/login",
        json={
            "email": "admin@example.com",
            "password": "adminpassword123"
        }
    )
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def admin_headers(admin_token):
    """Return authorization headers for the admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


class TestAuditLogEndpoint:
    """Tests for the /audit log endpoint."""
    
    def test_audit_log_unauthorized(self, client):
        """Test accessing audit log without authentication returns 401."""
        response = client.get("/audit")
        assert response.status_code == 401
    
    def test_audit_log_empty_for_user(self, client, auth_headers):
        """Test audit log is empty when no actions have been performed."""
        response = client.get("/audit", headers=auth_headers)
        assert response.status_code == 200
        logs = response.json()
        assert logs == []
    
    def test_audit_log_contains_grant_creation(self, client, db_session, auth_headers, monkeypatch):
        """Test that creating a grant generates an audit log entry."""
        # Create kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kubeconfig', delete=False) as f:
            f.write("apiVersion: v1\nkind: Config\n")
            kubeconfig_path = f.name
        
        monkeypatch.setenv("KUBECONFIG", kubeconfig_path)
        
        # Create a grant (which should log an audit entry)
        response = client.post(
            "/grants",
            json={
                "cluster_name": "audit-test-cluster",
                "role": "view"
            },
            headers=auth_headers
        )
        
        os.unlink(kubeconfig_path)
        
        assert response.status_code == 201
        
        # Check audit log contains the creation entry
        audit_response = client.get("/audit", headers=auth_headers)
        assert audit_response.status_code == 200
        logs = audit_response.json()
        assert len(logs) >= 1
        
        # Find the grant creation entry
        creation_entries = [log for log in logs if log["action"] == "created"]
        assert len(creation_entries) >= 1
        assert "audit-test-cluster" in creation_entries[0]["details"]
    
    def test_audit_log_contains_grant_revocation(self, client, db_session, auth_headers, monkeypatch):
        """Test that revoking a grant generates an audit log entry."""
        # Create kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kubeconfig', delete=False) as f:
            f.write("apiVersion: v1\nkind: Config\n")
            kubeconfig_path = f.name
        
        monkeypatch.setenv("KUBECONFIG", kubeconfig_path)
        
        # Create a grant first
        client.post(
            "/grants",
            json={
                "cluster_name": "revoke-test-cluster",
                "role": "view"
            },
            headers=auth_headers
        )
        
        # Get the grant ID from grants list
        grants_response = client.get("/grants", headers=auth_headers)
        grants = grants_response.json()
        assert len(grants) >= 1
        grant_id = grants[0]["id"]
        
        # Revoke the grant
        revoke_response = client.delete(f"/grants/{grant_id}", headers=auth_headers)
        assert revoke_response.status_code == 204
        
        os.unlink(kubeconfig_path)
        
        # Check audit log contains the revocation entry
        audit_response = client.get("/audit", headers=auth_headers)
        assert audit_response.status_code == 200
        logs = audit_response.json()
        
        # Find the revocation entries (may have creation + revocation)
        revoke_entries = [log for log in logs if log["action"] == "revoked"]
        assert len(revoke_entries) >= 1
    
    def test_audit_log_fields(self, client, db_session, auth_headers, monkeypatch):
        """Test that audit log entries contain all expected fields."""
        # Create kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kubeconfig', delete=False) as f:
            f.write("apiVersion: v1\nkind: Config\n")
            kubeconfig_path = f.name
        
        monkeypatch.setenv("KUBECONFIG", kubeconfig_path)
        
        # Create a grant
        client.post(
            "/grants",
            json={
                "cluster_name": "fields-test-cluster",
                "role": "view"
            },
            headers=auth_headers
        )
        
        os.unlink(kubeconfig_path)
        
        # Check audit log entry structure
        audit_response = client.get("/audit", headers=auth_headers)
        assert audit_response.status_code == 200
        logs = audit_response.json()
        assert len(logs) >= 1
        
        entry = logs[0]
        expected_fields = {"id", "user_id", "grant_id", "action", "details", "created_at"}
        for field in expected_fields:
            assert field in entry, f"Missing field in audit log: {field}"
    
    def test_audit_log_ordering_descending(self, client, db_session, auth_headers, monkeypatch):
        """Test that audit log entries are returned in descending order (newest first)."""
        # Create kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kubeconfig', delete=False) as f:
            f.write("apiVersion: v1\nkind: Config\n")
            kubeconfig_path = f.name
        
        monkeypatch.setenv("KUBECONFIG", kubeconfig_path)
        
        # Create multiple grants to generate multiple audit entries
        for i in range(3):
            client.post(
                "/grants",
                json={
                    "cluster_name": f"ordering-cluster-{i}",
                    "role": "view"
                },
                headers=auth_headers
            )
        
        os.unlink(kubeconfig_path)
        
        # Check audit log ordering
        audit_response = client.get("/audit", headers=auth_headers)
        assert audit_response.status_code == 200
        logs = audit_response.json()
        assert len(logs) >= 3
        
        # Verify ordering is descending (newest first)
        for i in range(len(logs) - 1):
            assert logs[i]["created_at"] >= logs[i + 1]["created_at"]
    
    def test_audit_log_limit(self, client, db_session, auth_headers, monkeypatch):
        """Test that audit log respects a limit of 100 entries."""
        # Create kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kubeconfig', delete=False) as f:
            f.write("apiVersion: v1\nkind: Config\n")
            kubeconfig_path = f.name
        
        monkeypatch.setenv("KUBECONFIG", kubeconfig_path)
        
        # Create many grants to exceed the limit
        for i in range(150):
            client.post(
                "/grants",
                json={
                    "cluster_name": f"limit-cluster-{i}",
                    "role": "view"
                },
                headers=auth_headers
            )
        
        os.unlink(kubeconfig_path)
        
        # Check audit log respects limit of 100
        audit_response = client.get("/audit", headers=auth_headers)
        assert audit_response.status_code == 200
        logs = audit_response.json()
        assert len(logs) <= 100
    
    def test_audit_log_user_only_sees_own_entries(self, client, db_session, other_headers, admin_token, monkeypatch):
        """Test that non-admin users only see their own audit log entries."""
        # Create kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kubeconfig', delete=False) as f:
            f.write("apiVersion: v1\nkind: Config\n")
            kubeconfig_path = f.name
        
        monkeypatch.setenv("KUBECONFIG", kubeconfig_path)
        
        # Admin creates a grant
        admin_response = client.post(
            "/grants",
            json={
                "cluster_name": "admin-cluster",
                "role": "view"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_response.status_code == 201
        
        # Regular user creates a grant
        user_response = client.post(
            "/grants",
            json={
                "cluster_name": "user-cluster",
                "role": "view"
            },
            headers=other_headers
        )
        assert user_response.status_code == 201
        
        os.unlink(kubeconfig_path)
        
        # Regular user should only see their own entries
        audit_response = client.get("/audit", headers=other_headers)
        assert audit_response.status_code == 200
        logs = audit_response.json()
        
        # Filter for the user's cluster entries
        user_entries = [log for log in logs if "user-cluster" in log.get("details", "")]
        admin_entries = [log for log in logs if "admin-cluster" in log.get("details", "")]
        
        assert len(user_entries) >= 1
        assert len(admin_entries) == 0
    
    def test_audit_log_admin_sees_all_entries(self, client, db_session, admin_headers, other_token, monkeypatch):
        """Test that admin users can see all audit log entries."""
        # Create kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kubeconfig', delete=False) as f:
            f.write("apiVersion: v1\nkind: Config\n")
            kubeconfig_path = f.name
        
        monkeypatch.setenv("KUBECONFIG", kubeconfig_path)
        
        # Admin creates a grant
        admin_response = client.post(
            "/grants",
            json={
                "cluster_name": "admin-audit-cluster",
                "role": "view"
            },
            headers=admin_headers
        )
        assert admin_response.status_code == 201
        
        # Regular user creates a grant
        client.post(
            "/grants",
            json={
                "cluster_name": "user-audit-cluster",
                "role": "view"
            },
            headers={"Authorization": f"Bearer {other_token}"}
        )
        
        os.unlink(kubeconfig_path)
        
        # Admin should see both entries
        audit_response = client.get("/audit", headers=admin_headers)
        assert audit_response.status_code == 200
        logs = audit_response.json()
        
        admin_cluster_entries = [log for log in logs if "admin-audit-cluster" in log.get("details", "")]
        user_cluster_entries = [log for log in logs if "user-audit-cluster" in log.get("details", "")]
        
        assert len(admin_cluster_entries) >= 1
        assert len(user_cluster_entries) >= 1


class TestAuditLogIntegration:
    """Integration tests for audit log with grant operations."""
    
    def test_full_lifecycle_audit_trail(self, client, db_session, auth_headers, monkeypatch):
        """Test that a full grant lifecycle (create -> revoke) produces complete audit trail."""
        # Create kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kubeconfig', delete=False) as f:
            f.write("apiVersion: v1\nkind: Config\n")
            kubeconfig_path = f.name
        
        monkeypatch.setenv("KUBECONFIG", kubeconfig_path)
        
        # Create grant
        create_response = client.post(
            "/grants",
            json={
                "cluster_name": "lifecycle-cluster",
                "role": "edit"
            },
            headers=auth_headers
        )
        assert create_response.status_code == 201
        grant_id = create_response.json()["id"]
        
        os.unlink(kubeconfig_path)
        
        # Revoke grant
        revoke_response = client.delete(f"/grants/{grant_id}", headers=auth_headers)
        assert revoke_response.status_code == 204
        
        # Check complete audit trail
        audit_response = client.get("/audit", headers=auth_headers)
        assert audit_response.status_code == 200
        logs = audit_response.json()
        
        actions = [log["action"] for log in logs]
        assert "created" in actions
        assert "revoked" in actions
        
        # Verify grant_id is linked in both entries
        created_entry = next(log for log in logs if log["action"] == "created")
        revoked_entry = next(log for log in logs if log["action"] == "revoked")
        
        assert created_entry["grant_id"] == grant_id
        assert revoked_entry["grant_id"] == grant_id
    
    def test_audit_log_grant_id_present(self, client, db_session, auth_headers, monkeypatch):
        """Test that audit log entries for grant operations include the grant_id."""
        # Create kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kubeconfig', delete=False) as f:
            f.write("apiVersion: v1\nkind: Config\n")
            kubeconfig_path = f.name
        
        monkeypatch.setenv("KUBECONFIG", kubeconfig_path)
        
        # Create grant
        create_response = client.post(
            "/grants",
            json={
                "cluster_name": "grant-id-test-cluster",
                "role": "view"
            },
            headers=auth_headers
        )
        assert create_response.status_code == 201
        grant_id = create_response.json()["id"]
        
        os.unlink(kubeconfig_path)
        
        # Check audit log has the grant_id
        audit_response = client.get("/audit", headers=auth_headers)
        assert audit_response.status_code == 200
        logs = audit_response.json()
        
        created_entry = next((log for log in logs if log["action"] == "created"), None)
        assert created_entry is not None
        assert created_entry["grant_id"] == grant_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
