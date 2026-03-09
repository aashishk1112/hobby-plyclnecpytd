import boto3
import os
import json
from botocore.exceptions import ClientError
import logging
from decimal import Decimal
from backend.core.config import get_config

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
# Constants
AWS_REGION = get_config("AWS_REGION", "ap-south-1")
TABLE_NAME = get_config("DYNAMODB_TABLE", "ScalarUsers")
TRADES_TABLE_NAME = get_config("TRADES_TABLE", "ScalarTrades")
IS_LOCAL = get_config("IS_LOCAL", "false").lower() == "true"

from botocore.config import Config

def get_dynamodb_resource():
    config = Config(
        connect_timeout=1,
        read_timeout=1,
        retries={'max_attempts': 0}
    )
    if IS_LOCAL:
        return boto3.resource(
            "dynamodb", 
            endpoint_url="http://localhost:4566", 
            region_name="us-east-1",
            config=config
        )
    return boto3.resource("dynamodb", region_name=AWS_REGION)

db = get_dynamodb_resource()
table = db.Table(TABLE_NAME)
trades_table = db.Table(TRADES_TABLE_NAME)

# Mock In-Memory DB for completely local execution without LocalStack
DB_FILE = "local_db.json"
MOCK_DB = {}
MOCK_TRADES = {}

def _save_mock_db():
    try:
        with open(DB_FILE, "w") as f:
            json.dump({"db": MOCK_DB, "trades": MOCK_TRADES}, f, default=str)
    except Exception as e:
        logger.error(f"Failed to save mock DB: {e}")

def _load_mock_db():
    global MOCK_DB, MOCK_TRADES
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                MOCK_DB = data.get("db", {})
                MOCK_TRADES = data.get("trades", {})
                logger.info("Local mock DB loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load mock DB: {e}")

# Load on module import
if IS_LOCAL:
    _load_mock_db()

def reset_mock_db():
    """Clear memory and file cache for testing."""
    global MOCK_DB, MOCK_TRADES
    MOCK_DB = {}
    MOCK_TRADES = {}
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    logger.info("Mock DB has been reset.")

def get_user_data(user_id: str):
    """Retrieve user configuration and tracked wallets."""
    # Try in-memory first for mock mode
    if IS_LOCAL and user_id in MOCK_DB:
        return MOCK_DB[user_id]
        
    try:
        response = table.get_item(Key={"userId": user_id})
        item = response.get("Item")
        if item: return item
    except Exception as e:
        logger.warning(f"DynamoDB connection failed, falling back to mock: {e}")

    # Default skeleton for new user
    default_user = {
        "userId": user_id,
        "trackedWallets": [],
        "disabledWallets": [],
        "terminatedWallets": [],
        "initialBalance": 100.0,
        "balance": 100.0,
        "balanceThreshold": 0.0,
        "dailyPnlThreshold": 1000.0,
        "tradingMode": "paper",
        "subscriptionStatus": "free", # free, pro, elite
        "extraSlots": 0,
        "referralCode": f"ref-{user_id[:8]}",
        "referredBy": None,
        "referralCount": 0,
        "followers": [],
        "following": [],
        "isPublic": False,
        "bio": "",
        "smartCopyRules": {},
        "riskControls": {},
        "allocationWeights": {}
    }
    if IS_LOCAL: 
        MOCK_DB[user_id] = default_user
        _save_mock_db()
    return default_user

def update_user_data(user_id: str, data: dict):
    """Update or create user configuration."""
    if IS_LOCAL:
        MOCK_DB[user_id] = data
        _save_mock_db()
        
    try:
        data["userId"] = user_id
        table.put_item(Item=handle_floats(data))
        return True
    except Exception as e:
        if IS_LOCAL: return True # Already updated in mock
        logger.error(f"Error updating user data: {e}")
        return False

def update_user_balance(user_id: str, balance: float):
    """Update only the current balance for a user."""
    if IS_LOCAL:
        data = get_user_data(user_id)
        data["balance"] = balance
        MOCK_DB[user_id] = data
        _save_mock_db()
        return True
    try:
        table.update_item(
            Key={"userId": user_id},
            UpdateExpression="SET balance = :b",
            ExpressionAttributeValues={":b": handle_floats(balance)}
        )
        return True
    except ClientError as e:
        logger.error(f"Error updating balance for {user_id}: {e.response['Error']['Message']}")
        return False

def add_wallet(user_id: str, address: str):
    try:
        data = get_user_data(user_id)
        if not data: return False
        
        current_wallets = data.get("trackedWallets", [])
        terminated_wallets = data.get("terminatedWallets", [])
        
        # Check for reactivation
        if address in current_wallets and address in terminated_wallets:
            terminated_wallets.remove(address)
            data["terminatedWallets"] = terminated_wallets
            
            # Ensure it's removed from disabledWallets to resume tracking
            disabled = data.get("disabledWallets", [])
            if address in disabled:
                disabled.remove(address)
                data["disabledWallets"] = disabled
                
            update_user_data(user_id, data)
            return "reactivated"
            
        if IS_LOCAL:
            if address in current_wallets: return "duplicate"
            current_wallets.append(address)
            data["trackedWallets"] = current_wallets
            update_user_data(user_id, data)
            return True

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

def terminate_wallet(user_id: str, address: str):
    """Mark a wallet as terminated. It remains in trackedWallets but trading stops."""
    data = get_user_data(user_id)
    if not data: return False
    
    if address in data["trackedWallets"]:
        if "terminatedWallets" not in data:
            data["terminatedWallets"] = []
        
        if address not in data["terminatedWallets"]:
            data["terminatedWallets"].append(address)
            
        # Also ensure it's in disabledWallets for tracker
        if "disabledWallets" not in data:
            data["disabledWallets"] = []
        if address not in data["disabledWallets"]:
            data["disabledWallets"].append(address)
            
        return update_user_data(user_id, data)
    return True

def save_trade(user_id: str, trade_data: dict):
    """Persist trade history item."""
    if IS_LOCAL:
        if user_id not in MOCK_TRADES: MOCK_TRADES[user_id] = []
        MOCK_TRADES[user_id].insert(0, trade_data)
        _save_mock_db()

    try:
        timestamp = trade_data.get("timestamp_raw", trade_data.get("timestamp"))
        tx_hash = trade_data.get("id")
        item = {
            "userId": user_id,
            "sortKey": f"{timestamp}#{tx_hash}",
            **trade_data
        }
        trades_table.put_item(Item=handle_floats(item))
        return True
    except Exception as e:
        if IS_LOCAL: return True
        logger.error(f"Error saving trade for {user_id}: {e}")
        return False

def is_trade_processed(user_id: str, tx_hash: str):
    """Check if a trade ID already exists in ScalarTrades."""
    if IS_LOCAL:
        trades = MOCK_TRADES.get(user_id, [])
        return any(t.get("id") == tx_hash for t in trades)

    try:
        # We need to query by userId and check if any sortKey contains the tx_hash
        # Since sortKey is timestamp#txHash, we've stored tx_hash as 'id' in the item as well
        response = trades_table.query(
            KeyConditionExpression="userId = :uid",
            FilterExpression="#tx_id = :tx",
            ExpressionAttributeNames={
                "#tx_id": "id"
            },
            ExpressionAttributeValues={
                ":uid": user_id,
                ":tx": tx_hash
            },
            Limit=1
        )
        return len(response.get("Items", [])) > 0
    except ClientError as e:
        logger.error(f"Error checking trade existence: {e.response['Error']['Message']}")
        return False

def get_user_trades(user_id: str, limit: int = 50):
    """Fetch recent trades for a user."""
    if IS_LOCAL:
        return MOCK_TRADES.get(user_id, [])[:limit]
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

def clear_user_trades(user_id: str):
    """Delete all trade entries for a user from the ScalarTrades table."""
    if IS_LOCAL:
        MOCK_TRADES[user_id] = []
        _save_mock_db()
        return True
    try:
        # First, query to get all sort keys
        response = trades_table.query(
            KeyConditionExpression="userId = :uid",
            ExpressionAttributeValues={":uid": user_id},
            ProjectionExpression="userId, sortKey"
        )
        items = response.get("Items", [])
        
        while "LastEvaluatedKey" in response:
            response = trades_table.query(
                KeyConditionExpression="userId = :uid",
                ExpressionAttributeValues={":uid": user_id},
                ProjectionExpression="userId, sortKey",
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))

        # Batch delete items
        with trades_table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"userId": item["userId"], "sortKey": item["sortKey"]})
        
        logger.info(f"Cleared {len(items)} trades for user {user_id}")
        return True
    except ClientError as e:
        logger.error(f"Error clearing trades for {user_id}: {e.response['Error']['Message']}")
        return False

def get_users():
    """Fetch all users to run tracker for."""
    if IS_LOCAL:
        return list(MOCK_DB.keys())
    try:
        # In a very large system, we would use an index or pagination
        response = table.scan(ProjectionExpression="userId")
        return [item["userId"] for item in response.get("Items", [])]
    except ClientError as e:
        logger.error(f"Error scanning users: {e.response['Error']['Message']}")
        return []
