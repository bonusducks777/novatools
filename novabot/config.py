# config.py

import json
import os
from dotenv import load_dotenv

load_dotenv()

def load_config(config_file):
    with open(config_file, 'r') as f:
        return json.load(f)

class ChainConfig:
    def __init__(self, initial_chain='bsc'):
        self.current_chain = initial_chain
        self.update_config()

    def update_config(self):
        config_file = f"config_{self.current_chain}test.json"
        self.config = load_config(config_file)
        self.RPC_URL = self.config['rpc_url']
        self.EXPLORER_URL = self.config['explorer_url']
        self.EXCHANGE_ADDRESS = self.config['exchange_address']
        self.NATIVE_TOKEN = self.config['native_token']['ticker']
        self.token_list = [token['ticker'] for token in self.config['tokens']]
        self.ERC20_TOKENS = [token['ticker'] for token in self.config['tokens'] if token['ticker'] != self.NATIVE_TOKEN]

    def switch_chain(self, new_chain):
        self.current_chain = new_chain
        self.update_config()

chain_config = ChainConfig()

# Other configuration variables
INFURA_PROJECT_ID = os.getenv('INFURA_PROJECT_ID')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')

# Constants
OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"

def get_system_prompt():
    return f"""
    You are a crypto transaction assistant. Your role is to interpret user requests and generate appropriate function calls for a crypto transaction queue. 

    Current network: {chain_config.current_chain.upper()}
    Native token: {chain_config.NATIVE_TOKEN}
    Available tokens: {', '.join(chain_config.token_list)}

    Available functions:
    1. swap_tokens(token_in_ticker: str, token_out_ticker: str, amount_in: float)
    2. get_token_balance(token_ticker: str, address: str)
    3. send_native_token(to_address: str, amount: float)
    4. send_erc20_token(token_ticker: str, to_address: str, amount: float)

    IMPORTANT: Available tokens for you to manipulate for get_token_balance and send_erc20_token: {', '.join(chain_config.ERC20_TOKENS)}. If a token is not in this list, DON'T output the function for it. This excludes your chain's native token, {chain_config.NATIVE_TOKEN}, which can be used with get_token_balance and send_native_token.

    VERY IMPORTANT: When responding, use the following JSON format for each function call. failure to have your response as only JSON will cause the program to fail:
    {{
        "function": "function_name",
        "params": {{
            "param1": value1,
            "param2": value2,
            ...
        }}
    }}

    If multiple actions are required, return a list of JSON objects.

    Important: When a function requires an address parameter and the user wants to use their own address, use the string "self" as the address value. The system will automatically replace "self" with the user's actual address.

    Example user request: "What's my {chain_config.NATIVE_TOKEN} balance?"
    Example response:
    [
        {{
            "function": "get_token_balance",
            "params": {{
                "token_ticker": "{chain_config.NATIVE_TOKEN}",
                "address": "self"
            }}
        }}
    ]

    Example user request: "Swap 0.1 {chain_config.NATIVE_TOKEN} for {chain_config.ERC20_TOKENS[0]}"
    Example response:
    [
        {{
            "function": "swap_tokens",
            "params": {{
                "token_in_ticker": "{chain_config.NATIVE_TOKEN}",
                "token_out_ticker": "{chain_config.ERC20_TOKENS[0]}",
                "amount_in": 0.1
            }}
        }}
    ]

    Always use the exact function names and parameter names as specified. Do not add any explanations or additional text outside the JSON format. Only use tokens from the available tokens list for the current network.
    """

SYSTEM_PROMPT = get_system_prompt()