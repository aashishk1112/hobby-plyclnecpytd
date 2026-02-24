import boto3
import os
import json
from botocore.exceptions import ClientError
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

def handle_floats(obj):
    """Recursively convert floats to Decimals for DynamoDB."""
    if isinstance(obj, list):
        return [handle_floats(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: handle_floats(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj

# Load local config if exists (for LocalStack IDs)
AWS_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", ".aws_config.json"))
AWS_CONFIG = {}
if os.path.exists(AWS_CONFIG_PATH):
    with open(AWS_CONFIG_PATH, "r") as f:
        AWS_CONFIG = json.load(f)

# Environment variables (provided by Lambda or local setup)
TABLE_NAME = os.getenv("DYNAMODB_TABLE", AWS_CONFIG.get("DYNAMODB_TABLE", "ScalarUsers"))
TRADES_TABLE_NAME = os.getenv("TRADES_TABLE", AWS_CONFIG.get("TRADES_TABLE", "ScalarTrades"))
IS_LOCAL = os.getenv("AWS_SAM_LOCAL") or os.getenv("LOCALSTACK_HOSTNAME") or True # Default to True for now

def get_dynamodb_resource():
    if IS_LOCAL:
        return boto3.resource("dynamodb", endpoint_url="http://localhost:4566", region_name="us-east-1")
    return boto3.resource("dynamodb")

db = get_dynamodb_resource()
table = db.Table(TABLE_NAME)
trades_table = db.Table(TRADES_TABLE_NAME)

def get_user_data(user_id: str):
    """Retrieve user configuration and tracked wallets."""
    try:
        response = table.get_item(Key={"userId": user_id})
        return response.get("Item", {
            "userId": user_id,
            "trackedWallets": [],
            "disabledWallets": [],
            "initialBalance": 100.0,
            "subscriptionStatus": "free", # free, pro, cancelled
            "subscriptionId": None,
            "extraSlots": 0  # Number of additional slots purchased
        })
    except ClientError as e:
        logger.error(f"Error fetching user data: {e.response['Error']['Message']}")
        return None

def update_user_data(user_id: str, data: dict):
    """Update or create user configuration."""
    try:
        data["userId"] = user_id
        table.put_item(Item=handle_floats(data))
        return True
    except ClientError as e:
        logger.error(f"Error updating user data: {e.response['Error']['Message']}")
        return False

def add_wallet(user_id: str, address: str):
    try:
        # Check for duplicate
        data = get_user_data(user_id)
        if address in data.get("trackedWallets", []):
            return "duplicate"
            
        table.update_item(
            Key={"userId": user_id},
            UpdateExpression="SET trackedWallets = list_append(if_not_exists(trackedWallets, :empty_list), :addr)",
            ExpressionAttributeValues={
                ":addr": [address],
                ":empty_list": []
            }
        )
        return True
    except ClientError as e:
        logger.error(f"Error adding wallet: {e.response['Error']['Message']}")
        return False

def remove_wallet(user_id: str, address: str):
    data = get_user_data(user_id)
    if not data: return False
    
    if address in data["trackedWallets"]:
        data["trackedWallets"].remove(address)
        if address in data.get("disabledWallets", []):
            data["disabledWallets"].remove(address)
        return update_user_data(user_id, data)
    return True

def save_trade(user_id: str, trade_data: dict):
    """Persist trade history item."""
    try:
        # Use composite key for SK to allow time-based sorting: timestamp#txHash
        # Convert timestamp to ISO string or float for SK
        timestamp = trade_data.get("timestamp_raw", trade_data.get("timestamp"))
        tx_hash = trade_data.get("id")
        
        item = {
            "userId": user_id,
            "sortKey": f"{timestamp}#{tx_hash}",
            **trade_data
        }
        trades_table.put_item(Item=handle_floats(item))
        return True
    except ClientError as e:
        logger.error(f"Error saving trade for {user_id}: {e.response['Error']['Message']}")
        return False

def get_user_trades(user_id: str, limit: int = 50):
    """Fetch recent trades for a user."""
    try:
        response = trades_table.query(
            KeyConditionExpression="userId = :uid",
            ExpressionAttributeValues={":uid": user_id},
            ScanIndexForward=False, # Decending order (newest first)
            Limit=limit
        )
        return response.get("Items", [])
    except ClientError as e:
        logger.error(f"Error fetching trades for {user_id}: {e.response['Error']['Message']}")
        return []

def get_users():
    """Fetch all users to run tracker for."""
    try:
        # In a very large system, we would use an index or pagination
        response = table.scan(ProjectionExpression="userId")
        return [item["userId"] for item in response.get("Items", [])]
    except ClientError as e:
        logger.error(f"Error scanning users: {e.response['Error']['Message']}")
        return []
