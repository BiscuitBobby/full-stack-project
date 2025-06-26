import requests

BASE_URL = 'http://localhost:8000/api'  # Change this if your server is hosted elsewhere

REGISTER_URL = f'{BASE_URL}/register/'
LOGIN_URL = f'{BASE_URL}/login/'
PROFILE_URL = f'{BASE_URL}/profile/'
LOGOUT_URL = f'{BASE_URL}/logout/'

# Test user credentials
TEST_USER = {
    'username': 'testuser',
    'password': 'testpass123',
    'email': 'test@example.com'  # Add other fields if required by your UserSerializer
}

def register_user():
    print("📤 Registering user...")
    response = requests.post(REGISTER_URL, data=TEST_USER)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    return response

def login_user():
    print("🔐 Logging in...")
    login_data = {
        'username': TEST_USER['username'],
        'password': TEST_USER['password']
    }
    response = requests.post(LOGIN_URL, data=login_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    token = response.json().get('token')
    return token

def get_profile(token):
    print("👤 Fetching profile...")
    headers = {'Authorization': f'Token {token}'}
    response = requests.get(PROFILE_URL, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

def logout_user(token):
    print("🚪 Logging out...")
    headers = {'Authorization': f'Token {token}'}
    response = requests.post(LOGOUT_URL, headers=headers, json={})
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == '__main__':
    # Run all steps
    reg_response = register_user()

    # If already registered, login instead
    if reg_response.status_code != 201:
        print("User may already exist, proceeding to login...")

    token = login_user()
    if token:
        get_profile(token)
        logout_user(token)
    else:
        print("❌ Failed to retrieve token; cannot continue tests.")
