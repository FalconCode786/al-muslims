import pytest
from app import create_app
from config import Config

class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret-key'
    SUPABASE_URL = 'test-url'
    SUPABASE_KEY = 'test-key'
    SUPABASE_SERVICE_ROLE_KEY = 'test-service-key'

@pytest.fixture
def app():
    app = create_app()
    app.config.from_object(TestConfig)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_landing_page(client):
    """Test that landing page loads successfully"""
    response = client.get('/')
    assert response.status_code == 200

def test_login_page(client):
    """Test that login page loads successfully"""
    response = client.get('/auth/login')
    assert response.status_code == 200

def test_register_page(client):
    """Test that register page loads successfully"""
    response = client.get('/auth/register')
    assert response.status_code == 200

def test_dashboard_requires_login(client):
    """Test that dashboard redirects to login when not authenticated"""
    response = client.get('/dashboard/')
    assert response.status_code == 302
    assert '/auth/login' in response.location

def test_login_validation(client):
    """Test login form validation"""
    # Test empty form
    response = client.post('/auth/login', data={})
    assert response.status_code == 200
    
    # Test invalid email
    response = client.post('/auth/login', data={
        'email': 'invalid-email',
        'password': 'password123'
    })
    assert response.status_code == 200

def test_register_validation(client):
    """Test registration form validation"""
    # Test empty form
    response = client.post('/auth/register', data={})
    assert response.status_code == 200
    
    # Test password mismatch
    response = client.post('/auth/register', data={
        'full_name': 'Test User',
        'email': 'test@example.com',
        'password': 'TestPass123',
        'confirm_password': 'DifferentPass123'
    })
    assert response.status_code == 200

def test_logout_redirects(client):
    """Test that logout redirects to landing page"""
    response = client.get('/auth/logout')
    assert response.status_code == 302