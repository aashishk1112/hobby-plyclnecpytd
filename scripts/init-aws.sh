#!/bin/bash
# LocalStack Initialization Script (Simplified Setup)

# Ensure AWS CLI has dummy credentials for LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

# Use provided endpoint or default to localhost
ENDPOINT_URL=${LOCALSTACK_ENDPOINT:-http://localhost:4566}
REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "🛠️ Initializing LocalStack Services at $ENDPOINT_URL (Region: $REGION)..."

# 1. Create DynamoDB Tables
echo "📂 Creating DynamoDB table: ScalarUsers..."
aws --endpoint-url=$ENDPOINT_URL dynamodb create-table \
    --table-name ScalarUsers \
    --attribute-definitions AttributeName=userId,AttributeType=S \
    --key-schema AttributeName=userId,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region $REGION || echo "⚠️ ScalarUsers table already exists or error."

echo "📂 Creating DynamoDB table: ScalarTrades..."
aws --endpoint-url=$ENDPOINT_URL dynamodb create-table \
    --table-name ScalarTrades \
    --attribute-definitions AttributeName=userId,AttributeType=S AttributeName=sortKey,AttributeType=S \
    --key-schema AttributeName=userId,KeyType=HASH AttributeName=sortKey,KeyType=RANGE \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region $REGION || echo "⚠️ ScalarTrades table already exists or error."

# 2. Cognito User Pool Setup
echo "👤 Creating Cognito User Pool..."
POOL_ID=$(aws --endpoint-url=$ENDPOINT_URL cognito-idp create-user-pool \
    --pool-name ScalarUserPool \
    --region $REGION \
    --query 'UserPool.Id' --output text)

if [ -z "$POOL_ID" ] || [ "$POOL_ID" == "None" ] || [[ "$POOL_ID" == *"Error"* ]]; then
    echo "❌ Error: Failed to create User Pool. Capturing output instead..."
    aws --endpoint-url=$ENDPOINT_URL cognito-idp create-user-pool --pool-name ScalarUserPool --region $REGION
    POOL_ID="us-east-1_dummy"
else
    echo "✅ User Pool Created: $POOL_ID"
fi

echo "👤 Creating User Pool Client..."
CLIENT_ID=$(aws --endpoint-url=$ENDPOINT_URL cognito-idp create-user-pool-client \
    --user-pool-id "$POOL_ID" \
    --client-name ScalarClient \
    --region $REGION \
    --query 'UserPoolClient.ClientId' --output text || echo "dummy_client")

echo "✅ Client ID Created: $CLIENT_ID"

# 3. Add Identity Providers (Google & Twitter)
# These will likely fail in Community LocalStack but we include them for completeness.
if [ "$POOL_ID" != "us-east-1_dummy" ]; then
    echo "🔗 Configuring Google Identity Provider..."
    aws --endpoint-url=$ENDPOINT_URL cognito-idp create-identity-provider \
        --user-pool-id "$POOL_ID" \
        --provider-name Google \
        --provider-type Google \
        --provider-details "{\"client_id\":\"${GOOGLE_CLIENT_ID:-google_placeholder}\",\"client_secret\":\"${GOOGLE_CLIENT_SECRET:-google_placeholder}\",\"authorize_scopes\":\"email openid profile\"}" \
        --attribute-mapping "{\"email\":\"email\",\"username\":\"sub\"}" \
        --region $REGION || echo "⚠️ Could not create Google IdP (expected in LocalStack Community)."

    echo "🔗 Configuring Twitter Identity Provider..."
    aws --endpoint-url=$ENDPOINT_URL cognito-idp create-identity-provider \
        --user-pool-id "$POOL_ID" \
        --provider-name Twitter \
        --provider-type OIDC \
        --provider-details "{\"client_id\":\"${TWITTER_CLIENT_ID:-twitter_placeholder}\",\"client_secret\":\"${TWITTER_CLIENT_SECRET:-twitter_placeholder}\",\"oidc_issuer\":\"https://twitter.com\",\"authorize_scopes\":\"openid email profile\"}" \
        --attribute-mapping "{\"email\":\"email\",\"username\":\"sub\"}" \
        --region $REGION || echo "⚠️ Could not create Twitter IdP (expected in LocalStack Community)."
fi

# 4. Inject Unified Configuration into Secrets Manager
echo "🔐 Seeding unified configuration into Secrets Manager (ScalarPlanckConfig)..."
SECRET_JSON=$(cat <<EOF
{
  "POLY_API_KEY": "mock-poly-key",
  "POLY_API_SECRET": "mock-poly-secret",
  "POLY_API_PASSPHRASE": "mock-poly-passphrase",
  "POLY_PRIVATE_KEY": "//0x0000000000000000000000000000000000000000000000000000000000000000",
  "PAPER_TRADING": "True",
  "LOG_LEVEL": "INFO",
  "MOCK_AUTH": "false",
  "GOOGLE_CLIENT_ID": "mock-google-id",
  "GOOGLE_CLIENT_SECRET": "mock-google-secret",
  "TWITTER_CLIENT_ID": "YOUR_TWITTER_CLIENT_ID",
  "TWITTER_CLIENT_SECRET": "YOUR_TWITTER_CLIENT_SECRET",
  "STRIPE_SECRET_KEY": "sk_test_mock",
  "STRIPE_WEBHOOK_SECRET": "whsec_mock",
  "FRONTEND_URL": "https://d3ukbv7x6b8vr.cloudfront.net",
  "USER_POOL_ID": "$POOL_ID",
  "USER_POOL_CLIENT_ID": "$CLIENT_ID",
  "DYNAMODB_TABLE": "ScalarUsers",
  "TRADES_TABLE": "ScalarTrades"
}
EOF
)

aws --endpoint-url=$ENDPOINT_URL secretsmanager create-secret \
    --name ScalarPlanckConfig \
    --description "Master Configuration for Scalar-Planck" \
    --secret-string "$SECRET_JSON" \
    --region $REGION || echo "⚠️ Secret ScalarPlanckConfig already exists or could not be created."

# 5. Output Configuration
CONFIG_JSON="{\"REGION\": \"$REGION\", \"USER_POOL_ID\": \"$POOL_ID\", \"USER_POOL_CLIENT_ID\": \"$CLIENT_ID\", \"DYNAMODB_TABLE\": \"ScalarUsers\"}"
echo "$CONFIG_JSON" > /.aws_config.json
# Write to the project root as well so frontend/backend can see it
echo "$CONFIG_JSON" > /app_root/.aws_config.json || echo "Could not write to /app_root"

echo "✅ LocalStack Initialization Complete."
