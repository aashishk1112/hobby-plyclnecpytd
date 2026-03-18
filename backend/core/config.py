import os
import json
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load .env for local development
load_dotenv()
# Also load from the project root if it exists - consolidated source of truth
root_env = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(root_env):
    load_dotenv(root_env, override=True)

# Mock Defaults for Local Development without AWS credentials
MOCK_DEFAULTS = {
    "POLY_API_KEY": "mock-poly-key",
    "POLY_API_SECRET": "mock-poly-secret",
    "POLY_API_PASSPHRASE": "mock-poly-passphrase",
    "POLY_PRIVATE_KEY": "//0x0000000000000000000000000000000000000000000000000000000000000000",
    "PAPER_TRADING": "True",
    "LOG_LEVEL": "INFO",
    "MOCK_AUTH": "True",
    "GOOGLE_CLIENT_ID": "mock-google-id",
    "GOOGLE_CLIENT_SECRET": "mock-google-secret",
    "STRIPE_SECRET_KEY": "sk_test_mock",
    "STRIPE_WEBHOOK_SECRET": "whsec_mock",
    "FRONTEND_URL": "http://localhost:3000",
    "USER_POOL_ID": "us-east-1_mock_id",
    "DYNAMODB_TABLE": "ScalarUsersLocal",
    "TRADES_TABLE": "ScalarTradesLocal",
}

class ConfigLoader:
    _instance = None
    _config = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        # The variables are already loaded into os.environ by dotenv from backend/.env
        self._config = {k: v for k, v in os.environ.items()}

    def get(self, key, default=None):
        val = self._config.get(key)
        if val is not None:
            return val
        if default is not None:
            return default
        return MOCK_DEFAULTS.get(key)

config = ConfigLoader()

def get_config(key, default=None):
    return config.get(key, default)
