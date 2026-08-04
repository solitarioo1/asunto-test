import os

from dotenv import load_dotenv

load_dotenv()

TURNSTILE_SITE_KEY = os.environ["TURNSTILE_SITE_KEY"]
TURNSTILE_SECRET_KEY = os.environ["TURNSTILE_SECRET_KEY"]
