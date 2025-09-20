import os
import requests
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env if present
load_dotenv(find_dotenv())

API_KEY = os.getenv('ELEVENLABS_API_KEY') or os.getenv('API_KEY')
AGENT_ID = os.getenv('ELEVENLABS_AGENT_ID') or os.getenv('AGENT_ID')

if not API_KEY or not AGENT_ID:
    raise RuntimeError(
        "Missing environment variables. Please set ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID (or API_KEY and AGENT_ID) in your .env file."
    )

session_url = 'https://api.elevenlabs.io/v1/agents/{}/sessions'.format(AGENT_ID)
headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

# Start new session (conversation)
response = requests.post(session_url, headers=headers)
if response.status_code == 200:
    data = response.json()
    conversation_id = data.get('conversation_id')
    signed_url = data.get('signed_url')
    print('Conversation start response:', data)
    if conversation_id:
        print('Conversation started with ID:', conversation_id)
    if signed_url:
        print('Signed WebSocket URL:', signed_url)
else:
    print('Failed to start session:', response.text)
