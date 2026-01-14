#Handles communication with backend API
import requests
import streamlit as st
import os

# Use service name 'api' when running in Docker, or localhost if running locally
# We can default to 'api' if we assume Docker execution
API_URL = os.getenv("API_URL", "http://findora_api:8000") 

class APIClient:
    #gets the user token from Streamlit session state
    #Adds it to Authorization header for authenticated requests
    def __init__(self):
        self.token = st.session_state.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
#Sends username & password to POST /token endpoint
#Returns JSON response on success or error message on failure.
    def login(self, username, password):
        data = {"username": username, "password": password}
        try:
            response = requests.post(f"{API_URL}/token", data=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e) if not response else response.text}

#Sends registration info to POST /users/register.

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

#Fetches the user’s flows from backend.

#Returns a list of flows or empty list if error
    def get_my_flows(self):
        try:
            response = requests.get(f"{API_URL}/flows/my-flows", headers=self.headers)
            if response.status_code == 200:
                return response.json().get("flows", [])
            return []
        except:
            return []

#Creates a new flow with a given name
    def create_flow(self, name):
        try:
            response = requests.post(f"{API_URL}/flows/create", data={"name": name}, headers=self.headers)
            return response.json()
        except:
            return None

#Uploads a document file to the backend for processing
#Every file has a type, called a MIME type
#The function guesses the file type automatically from the filename
    def upload_document(self, file_bytes, filename, flow_name=None):
        import mimetypes
        mimetype, _ = mimetypes.guess_type(filename)
        if not mimetype:
            mimetype = "application/octet-stream"
            # which file to send, its name, and its type
        files = {"file": (filename, file_bytes, mimetype)}
        #data is a dictionary of extra info to send along with the file.
        # If a flow_name is provided, it adds "flow_name" to data.
        # This tells the backend which flow this document belongs to.
        data = {}
        if flow_name:
            data["flow_name"] = flow_name
            
        try:
            #Send the POST request to /upload endpoint
            response = requests.post(f"{API_URL}/upload", files=files, data=data, headers=self.headers)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

#Sends a chat message to the backend for a specific flow
    def chat(self, message, flow_id, session_id=None, model="llama-3.3-70b-versatile"):
        data = {"message": message, "flow_id": flow_id, "model": model}
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

    def chat_stream(self, message, flow_id, session_id=None, model="llama-3.3-70b-versatile"):
        data = {"message": message, "flow_id": flow_id, "model": model}
        if session_id:
            data["session_id"] = session_id
            
        try:
            return requests.post(f"{API_URL}/chat/stream", data=data, headers=self.headers, stream=True)
        except Exception as e:
            return {"error": str(e)}

    def get_review(self, flow_id):
        try:
            response = requests.get(f"{API_URL}/flows/{flow_id}/review", headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": response.text}
        except Exception as e:
            return {"error": str(e)}

    def get_chat_history(self, session_id):
        try:
            # We don't have a direct endpoint for history in main.py yet, or do we?
            # Looking at main.py, there's no @app.get("/chat/history/{session_id}")
            # I should add it.
            response = requests.get(f"{API_URL}/chat/history/{session_id}", headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []

#
def require_auth():
    if "token" not in st.session_state:
        st.warning("Please verify you are logged in.")
        st.stop()
