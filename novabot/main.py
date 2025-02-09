import asyncio
from ollama_assistant import get_ollama_response, parse_ollama_output
from token_operations import get_token_balance_async
from web3_utils import account

async def execute_with_delay(func, *args, **kwargs):
    result = await func(*args, **kwargs)
    await asyncio.sleep(3)
    return result

async def process_queue(queue):
    results = []
    for func in queue:
        result = await execute_with_delay(func)
        results.append(result)
    return results

# The main_async and main functions are no longer needed here, as they're handled by web_ui.py

print("Main script initialized. Run web_ui.py to start the Crypto Transaction Assistant with a web interface.")