# Scalar Planck Manual Deployment Guide

This guide details the steps to manually deploy the application to AWS.

## 1. Prerequisites
- **AWS CLI**: Configured locally.
- **Docker**: For building backend images.
- **Node.js**: For building the frontend.

## 2. Infrastructure Setup (AWS Console)

### DynamoDB
Create two tables:
1.  **ScalarUsers**: Partition key `userId` (String).
2.  **ScalarTrades**: Partition key `userId` (String), Sort key `sortKey` (String).

### Cognito
1.  Create a **User Pool** (e.g., `ScalarUserPool`).
2.  Add an **App Client** (e.g., `ScalarClient`).
3.  (Optional) Add **Identity Providers** (Google).
4.  Note down the **User Pool ID** and **Client ID**.

### Amazon ECR
Create a repository named `scalar-planck-backend`.

## 3. Backend Deployment (Lambda)

1.  **Build and Push Image**:
    ```bash
    aws ecr get-login-password --region <REGION> | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com
    docker build -t scalar-planck-backend ./backend
    docker tag scalar-planck-backend:latest <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/scalar-planck-backend:latest
    docker push <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/scalar-planck-backend:latest
    ```
2.  **Create Lambda**:
    - Choose **Container image**.
    - Select the image from ECR.
    - Set environment variables: `DYNAMODB_TABLE`, `TRADES_TABLE`, `USER_POOL_ID`, `USER_POOL_CLIENT_ID`, `MOCK_AUTH=False`.
    - Grant the Lambda IAM Role permissions to access DynamoDB and Cognito.
3.  **API Gateway**:
    - Create an **HTTP API**.
    - Add a **Proxy integration** to the Lambda function.
    - Note down the **API Endpoint URL**.

## 4. Frontend Deployment (S3)

1.  **Configure**: Update `/frontend/.aws_config.json` with the production IDs and URLs.
2.  **Build**:
    ```bash
    cd frontend
    npm install
    npm run build
    ```
3.  **S3 Hosting**:
    - Create an S3 bucket (e.g., `scalar-planck-web`).
    - Enable **Static website hosting**.
    - Disable **Block Public Access**.
    - Add a **Bucket Policy** for `s3:GetObject` (public read).
    - Sync files: `aws s3 sync frontend/out s3://your-bucket-name --delete`.

## 5. Local Development
For local testing with LocalStack, use: `docker-compose up --build`.
