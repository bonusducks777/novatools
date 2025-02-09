# chat_manager.py
import json
import requests
from config import OLLAMA_ENDPOINT, get_system_prompt
from token_operations import TokenOperations

class ChatManager:
    def __init__(self):
        self.system_prompt = get_system_prompt()
        self.token_operations = TokenOperations()
        self.planned_actions = []

    def update_system_prompt(self, new_prompt):
        self.system_prompt = new_prompt

    def start_chat_session(self):
        return "Hello! I'm your crypto transaction assistant. How can I help you today?"

    def handle_user_request(self, user_message):
        response = self.generate_response(user_message)
        try:
            actions = json.loads(response)
            if isinstance(actions, list):
                self.planned_actions = [action for action in actions if isinstance(action, dict) and 'function' in action]
            elif isinstance(actions, dict) and 'function' in actions:
                self.planned_actions = [actions]
            else:
                self.planned_actions = []
        
            return self.format_planned_actions(), self.planned_actions
        except json.JSONDecodeError:
            self.planned_actions = []
            return "I'm sorry, I couldn't understand that request. Could you please rephrase it?", []

    def generate_response(self, user_message):
        payload = {
            "model": "llama3.2",
            "prompt": f"{self.system_prompt}\nUser: {user_message}\nAssistant:",
            "stream": False
        }
        try:
            response = requests.post(OLLAMA_ENDPOINT, json=payload)
            response.raise_for_status()  # This will raise an exception for HTTP errors
            return response.json()['response']
        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama API: {e}")
            return "Sorry, I'm having trouble processing your request right now."

    def format_planned_actions(self):
        if not self.planned_actions:
            return "I don't have any actions planned. What would you like me to do?"
        
        action_descriptions = []
        for action in self.planned_actions:
            if action['function'] == 'swap_tokens':
                desc = f"Swap {action['params']['amount_in']} {action['params']['token_in_ticker']} for {action['params']['token_out_ticker']}"
            elif action['function'] == 'get_token_balance':
                desc = f"Check balance of {action['params']['token_ticker']}"
            elif action['params']['function'] == 'send_native_token':
                desc = f"Send {action['params']['amount']} native tokens to {action['params']['to_address']}"
            elif action['function'] == 'send_erc20_token':
                desc = f"Send {action['params']['amount']} {action['params']['token_ticker']} to {action['params']['to_address']}"
            else:
                desc = f"Unknown action: {action['function']}"
            action_descriptions.append(desc)
        
        return "I plan to:<br>" + "<br>".join(f"{i+1}. {desc}" for i, desc in enumerate(action_descriptions))

    def execute_actions(self):
        results = []
        for action in self.planned_actions:
            if action['function'] == 'swap_tokens':
                result = self.token_operations.swap_tokens(**action['params'])
            elif action['function'] == 'get_token_balance':
                result = self.token_operations.get_token_balance(**action['params'])
            elif action['function'] == 'send_native_token':
                result = self.token_operations.send_native_token(**action['params'])
            elif action['function'] == 'send_erc20_token':
                result = self.token_operations.send_erc20_token(**action['params'])
            else:
                result = {'status': 'error', 'message': f"Unknown action: {action['function']}"}
            results.append(result)
        
        self.planned_actions = []
        return results
