# token_operations.py

from web3 import Web3
from web3_utils import w3, get_account, get_nonce_manager, send_transaction, get_token_address, get_explorer_link
from config import chain_config
import time

class TokenOperations:
    @staticmethod
    def handle_transaction_hash(tx_hash):
        if isinstance(tx_hash, bytes):
            return tx_hash.hex()
        elif isinstance(tx_hash, str):
            return tx_hash
        else:
            return str(tx_hash)  # Fallback to string conversion for any other type

    @staticmethod
    def approve_token(token_address: str, spender_address: str, amount: int):
        abi = [{"constant":False,"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}]
        contract = w3.eth.contract(address=token_address, abi=abi)
        nonce_manager = get_nonce_manager()
        nonce = nonce_manager.get_next_nonce()
        account = get_account()
        tx = contract.functions.approve(spender_address, amount).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': w3.eth.gas_price * 2
        })
        receipt = send_transaction(tx)
        time.sleep(1)
        return receipt

    @staticmethod
    def get_token_balance(token_ticker: str, address: str = None):
        if address is None or address == 'self':
            address = get_account().address
        token_address = get_token_address(token_ticker)
        print(f"Getting {token_ticker} balance for {address}")
        try:
            if token_ticker.upper() == chain_config.NATIVE_TOKEN:
                balance_wei = w3.eth.get_balance(Web3.to_checksum_address(address))
                balance = w3.from_wei(balance_wei, 'ether')
            else:
                abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]
                contract = w3.eth.contract(address=token_address, abi=abi)
                balance = contract.functions.balanceOf(address).call()
                decimals = contract.functions.decimals().call()
                balance = balance / (10 ** decimals)
            return f"{token_ticker} balance: {balance}"
        except Exception as e:
           print(f"Error in get_token_balance: {str(e)}")
           print(f"Token ticker: {token_ticker}, Address: {address}")
           return f"Error getting {token_ticker} balance: {str(e)}"

    @staticmethod
    def swap_tokens(token_in_ticker: str, token_out_ticker: str, amount_in: float):
        print(f"\nInitiating swap: {amount_in} {token_in_ticker} for {token_out_ticker}")
        try:
            token_in_address = get_token_address(token_in_ticker)
            token_out_address = get_token_address(token_out_ticker)
            exchange_router_address = chain_config.EXCHANGE_ADDRESS
            native_token_ticker = chain_config.NATIVE_TOKEN
            native_token_address = get_token_address(native_token_ticker)
            
            abi = [
                {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"}
            ]
            
            router = w3.eth.contract(address=exchange_router_address, abi=abi)
            deadline = w3.eth.get_block('latest')['timestamp'] + 1200  # 20 minutes from now

            nonce_manager = get_nonce_manager()
            account = get_account()

            if token_in_ticker.upper() == native_token_ticker:
                amount_in_wei = w3.to_wei(amount_in, 'ether')
                nonce = nonce_manager.get_next_nonce()
                tx = router.functions.swapExactETHForTokens(
                    0,  # amountOutMin: We don't set a minimum amount out for simplicity, but in production, you should
                    [native_token_address, token_out_address],
                    account.address,
                    deadline
                ).build_transaction({
                    'from': account.address,
                    'value': amount_in_wei,
                    'nonce': nonce,
                    'gas': 300000,
                    'gasPrice': w3.eth.gas_price * 2
                })
            elif token_out_ticker.upper() == native_token_ticker:
                token_abi = [{"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]
                token_contract = w3.eth.contract(address=token_in_address, abi=token_abi)
                decimals = token_contract.functions.decimals().call()
                amount_in_wei = int(amount_in * (10 ** decimals))
                
                # Approve the router to spend tokens
                TokenOperations.approve_token(token_in_address, exchange_router_address, amount_in_wei)
                
                nonce = nonce_manager.get_next_nonce()
                tx = router.functions.swapExactTokensForETH(
                    amount_in_wei,
                    0,  # amountOutMin: We don't set a minimum amount out for simplicity, but in production, you should
                    [token_in_address, native_token_address],
                    account.address,
                    deadline
                ).build_transaction({
                    'from': account.address,
                    'nonce': nonce,
                    'gas': 300000,
                    'gasPrice': w3.eth.gas_price * 2
                })
            else:
                token_abi = [{"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]
                token_contract = w3.eth.contract(address=token_in_address, abi=token_abi)
                decimals = token_contract.functions.decimals().call()
                amount_in_wei = int(amount_in * (10 ** decimals))
                
                # Approve the router to spend tokens
                TokenOperations.approve_token(token_in_address, exchange_router_address, amount_in_wei)
                
                nonce = nonce_manager.get_next_nonce()
                tx = router.functions.swapExactTokensForTokens(
                    amount_in_wei,
                    0,  # amountOutMin: We don't set a minimum amount out for simplicity, but in production, you should
                    [token_in_address, token_out_address],
                    account.address,
                    deadline
                ).build_transaction({
                    'from': account.address,
                    'nonce': nonce,
                    'gas': 300000,
                    'gasPrice': w3.eth.gas_price * 2
                })

            receipt = send_transaction(tx)
            print(f"Swap completed: {amount_in} {token_in_ticker} for {token_out_ticker}")
            tx_hash = TokenOperations.handle_transaction_hash(receipt['transactionHash'])
            explorer_link = get_explorer_link(tx_hash)
            return {
                "status": "success",
                "message": f"Swapped {amount_in} {token_in_ticker} for {token_out_ticker}",
                "transactionHash": tx_hash,
                "explorer_link": explorer_link
            }
        except Exception as e:
            print(f"Error in swap_tokens: {e}")
            nonce_manager = get_nonce_manager()
            nonce_manager.reset_nonce()  # Reset nonce on error
            raise

    @staticmethod
    def send_native_token(to_address: str, amount: float):
        print(f"\nInitiating native token transfer: {amount} {chain_config.NATIVE_TOKEN} to {to_address}")
        try:
            amount_wei = w3.to_wei(amount, 'ether')
            nonce_manager = get_nonce_manager()
            nonce = nonce_manager.get_next_nonce()
            account = get_account()
            tx = {
                'to': to_address,
                'value': amount_wei,
                'gas': 21000,
                'gasPrice': w3.eth.gas_price * 2,
                'nonce': nonce,
            }
            receipt = send_transaction(tx)
            print(f"Native token transfer completed: {amount} {chain_config.NATIVE_TOKEN} to {to_address}")
            tx_hash = TokenOperations.handle_transaction_hash(receipt['transactionHash'])
            explorer_link = get_explorer_link(tx_hash)
            return {
                "status": "success",
                "message": f"Sent {amount} {chain_config.NATIVE_TOKEN} to {to_address}",
                "transactionHash": tx_hash,
                "explorer_link": explorer_link
            }
        except Exception as e:
            print(f"Error in send_native_token: {e}")
            nonce_manager = get_nonce_manager()
            nonce_manager.reset_nonce()  # Reset nonce on error
            raise

    @staticmethod
    def send_erc20_token(token_ticker: str, to_address: str, amount: float):
        token_address = get_token_address(token_ticker)
        print(f"\nInitiating ERC20 token transfer: {amount} {token_ticker} to {to_address}")
        try:
            abi = [
                {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
                {"constant":False,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"}
            ]
            contract = w3.eth.contract(address=token_address, abi=abi)
            decimals = contract.functions.decimals().call()
            amount_wei = int(amount * (10 ** decimals))
            nonce_manager = get_nonce_manager()
            nonce = nonce_manager.get_next_nonce()
            account = get_account()
            tx = contract.functions.transfer(to_address, amount_wei).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': w3.eth.gas_price * 2
            })
            receipt = send_transaction(tx)
            print(f"ERC20 token transfer completed: {amount} {token_ticker} to {to_address}")
            tx_hash = TokenOperations.handle_transaction_hash(receipt['transactionHash'])
            explorer_link = get_explorer_link(tx_hash)
            return {
                "status": "success",
                "message": f"Sent {amount} {token_ticker} to {to_address}",
                "transactionHash": tx_hash,
                "explorer_link": explorer_link
            }
        except Exception as e:
            print(f"Error in send_erc20_token: {e}")
            nonce_manager = get_nonce_manager()
            nonce_manager.reset_nonce()  # Reset nonce on error
            raise

print("Token operations initialized successfully.")