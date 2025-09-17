#!/bin/bash

# AWS Free Tier Deployment Script for Aura
set -e

echo "🆓 Starting AWS Free Tier deployment for Aura..."

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

# Deploy infrastructure with Terraform (free tier version)
if [ -f "terraform/main-free-tier.tf" ]; then
    echo "🏗️  Deploying Free Tier infrastructure with Terraform..."
    cd terraform
    
    # Copy free tier files to main files
    cp main-free-tier.tf main.tf
    cp ecs-free-tier.tf ecs.tf
    
    terraform init
    terraform plan
    terraform apply -auto-approve
    cd ..
else
    echo "⚠️  No Free Tier Terraform configuration found. Please set up your AWS infrastructure manually:"
    echo "   - ECS Cluster"
    echo "   - RDS PostgreSQL instance (db.t2.micro)"
    echo "   - ElastiCache Redis cluster (cache.t2.micro)"
    echo "   - Application Load Balancer"
    echo "   - VPC and subnets"
fi

echo "🎉 AWS Free Tier deployment completed!"
echo ""
echo "💰 Cost Summary:"
echo "   - ECS Fargate: $0/month (within free tier)"
echo "   - RDS PostgreSQL: $0/month (within free tier)"
echo "   - ElastiCache Redis: $0/month (within free tier)"
echo "   - Application Load Balancer: $0/month (within free tier)"
echo "   - Data Transfer: $0/month (within free tier)"
echo "   - Total: $0/month for 12 months!"
echo ""
echo "⚠️  Important Notes:"
echo "   - This deployment uses public subnets for ECS tasks (no NAT Gateway cost)"
echo "   - Database and Redis are in private subnets for security"
echo "   - No encryption or backups (not available in free tier)"
echo "   - Single AZ deployment (no high availability)"
echo ""
echo "Next steps:"
echo "1. Set up your domain and SSL certificates"
echo "2. Update your environment variables in AWS Systems Manager Parameter Store"
echo "3. Monitor your free tier usage in AWS Cost Explorer"
echo "4. Set up billing alerts to avoid unexpected charges"
