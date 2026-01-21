import requests
import logging

# Configure basic logging for the frontend
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
"""
Shared utilities for the Streamlit frontend, including API client and authentication helpers.
"""
import streamlit as st
import os

# Use service name 'api' when running in Docker, or localhost if running locally
# We can default to 'api' if we assume Docker execution
API_URL = os.getenv("API_URL", "http://findora_api:8000") 

class APIClient:
    #gets the user token from Streamlit session state
    #Adds it to Authorization header for authenticated requests
    def __init__(self):
        """Initializes the API client with the user token from session state."""
        self.token = st.session_state.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
#Sends username & password to POST /token endpoint
#Returns JSON response on success or error message on failure.
    def login(self, username, password):
        """Authenticates the user and returns the access token."""
        data = {"username": username, "password": password}
        try:
            response = requests.post(f"{API_URL}/token", data=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Login failed: {str(e)}")
            return {"error": str(e) if not response else response.text}

#Sends registration info to POST /users/register.

    def register(self, username, password, email=None):
        """Registers a new user account."""
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
            logger.error(f"Registration failed: {str(e)}")
            return {"error": str(e)}

#Fetches the user’s flows from backend.

#Returns a list of flows or empty list if error
    def get_my_flows(self):
        """Fetches the list of flows owned by the current user."""
        try:
            response = requests.get(f"{API_URL}/flows/my-flows", headers=self.headers)
            if response.status_code == 200:
                flows = response.json().get("flows", [])
                logger.debug(f"Retrieved {len(flows)} flows for current user.")
                return flows
            logger.error(f"Failed to fetch flows: {response.status_code} - {response.text}")
            return []
        except Exception as e:
            logger.error(f"Error fetching flows: {str(e)}")
            return []

#Creates a new flow with a given name
    def create_flow(self, name):
        """Creates a new document flow."""
        try:
            response = requests.post(f"{API_URL}/flows/create", data={"name": name}, headers=self.headers)
            if response.status_code == 200:
                res = response.json()
                logger.info(f"Successfully created flow: {name}")
                return res
            logger.error(f"Failed to create flow '{name}': {response.status_code} - {response.text}")
            return {"error": response.text}
        except Exception as e:
            logger.error(f"Error creating flow '{name}': {str(e)}")
            return {"error": str(e)}

#Uploads a document file to the backend for processing
#Every file has a type, called a MIME type
#The function guesses the file type automatically from the filename
    def upload_document(self, file_bytes, filename, flow_name=None):
        """Uploads a file to the backend and associates it with a flow."""
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
            if response.status_code == 200:
                res = response.json()
                logger.info(f"Uploaded document '{filename}' successfully. Task ID: {res.get('task_id')}")
                return res
            logger.error(f"Upload failed for '{filename}': {response.status_code} - {response.text}")
            return {"error": response.text}
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            return {"error": str(e)}

#Sends a chat message to the backend for a specific flow
    def chat(self, message, flow_id, session_id=None, model="llama-3.3-70b-versatile"):
        """Sends a synchronous chat message and receives the AI response."""
        data = {"message": message, "flow_id": flow_id, "model": model}
        if session_id:
            data["session_id"] = session_id
            
        try:
            response = requests.post(f"{API_URL}/chat", data=data, headers=self.headers)
            if response.status_code == 200:
                logger.debug(f"Succesful chat request for flow {flow_id}")
                return response.json()
            else:
                logger.error(f"Chat request failed for flow {flow_id}: {response.text}")
                return {"error": response.text}
        except Exception as e:
            logger.error(f"Error during chat request for flow {flow_id}: {str(e)}")
            return {"error": str(e)}

    def chat_stream(self, message, flow_id, session_id=None, model="llama-3.3-70b-versatile"):
        """Initiates a streaming chat connection for real-time AI responses."""
        data = {"message": message, "flow_id": flow_id, "model": model}
        if session_id:
            data["session_id"] = session_id
            
        try:
            logger.debug(f"Initiating chat stream for flow {flow_id}")
            return requests.post(f"{API_URL}/chat/stream", data=data, headers=self.headers, stream=True)
        except Exception as e:
            logger.error(f"Error initiating chat stream for flow {flow_id}: {str(e)}")
            return {"error": str(e)}

    def get_review(self, flow_id):
        """Requests an AI-generated review for all documents in a flow."""
        try:
            response = requests.get(f"{API_URL}/flows/{flow_id}/review", headers=self.headers)
            if response.status_code == 200:
                logger.info(f"Retrieved review for flow {flow_id}")
                return response.json()
            else:
                logger.error(f"Failed to get review for flow {flow_id}: {response.status_code} - {response.text}")
                return {"error": response.text}
        except Exception as e:
            logger.error(f"Error requesting review for flow {flow_id}: {str(e)}")
            return {"error": str(e)}

    def get_chat_history(self, session_id):
        """Retrieves previous messages for a specific chat session."""
        try:
            response = requests.get(f"{API_URL}/chat/history/{session_id}", headers=self.headers)
            if response.status_code == 200:
                history = response.json()
                logger.debug(f"Retrieved {len(history)} messages for session {session_id}")
                return history
            logger.error(f"Failed to fetch chat history for {session_id}: {response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error fetching chat history for {session_id}: {str(e)}")
            return []

#
def require_auth():
    """Enforces authentication by stopping page execution if no token is present."""
    if "token" not in st.session_state:
        st.warning("Please verify you are logged in.")
        st.stop()
