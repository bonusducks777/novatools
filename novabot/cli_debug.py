import asyncio
from config import PRIVATE_KEY, config
from web3_utils import set_account, w3, get_account
from token_operations import swap_tokens_async, get_token_balance_async, send_native_token_async, send_erc20_token_async

async def main():
    try:
        # Set up the account and nonce manager
        set_account(PRIVATE_KEY)

        # Get the account to verify it's set up correctly
        account = get_account()

        # Print account address
        print(f"Account address: {account.address}")

        # Print configuration details
        print(f"RPC URL: {config['rpc_url']}")
        print(f"Exchange address: {config['exchange_address']}")

        # Check BNB balance
        bnb_balance = await get_token_balance_async('BNB', account.address)
        print(f"Initial BNB balance: {bnb_balance}")

        # Check CAKE balance
        cake_balance = await get_token_balance_async('CAKE', account.address)
        print(f"Initial CAKE balance: {cake_balance}")

        # Attempt to swap 0.001 BNB for CAKE
        print("\nAttempting to swap 0.001 BNB for CAKE...")
        try:
            result = await swap_tokens_async('BNB', 'CAKE', 0.001)
            print(f"Swap result: {result}")
        except Exception as e:
            print(f"Error during swap: {str(e)}")

        # Check balances again
        bnb_balance = await get_token_balance_async('BNB', account.address)
        print(f"\nFinal BNB balance: {bnb_balance}")

        cake_balance = await get_token_balance_async('CAKE', account.address)
        print(f"Final CAKE balance: {cake_balance}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())