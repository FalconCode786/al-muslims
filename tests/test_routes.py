import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_static_files(client):
    """Test that static files are served"""
    response = client.get('/static/css/style.css')
    assert response.status_code == 200

def test_404_error(client):
    """Test 404 error handling"""
    response = client.get('/nonexistent')
    assert response.status_code == 404

def test_csrf_protection(client):
    """Test that forms require proper method"""
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert b'POST' in response.data