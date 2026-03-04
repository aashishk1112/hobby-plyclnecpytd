import os
import json
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load .env for local development
load_dotenv()

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
        secret_name = os.getenv("AWS_SECRET_NAME", "ScalarPlanckConfig")
        region_name = os.getenv("AWS_REGION", "ap-south-1")

        # Start with environment variables as default
        self._config = {k: v for k, v in os.environ.items()}

        # Attempt to load from Secrets Manager if not in local mode
        if os.getenv("IS_LOCAL", "false").lower() == "false":
            try:
                # Basic check for AWS credentials or profile to avoid hanging if possible
                session = boto3.session.Session()
                client = session.client(
                    service_name='secretsmanager',
                    region_name=region_name
                )
                get_secret_value_response = client.get_secret_value(
                    SecretId=secret_name
                )
                if 'SecretString' in get_secret_value_response:
                    secrets = json.loads(get_secret_value_response['SecretString'])
                    self._config.update(secrets)
                    print(f"Successfully loaded {len(secrets)} secrets from Secrets Manager: {secret_name}")
                elif 'SecretBinary' in get_secret_value_response:
                    # In case the secret is binary
                    import base64
                    decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
                    secrets = json.loads(decoded_binary_secret)
                    self._config.update(secrets)
                    print(f"Successfully loaded {len(secrets)} binary secrets from Secrets Manager: {secret_name}")
            except (ClientError, Exception) as e:
                # If we cannot fetch from Secrets Manager, we still have env vars
                print(f"Notice: Could not fetch secrets from Secrets Manager ({type(e).__name__}). Using environment/mock fallbacks.")

    def get(self, key, default=None):
        # 1. Check loaded config (Secrets Manager + Env)
        val = self._config.get(key)
        if val is not None:
            return val
        
        # 2. Check provided default in the call
        if default is not None:
            return default
            
        # 3. Check hardcoded mock defaults
        return MOCK_DEFAULTS.get(key)

# Singleton instance
config = ConfigLoader()

def get_config(key, default=None):
    return config.get(key, default)
