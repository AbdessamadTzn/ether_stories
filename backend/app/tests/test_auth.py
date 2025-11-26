from fastapi.testclient import TestClient

def test_signup_user(client: TestClient):
    response = client.post(
        "/auth/signup",
        json={
            "email": "test@ether.com", 
            "password": "securepassword123", 
            "full_name": "Test User"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@ether.com"
    assert "id" in data
    assert "password" not in data 

def test_signup_duplicate_email(client: TestClient):
    # 1. Create first user
    client.post(
        "/auth/signup",
        json={
            "email": "dupe@ether.com", 
            "password": "123",
            "full_name": "First One"
        }
    )
    
    # 2. Try to create same user again
    response = client.post(
        "/auth/signup",
        json={
            "email": "dupe@ether.com", 
            "password": "123",
            "full_name": "Second One"
        }
    )
    
    # Assert Failure (400 Bad Request, not 422)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_login_success(client: TestClient):
    # 1. Create user
    signup_res = client.post(
        "/auth/signup",
        json={
            "email": "login@ether.com", 
            "password": "mypassword",
            "full_name": "Login User"
        }
    )
    assert signup_res.status_code == 200

    # 2. Login (OAuth2 uses form data)
    response = client.post(
        "/auth/token",
        data={"username": "login@ether.com", "password": "mypassword"}
    )
    
    # Debug: if this fails, print the error
    if response.status_code != 200:
        print(response.json())

    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"