# Scalar Planck Deployment Guide

This project supports both local containerized development and full AWS serverless deployment.

## 1. Local Development (Docker)
Run the entire stack (Frontend, Backend, and LocalStack) locally:

```bash
docker-compose up --build
```

- **Frontend**: [http://localhost:3001](http://localhost:3001)
- **Backend**: [http://localhost:8001](http://localhost:8001) (via Lambda RIE)
- **LocalStack**: [http://localhost:4566](http://localhost:4566) (DynamoDB, Cognito emulation)

## 2. AWS Deployment (Production)
Deploy to AWS with Lambda-based backend and S3-based static frontend.

### Prerequisites
1.  **AWS CLI**: Configured with appropriate credentials.
2.  **Terraform**: Installed and initialized.
3.  **Docker**: Running (needed to build backend images).

### One-Click Deployment
Run the consolidated deployment script:

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### What the script does:
1.  **Backend**: Builds the Docker image and pushes it to Amazon ECR.
2.  **Infrastructure**: Runs `terraform apply` to provision:
    - **Lambda**: For FastAPI (via Mangum) and Tracker (Scheduled).
    - **S3**: For static frontend hosting.
    - **DynamoDB**: For user and trade persistence.
    - **Cognito**: For Google and Twitter authentication.
3.  **Frontend**: Builds the static site and syncs it to the S3 bucket.

## 3. Configuration Notes
- **Authentication**: Social login (Google/Twitter) requires valid Client IDs/Secrets in the AWS Cognito Console or via Terraform variables.
- **Mock Mode**: For local testing without real AWS account credentials, ensure `MOCK_AUTH=True` in your environment.
