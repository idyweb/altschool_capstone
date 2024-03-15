from fastapi.testclient import TestClient
from main import app  # replace with the actual location of your FastAPI app
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import models

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"  # replace with your test database URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_redirect_to_original_url():
    # Arrange
    shortened_url = "test_url"  # replace with a shortened URL that exists in your test database
    expected_status_code = 302

    # Act
    response = client.get(f"/url/{shortened_url}")

    # Assert
    assert response.status_code == expected_status_code
    assert response.headers["location"] == "original_url"  # replace with the expected original URL

@pytest.fixture(autouse=True)
def create_test_data():
    # This fixture is automatically used by all tests. It creates some test data before each test and deletes it after each test.
    db = TestingSessionLocal()
    test_url = models.Urls(original_url="original_url", shortened_url="test_url")  # replace with your actual Urls model and data
    db.add(test_url)
    db.commit()
    yield
    db.delete(test_url)
    db.commit()