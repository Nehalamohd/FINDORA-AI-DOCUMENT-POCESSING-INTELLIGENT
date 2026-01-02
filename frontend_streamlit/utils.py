import requests
import streamlit as st
import os

# Use service name 'api' when running in Docker, or localhost if running locally
# We can default to 'api' if we assume Docker execution
API_URL = os.getenv("API_URL", "http://findora_api:8000") 

class APIClient:
    def __init__(self):
        self.token = st.session_state.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def login(self, username, password):
        data = {"username": username, "password": password}
        try:
            response = requests.post(f"{API_URL}/token", data=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e) if not response else response.text}

    def register(self, username, password, email=None):
        data = {"username": username, "password": password}
        if email:
            data["email"] = email
        try:
            response = requests.post(f"{API_URL}/users/register", data=data)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": response.text}
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def get_my_flows(self):
        try:
            response = requests.get(f"{API_URL}/flows/my-flows", headers=self.headers)
            if response.status_code == 200:
                return response.json().get("flows", [])
            return []
        except:
            return []

    def create_flow(self, name):
        try:
            response = requests.post(f"{API_URL}/flows/create", data={"name": name}, headers=self.headers)
            return response.json()
        except:
            return None

    def upload_document(self, file_bytes, filename, flow_name=None):
        import mimetypes
        mimetype, _ = mimetypes.guess_type(filename)
        if not mimetype:
            mimetype = "application/octet-stream"
            
        files = {"file": (filename, file_bytes, mimetype)}
        data = {}
        if flow_name:
            data["flow_name"] = flow_name
            
        try:
            response = requests.post(f"{API_URL}/upload", files=files, data=data, headers=self.headers)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def chat(self, message, flow_id, session_id=None):
        data = {"message": message, "flow_id": flow_id}
        if session_id:
            data["session_id"] = session_id
            
        try:
            response = requests.post(f"{API_URL}/chat", data=data, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": response.text}
        except Exception as e:
            return {"error": str(e)}

def require_auth():
    if "token" not in st.session_state:
        st.warning("Please verify you are logged in.")
        st.stop()
