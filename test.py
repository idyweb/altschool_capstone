import pytest
from fastapi.testclient import TestClient
from main import app  # replace with the name of your FastAPI app
from scissors.models import Urls  # replace with your actual import path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_shorten_url():
    # Test data
    original_url = "https://example.com"
    access_token = "test_token"  
    custom_path = "test"

    # Send POST request
    response = client.post(
        "/url/shorten",
        data={"original_url": original_url, "custom_path": custom_path},
        cookies={"access_token": access_token}
    )

    # Check response
    assert response.status_code == 201
    assert "full_shortened_url" in response.json()

def test_update_url():
    # Test data
    shortened_url = "test_url" 
    url_data = {"original_url": "https://newexample.com"}

    # Send PUT request
    response = client.put(
        f"/url/{shortened_url}",
        json=url_data
    )

    # Check response
    assert response.status_code == 200
    assert response.json()["original_url"] == url_data["original_url"]