# web_ui.py

from flask import Flask, render_template, request, jsonify, url_for
from flask_socketio import SocketIO
from chat_manager import ChatManager
from web3_utils import set_account, get_account, switch_chain
from config import chain_config
import datetime
from jose import jwt

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this to a secure random string
socketio = SocketIO(app, cors_allowed_origins="*")
chat_manager = ChatManager()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    socketio.emit('message', {'status': 'info', 'message': 'Client connected'})

@socketio.on('disconnect')
def handle_disconnect():
    socketio.emit('message', {'status': 'info', 'message': 'Client disconnected'})

@socketio.on('set_private_key')
def handle_set_private_key(private_key):
    try:
        set_account(private_key)
        account = get_account()
        token = jwt.encode({'private_key': private_key, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)}, app.config['SECRET_KEY'], algorithm='HS256')
        
        response_data = {
            'status': 'success',
            'message': f"Account set successfully: {account.address}",
            'token': token,
            'address': account.address
        }
        
        socketio.emit('private_key_set', response_data)
        
        socketio.emit('set_cookie', {'name': 'auth_token', 'value': token, 'options': {
            'httpOnly': True,
            'secure': True,
            'sameSite': 'Strict',
            'maxAge': 86400  # 1 day expiration
        }})
        
        socketio.emit('message', {'status': 'success', 'message': f"Account set successfully: {account.address}"})
        socketio.emit('chat_message', {'sender': 'bot', 'message': f'Account set: {account.address}'})
        
        intro_message = chat_manager.start_chat_session()
        socketio.emit('message', {'status': 'info', 'message': f"Sending intro message: {intro_message}"})
        socketio.emit('chat_message', {'sender': 'bot', 'message': intro_message})
        
    except Exception as e:
        error_message = f"Error setting account: {str(e)}"
        socketio.emit('message', {'status': 'error', 'message': error_message})
        socketio.emit('chat_message', {'sender': 'bot', 'message': f"An error occurred: {error_message}"})

@socketio.on('check_auth')
def handle_check_auth(token):
    if token:
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            private_key = data['private_key']
            set_account(private_key)
            account = get_account()
            socketio.emit('auth_status', {'status': 'success', 'address': account.address})
        except jwt.ExpiredSignatureError:
            socketio.emit('auth_status', {'status': 'expired'})
        except Exception as e:
            socketio.emit('auth_status', {'status': 'error', 'message': str(e)})
    else:
        socketio.emit('auth_status', {'status': 'not_authenticated'})

@socketio.on('chat_message')
def handle_chat_message(data):
    user_message = data['message']
    socketio.emit('message', {'status': 'info', 'message': f"Received message: {user_message}"})
    
    response, planned_actions = chat_manager.handle_user_request(user_message)
    
    if response:
        socketio.emit('message', {'status': 'info', 'message': f"Bot response: {response}"})
        socketio.emit('chat_message', {'sender': 'bot', 'message': response})
    
    if planned_actions:
        formatted_actions = []
        for idx, action in enumerate(planned_actions, 1):
            if action['function'] == 'get_token_balance':
                formatted_action = f"Check balance of {action['params']['token_ticker']}"
            elif action['function'] == 'swap_tokens':
                formatted_action = f"Swap {action['params']['amount_in']} {action['params']['token_in_ticker']} for {action['params']['token_out_ticker']}"
            elif action['function'] == 'send_native_token':
                formatted_action = f"Send {action['params']['amount']} {chain_config.NATIVE_TOKEN} to {action['params']['to_address']}"
            elif action['function'] == 'send_erc20_token':
                formatted_action = f"Send {action['params']['amount']} {action['params']['token_ticker']} to {action['params']['to_address']}"
            else:
                formatted_action = f"Unknown action: {action['function']}"
            
            formatted_actions.append(formatted_action)
            socketio.emit('message', {'status': 'info', 'message': f"Planned action: {formatted_action}"})
        
        socketio.emit('planned_actions', {'actions': formatted_actions})
    
    # Auto-execute if all actions are balance checks
    if all(action['function'] == 'get_token_balance' for action in planned_actions):
        socketio.emit('message', {'status': 'info', 'message': "Auto-executing balance checks"})
        results = chat_manager.execute_actions()
        balance_message = "Here are your requested balances:<br>"  # Use <br> for HTML line break
        for result in results:
            if isinstance(result, dict):
                # Update: Changed balance output format
                formatted_message = f"🔍 {result['message']}"  # Remove the line break and move the emoji
                socketio.emit('message', {'status': 'success', 'message': formatted_message})
                balance_message += formatted_message + "<br>"  # Add an extra line break for spacing
            else:
                formatted_message = f"🔍 {str(result)}"  # Handle non-dict results
                socketio.emit('message', {'status': 'success', 'message': formatted_message})
                balance_message += formatted_message + "<br>"
        socketio.emit('chat_message', {'sender': 'bot', 'message': balance_message.strip()})
        socketio.emit('chat_message', {'sender': 'bot', 'message': "Anything else I can help you with?"})
    else:
        socketio.emit('chat_message', {'sender': 'bot', 'message': "Please review the planned actions and approve to execute."})
        
@socketio.on('execute_actions')
def handle_execute_actions():
    socketio.emit('message', {'status': 'info', 'message': "Executing planned actions"})
    results = chat_manager.execute_actions()
    execution_log = "Actions executed:<br>"
    chat_message = "Actions executed:<br>"
    
    for result in results:
        if isinstance(result, dict):
            socketio.emit('message', result)
            if result['status'] == 'success':
                if 'balance' in result['message'].lower():
                    execution_log += f"❓ {result['message']}<br>"
                    chat_message += f"❓ {result['message']}<br>"
                else:
                    execution_log += f"✅ {result['message']}<br>"
                    chat_message += f"✅ {result['message']}<br>"  # Added line break here
                    if 'explorer_link' in result:
                        execution_log += f"Transaction Hash: {result['transactionHash']}<br>"
                        execution_log += f"Explorer Link: {result['explorer_link']}<br>"
                        chat_message += f"<a href='{result['explorer_link']}' target='_blank'>View in Explorer</a>"
            else:
                execution_log += f"❌ {result['message']}<br>"
                chat_message += f"❌ {result['message']}<br>"
        else:
            execution_log += f"❓ {str(result)}<br>"
            chat_message += f"❓ {str(result)}<br>"
    
    execution_log += "<br>"
    chat_message += "<br>"
    
    socketio.emit('message', {'status': 'info', 'message': execution_log})
    socketio.emit('chat_message', {'sender': 'bot', 'message': chat_message})
    socketio.emit('chat_message', {'sender': 'bot', 'message': "Actions executed. Anything else I can help you with?"})

@socketio.on('switch_chain')
def handle_switch_chain(data):
    chain = data['chain']
    chain_config.switch_chain(chain)
    switch_chain(chain_config.RPC_URL)
    
    socketio.emit('message', {'status': 'info', 'message': f"Switched to {chain.upper()} network"})
    socketio.emit('chat_message', {'sender': 'bot', 'message': f"Switched to {chain.upper()} network. The following tokens are now available: {', '.join(chain_config.token_list)}"})

if __name__ == '__main__':
    socketio.run(app, debug=True)