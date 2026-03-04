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
# Constants
AWS_REGION = get_config("AWS_REGION", "ap-south-1")
TABLE_NAME = get_config("DYNAMODB_TABLE", "ScalarUsers")
TRADES_TABLE_NAME = get_config("TRADES_TABLE", "ScalarTrades")
IS_LOCAL = get_config("IS_LOCAL", "false").lower() == "true"

def get_dynamodb_resource():
    if IS_LOCAL:
        return boto3.resource("dynamodb", endpoint_url="http://localhost:4566", region_name="us-east-1")
    return boto3.resource("dynamodb", region_name=AWS_REGION)

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
            "terminatedWallets": [],
            "initialBalance": 100.0,
            "balance": 100.0,
            "balanceThreshold": 0.0,
            "name": None,
            "picture": None,
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

def update_user_balance(user_id: str, balance: float):
    """Update only the current balance for a user."""
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
            
        # Check for duplicate active wallet
        if address in current_wallets:
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

def is_trade_processed(user_id: str, tx_hash: str):
    """Check if a trade ID already exists in ScalarTrades."""
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
    try:
        # In a very large system, we would use an index or pagination
        response = table.scan(ProjectionExpression="userId")
        return [item["userId"] for item in response.get("Items", [])]
    except ClientError as e:
        logger.error(f"Error scanning users: {e.response['Error']['Message']}")
        return []
