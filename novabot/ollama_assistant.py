# ollama_assistant.py

import requests
import json
from config import OLLAMA_ENDPOINT, SYSTEM_PROMPT
from web3_utils import get_account

last_ollama_response = None

def get_ollama_response(prompt):
    global last_ollama_response
    data = {
        "model": "llama3.2",
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False
    }
    response = requests.post(OLLAMA_ENDPOINT, json=data)
    print("Sending chat to llama...")
    if response.status_code == 200:
        last_ollama_response = response.json()['response']
        return last_ollama_response
    else:
        raise Exception(f"Error from Ollama API: {response.text}")

def parse_ollama_output(output):
    try:
        actions = json.loads(output)
        if not isinstance(actions, list):
            actions = [actions]
        
        # Replace 'self' with the actual account address
        for action in actions:
            if 'params' in action:
                for key, value in action['params'].items():
                    if value == 'self':
                        action['params'][key] = get_account().address
        
        return actions
    except json.JSONDecodeError:
        print("Error: Invalid JSON in Ollama output")
        return []
    except KeyError as e:
        print(f"Error: Missing key in Ollama output - {e}")
        return []

def get_last_ollama_response():
    global last_ollama_response
    return last_ollama_response

print("Ollama assistant initialized successfully.")