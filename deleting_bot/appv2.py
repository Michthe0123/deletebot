import logging
import requests
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Set to DEBUG to capture all details
)
logger = logging.getLogger(__name__)

# Telegram bot token and URL
TOKEN = config.BOT_TOKEN
URL = f'https://api.telegram.org/bot{TOKEN}/'
ALLOWED_GROUP_IDS = config.ALLOWED_GROUP_IDS
DELETE_DELAY = config.DELETE_DELAY

# Scheduler for message deletion
scheduler = BackgroundScheduler()
scheduler.start()

# Function to send requests to the Telegram API
def send_request(method, data):
    url = URL + method
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        logger.debug(f'Request to {url} with data {data} succeeded: {response.json()}')
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f'Request to {url} with data {data} failed: {e}')
        return {}

# Function to check if a user is an admin
def is_user_admin(chat_id, user_id):
    response = send_request('getChatMember', {'chat_id': chat_id, 'user_id': user_id})
    if response.get('ok'):
        status = response['result']['status']
        return status in ['administrator', 'creator']
    else:
        logger.error(f'Failed to get chat member status for user {user_id} in chat {chat_id}')
        return False

# Function to delete a message
def delete_message(chat_id, message_id):
    logger.info(f'Deleting message {message_id} in chat {chat_id}')
    response = send_request('deleteMessage', {'chat_id': chat_id, 'message_id': message_id})
    if response.get('ok'):
        logger.info(f'Successfully deleted message {message_id} in chat {chat_id}')
    else:
        logger.error(f'Failed to delete message {message_id} in chat {chat_id}. Response: {response}')

# Function to handle incoming messages
def handle_message(message):
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    message_id = message['message_id']
    logger.info(f'Received message {message_id} in chat {chat_id} from user {user_id}')

    if chat_id in ALLOWED_GROUP_IDS:
        logger.info(f'Message {message_id} in chat {chat_id} is in an allowed group')
        if is_user_admin(chat_id, user_id):
            logger.info(f'Message {message_id} in chat {chat_id} is from an admin, not scheduling for deletion')
        else:
            # Schedule message deletion after specified delay
            delete_time = datetime.now() + timedelta(seconds=DELETE_DELAY)
            scheduler.add_job(delete_message, 'date', run_date=delete_time, args=[chat_id, message_id])
    else:
        logger.info(f'Message {message_id} in chat {chat_id} is not in an allowed group')

# Function to get updates
def get_updates(offset=None):
    data = {'timeout': 10, 'offset': offset}  # Reduce timeout to 10 seconds
    response = send_request('getUpdates', data)
    return response

# Main function to run the bot
def main():
    offset = None
    logger.info('Bot started. Polling for updates...')

    while True:
        updates = get_updates(offset)
        if updates.get('result'):
            logger.debug(f'Received updates: {updates["result"]}')
            for update in updates['result']:
                offset = update['update_id'] + 1
                if 'message' in update:
                    handle_message(update['message'])
        else:
            logger.debug('No updates received')

        time.sleep(1)

if __name__ == '__main__':
    main()
