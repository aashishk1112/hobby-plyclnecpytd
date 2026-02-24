#!/bin/bash
# -----------------------------------------------------------------------------
# Scalar Planck: Live AWS Authentication Setup Guide
# -----------------------------------------------------------------------------
# This script provides the CLI commands to set up real Cognito Auth Flow.
# 
# Usage: 
# 1. Obtain Google Client ID/Secret from Google Cloud Console.
# 2. Obtain Twitter Client ID/Secret from Twitter Developer Portal.
# 3. Fill in the variables below and run the commands.
# -----------------------------------------------------------------------------

set -e

PROJECT_NAME="scalar-planck"
REGION="ap-south-1" # Your detected region

# 1. Create User Pool
echo "🚀 Creating Live Cognito User Pool in $REGION..."
POOL_ID=$(aws cognito-idp create-user-pool \
    --pool-name "${PROJECT_NAME}-user-pool" \
    --region $REGION \
    --auto-verified-attributes email \
    --username-attributes email \
    --query 'UserPool.Id' --output text)

echo "✅ User Pool Created: $POOL_ID"

# 2. Create User Pool Client
echo "🚀 Creating User Pool Client..."
CLIENT_ID=$(aws cognito-idp create-user-pool-client \
    --user-pool-id $POOL_ID \
    --client-name "${PROJECT_NAME}-client" \
    --allowed-oauth-flows "code" "implicit" \
    --allowed-oauth-scopes "phone" "email" "openid" "profile" "aws.cognito.signin.user.admin" \
    --callback-urls "http://localhost:3001/" \
    --logout-urls "http://localhost:3001/" \
    --supported-identity-providers "COGNITO" "Google" "Twitter" \
    --query 'UserPoolClient.ClientId' --output text)

echo "✅ Client ID Created: $CLIENT_ID"

# 3. Set Domain
echo "🚀 Setting Cognito Domain..."
aws cognito-idp create-user-pool-domain \
    --domain "${PROJECT_NAME}-auth" \
    --user-pool-id $POOL_ID

# -----------------------------------------------------------------------------
# Instructions for Social Providers
# -----------------------------------------------------------------------------
# Google: Create a Google Identity Provider via AWS Console using your Client ID.
# Twitter: Create an OIDC Identity Provider via AWS Console for Twitter.
# 
# Mapping (Google): email -> email, sub -> username
# Mapping (Twitter): email -> email, sub -> username
# -----------------------------------------------------------------------------

echo "-----------------------------------------------------------------------------"
echo "🎉 Setup Complete! Use these IDs in your .aws_config.json for Live Mode:"
echo "REGION: $REGION"
echo "USER_POOL_ID: $POOL_ID"
echo "USER_POOL_CLIENT_ID: $CLIENT_ID"
echo "-----------------------------------------------------------------------------"
