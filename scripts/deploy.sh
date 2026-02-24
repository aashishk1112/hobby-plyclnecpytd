#!/bin/bash
set -e

# Configuration
PROJECT_NAME="scalar-planck"
REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO_BACKEND="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${PROJECT_NAME}-backend"
ECR_REPO_FRONTEND="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${PROJECT_NAME}-frontend"

echo "🚀 Starting Deployment Process for ${PROJECT_NAME}..."

# 1. Login to ECR
echo "🔑 Logging in to Amazon ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# 2. Build and Push Backend
echo "📦 Building Backend Image..."
docker build -t ${PROJECT_NAME}-backend ./backend
docker tag ${PROJECT_NAME}-backend:latest ${ECR_REPO_BACKEND}:latest
echo "📤 Pushing Backend Image to ECR..."
docker push ${ECR_REPO_BACKEND}:latest

# 3. Apply Terraform (Infrastructure First)
echo "🏗️ Applying Infrastructure changes via Terraform..."
cd terraform
terraform init
terraform apply -auto-approve \
  -var="project_name=${PROJECT_NAME}" \
  -var="region=${REGION}"

# Capture Outputs
FRONTEND_BUCKET="${PROJECT_NAME}-frontend-${REGION}"
API_URL=$(terraform output -raw api_gateway_url)
COGNITO_POOL=$(terraform output -raw cognito_user_pool_id)
COGNITO_CLIENT=$(terraform output -raw cognito_client_id)
cd ..

# 4. Generate .aws_config.json for frontend
echo "📝 Generating frontend config..."
cat <<EOF > .aws_config.json
{
  "REGION": "${REGION}",
  "USER_POOL_ID": "${COGNITO_POOL}",
  "USER_POOL_CLIENT_ID": "${COGNITO_CLIENT}",
  "API_URL": "${API_URL}"
}
EOF
cp .aws_config.json frontend/

# 5. Build and Deploy Frontend to S3
echo "📦 Building Frontend Static Site..."
cd frontend
npm install
npm run build # Ensure Next.js is set to export mode
cd ..

echo "📤 Syncing Frontend to S3..."
aws s3 sync frontend/out s3://${FRONTEND_BUCKET} --delete

echo "✅ Deployment Complete!"
echo "📍 Frontend URL: http://${FRONTEND_BUCKET}.s3-website-${REGION}.amazonaws.com"
