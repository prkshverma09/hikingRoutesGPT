import os
import threading
import time
from elevenlabs import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, ClientTools, AudioInterface
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

API_KEY = os.getenv("ELEVENLABS_API_KEY") or os.getenv("API_KEY")
AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID") or os.getenv("AGENT_ID")

def log_message(parameters):
    message = parameters.get("message")
    print(message)

client_tools = ClientTools()
client_tools.register("logMessage", log_message)

class MinimalAudioInterface(AudioInterface):
    def __init__(self):
        self._running = False
        self._thread = None

    def start(self, input_callback):
        self._running = True

        def loop():
            while self._running:
                time.sleep(0.25)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def output(self, audio: bytes):
        # No-op: discard audio or integrate with playback if desired
        pass

    def interrupt(self):
        self._running = False

conversation = Conversation(
    client=ElevenLabs(api_key=API_KEY),
    agent_id=AGENT_ID,
    client_tools=client_tools,
    requires_auth=True,
    audio_interface=MinimalAudioInterface(),
)

conversation.start_session()
