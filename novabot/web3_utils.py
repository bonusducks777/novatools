# web3_utils.py
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from config import chain_config

# Initialize Web3 instance
w3 = Web3(Web3.HTTPProvider(chain_config.RPC_URL))

# Add PoA middleware at layer 0 as required for BSC
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

# Initialize account and nonce_manager as None
account = None
nonce_manager = None

class NonceManager:
    def __init__(self, w3, address):
        self.w3 = w3
        self.address = address
        self.nonce = None

    def get_next_nonce(self):
        if self.nonce is None:
            self.nonce = self.w3.eth.get_transaction_count(self.address)
        else:
            self.nonce += 1
        return self.nonce

    def reset_nonce(self):
        self.nonce = None

def get_explorer_link(tx_hash):
    return f"{chain_config.EXPLORER_URL}{tx_hash}"

def set_account(private_key):
    global account, nonce_manager
    account = w3.eth.account.from_key(private_key)
    nonce_manager = NonceManager(w3, account.address)
    print(f"Account set: {account.address}")
    print(f"Nonce manager initialized for address: {account.address}")

def get_account():
    global account
    if account is None:
        raise ValueError("Account not initialized. Please call set_account first.")
    return account

def get_nonce_manager():
    global nonce_manager
    if nonce_manager is None:
        raise ValueError("Nonce manager not initialized. Please call set_account first.")
    return nonce_manager

def get_token_address(ticker):
    if ticker.upper() == chain_config.NATIVE_TOKEN:
        return chain_config.config['native_token']['address']
    for token in chain_config.config['tokens']:
        if token['ticker'].upper() == ticker.upper():
            return token['address']
    raise ValueError(f"Token with ticker {ticker} not found in configuration.")

def send_transaction(tx):
    account = get_account()
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transaction hash: {tx_hash.hex()}")
    print(f"Explorer link: {get_explorer_link(tx_hash)}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction mined. Status: {'Success' if receipt['status'] == 1 else 'Failed'}")
    return receipt

def switch_chain(rpc_url):
    global w3, account
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    if account:
        set_account(account._private_key.hex())  # Changed from privateKey to _private_key
    print(f"Switched to new network: {rpc_url}")

print("Web3 utilities initialized successfully.")