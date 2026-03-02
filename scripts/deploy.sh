#!/bin/bash
set -e

# Configuration
PROJECT_NAME="scalar-planck"
REGION=${AWS_DEFAULT_REGION:-"us-east-1"}

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Scalar Planck Deployment Helper${NC}"

echo -e "${BLUE}📦 Building Backend Image...${NC}"
docker build -t ${PROJECT_NAME}-backend ./backend

echo -e "${BLUE}📦 Building Frontend...${NC}"
cd frontend && npm install && npm run build && cd ..

echo -e "${GREEN}✅ Build Complete.${NC}"
echo -e "Follow the steps in DEPLOYMENT.md to manually push to ECR and S3."
