import requests
import json

BASE_URL = "http://localhost:8080/api"

def test_auth():
    """Test the authentication system."""
    print("Testing authentication system...")
    
    # Test registration
    print("\n1. Testing registration...")
    reg_data = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=reg_data)
        print(f"Status code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            token = response.json().get('token')
            user_id = response.json().get('user', {}).get('id')
            print(f"Registration successful! User ID: {user_id}")
        else:
            print("Registration failed.")
    except Exception as e:
        print(f"Error during registration: {e}")
    
    # Test login
    print("\n2. Testing login...")
    login_data = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Status code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            token = response.json().get('token')
            print(f"Login successful! Token: {token}")
            
            # Test protected route
            print("\n3. Testing protected route (chat history)...")
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            response = requests.get(f"{BASE_URL}/chat/history?session_id=test-session", headers=headers)
            print(f"Status code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                print("Protected route access successful!")
            else:
                print("Protected route access failed.")
        else:
            print("Login failed.")
    except Exception as e:
        print(f"Error during login: {e}")

if __name__ == "__main__":
    test_auth() 