from dotenv import load_dotenv
load_dotenv()

import os
import sys
import logging

logger=None

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
setup_logging()

logger = logging.getLogger(__name__)

ENVS=['DB_URL', 'BOT_TOKEN', 'MODE','ENV',"WEBHOOK_PATH","WEBHOOK_SECRET","PORT"]

CACHE_TTL=300 #10 mins in seconds

def check_envs():
    missing_envs = [env for env in ENVS if os.getenv(env) is None]
    if missing_envs:
        logging.error(f'Missing environment variables: {", ".join(missing_envs)}')
        sys.exit(1)
check_envs()

DB_URL = os.getenv('DB_URL')
BOT_TOKEN = os.getenv('BOT_TOKEN')
MODE=os.getenv('MODE')
ENV=os.getenv('ENV')

WEBHOOK_PATH=os.getenv("WEBHOOK_PATH","/webhook")
WEBHOOK_SECRET=os.getenv("WEBHOOK_SECRET","perlica")
PORT=os.getenv("PORT",8000)

_render_url = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or (_render_url if _render_url else f"http://localhost:{PORT}")