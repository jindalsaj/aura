#!/bin/bash

# AWS Deployment Script for Aura
set -e

echo "🚀 Starting AWS deployment for Aura..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first:"
    echo "   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run:"
    echo "   aws configure"
    exit 1
fi

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
APP_NAME="aura"

echo "✅ AWS Account: $AWS_ACCOUNT_ID"
echo "✅ AWS Region: $AWS_REGION"

# Check if .env.aws exists
if [ ! -f .env.aws ]; then
    echo "❌ .env.aws file not found!"
    echo "Please create .env.aws with your AWS-specific environment variables."
    echo "You can use env.prod.template as a starting point."
    exit 1
fi

# Load environment variables
export $(cat .env.aws | grep -v '^#' | xargs)

# Check required environment variables
required_vars=("POSTGRES_PASSWORD" "SECRET_KEY" "GOOGLE_CLIENT_ID" "GOOGLE_CLIENT_SECRET" "AMPLITUDE_API_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set in .env.aws"
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Create ECR repositories
echo "📦 Creating ECR repositories..."
aws ecr create-repository --repository-name $APP_NAME-backend --region $AWS_REGION 2>/dev/null || echo "Backend repository already exists"
aws ecr create-repository --repository-name $APP_NAME-frontend --region $AWS_REGION 2>/dev/null || echo "Frontend repository already exists"

# Get ECR login token
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push backend image
echo "🔨 Building and pushing backend image..."
docker build -f backend/Dockerfile.prod -t $APP_NAME-backend ./backend
docker tag $APP_NAME-backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$APP_NAME-backend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$APP_NAME-backend:latest

# Build and push frontend image
echo "🔨 Building and pushing frontend image..."
docker build -f frontend/Dockerfile.prod -t $APP_NAME-frontend ./frontend
docker tag $APP_NAME-frontend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$APP_NAME-frontend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$APP_NAME-frontend:latest

echo "✅ Images pushed to ECR successfully!"

# Deploy infrastructure with Terraform (if terraform files exist)
if [ -f "terraform/main.tf" ]; then
    echo "🏗️  Deploying infrastructure with Terraform..."
    cd terraform
    terraform init
    terraform plan
    terraform apply -auto-approve
    cd ..
else
    echo "⚠️  No Terraform configuration found. Please set up your AWS infrastructure manually:"
    echo "   - ECS Cluster"
    echo "   - RDS PostgreSQL instance"
    echo "   - ElastiCache Redis cluster"
    echo "   - Application Load Balancer"
    echo "   - VPC and subnets"
fi

echo "🎉 AWS deployment completed!"
echo ""
echo "Next steps:"
echo "1. Set up your AWS infrastructure (ECS, RDS, etc.)"
echo "2. Create ECS task definitions using the pushed images"
echo "3. Configure your domain and SSL certificates"
echo "4. Update your environment variables in AWS Systems Manager Parameter Store"
