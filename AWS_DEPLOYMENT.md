# AWS Deployment Guide for Aura

This guide will help you deploy the Aura application to AWS using ECS Fargate, RDS, and ElastiCache.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Terraform** installed (version >= 1.0)
4. **Docker** installed
5. **Domain name** pointing to your AWS resources

## Architecture Overview

The deployment creates:

- **VPC** with public and private subnets across 2 AZs
- **ECS Fargate** cluster running your containers
- **RDS PostgreSQL** database in private subnets
- **ElastiCache Redis** cluster for caching
- **Application Load Balancer** with SSL termination
- **CloudWatch** for logging and monitoring

## Step-by-Step Deployment

### 1. Configure AWS CLI

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and region
```

### 2. Set Up Environment Variables

Create a `.env.aws` file with your production values:

```bash
cp env.prod.template .env.aws
# Edit .env.aws with your actual values
```

### 3. Configure Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 4. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply the infrastructure
terraform apply
```

This will create:
- VPC and networking components
- RDS PostgreSQL instance
- ElastiCache Redis cluster
- ECS cluster and task definitions
- Application Load Balancer
- Security groups and IAM roles

### 5. Build and Push Docker Images

```bash
# Run the AWS deployment script
./aws-deploy.sh
```

This script will:
- Create ECR repositories
- Build and push your Docker images
- Tag images for ECS deployment

### 6. Set Up SSL Certificate

#### Option A: AWS Certificate Manager (Recommended)

```bash
# Request a certificate
aws acm request-certificate \
  --domain-name yourdomain.com \
  --subject-alternative-names www.yourdomain.com \
  --validation-method DNS \
  --region us-east-1

# Follow the DNS validation process
# Then update your ALB listener to use HTTPS
```

#### Option B: Import Existing Certificate

```bash
aws acm import-certificate \
  --certificate fileb://cert.pem \
  --private-key fileb://key.pem \
  --region us-east-1
```

### 7. Configure Domain and DNS

1. **Get your ALB DNS name:**
   ```bash
   terraform output alb_dns_name
   ```

2. **Update your DNS records:**
   - Create a CNAME record pointing your domain to the ALB DNS name
   - Or create an A record using the ALB IP addresses

### 8. Update ECS Services

After your infrastructure is deployed, update the ECS services to use the new images:

```bash
# Update backend service
aws ecs update-service \
  --cluster aura-cluster \
  --service aura-backend-service \
  --force-new-deployment

# Update frontend service
aws ecs update-service \
  --cluster aura-cluster \
  --service aura-frontend-service \
  --force-new-deployment
```

## Environment Variables

The following environment variables are automatically configured:

### Backend Environment Variables
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Application secret key
- `ALLOWED_ORIGINS` - CORS allowed origins

### Secrets (stored in AWS Systems Manager Parameter Store)
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `PLAID_CLIENT_ID`
- `PLAID_SECRET`
- `AMPLITUDE_API_KEY`
- `OPENAI_API_KEY`

### Frontend Environment Variables
- `REACT_APP_API_URL` - Backend API URL
- `REACT_APP_AMPLITUDE_API_KEY` - Amplitude API key

## Monitoring and Logs

### View Logs
```bash
# Backend logs
aws logs tail /ecs/aura-backend --follow

# Frontend logs
aws logs tail /ecs/aura-frontend --follow
```

### Monitor Services
```bash
# Check ECS service status
aws ecs describe-services \
  --cluster aura-cluster \
  --services aura-backend-service aura-frontend-service

# Check ALB health
aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw backend_target_group_arn)
```

## Scaling

### Scale ECS Services
```bash
# Scale backend to 3 instances
aws ecs update-service \
  --cluster aura-cluster \
  --service aura-backend-service \
  --desired-count 3

# Scale frontend to 3 instances
aws ecs update-service \
  --cluster aura-cluster \
  --service aura-frontend-service \
  --desired-count 3
```

### Auto Scaling
You can set up auto scaling based on CPU/memory usage:

```bash
# Create auto scaling target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/aura-cluster/aura-backend-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10
```

## Security Best Practices

1. **Network Security:**
   - Database and Redis are in private subnets
   - Only ALB is accessible from the internet
   - Security groups restrict traffic between services

2. **Secrets Management:**
   - API keys stored in AWS Systems Manager Parameter Store
   - IAM roles with minimal required permissions
   - No secrets in environment variables

3. **Encryption:**
   - RDS encryption at rest enabled
   - ElastiCache encryption in transit and at rest
   - ALB SSL/TLS termination

## Cost Optimization

1. **Use Spot Instances:**
   - Consider using Spot instances for non-critical workloads
   - Set up mixed instance types for better availability

2. **Right-size Resources:**
   - Monitor CPU and memory usage
   - Adjust ECS task CPU/memory allocation
   - Use CloudWatch metrics to optimize

3. **Reserved Instances:**
   - Consider RDS Reserved Instances for predictable workloads
   - Use Savings Plans for ECS Fargate

## Troubleshooting

### Common Issues

1. **ECS Tasks Not Starting:**
   ```bash
   # Check task definition
   aws ecs describe-task-definition --task-definition aura-backend
   
   # Check service events
   aws ecs describe-services --cluster aura-cluster --services aura-backend-service
   ```

2. **Database Connection Issues:**
   ```bash
   # Check RDS status
   aws rds describe-db-instances --db-instance-identifier aura-postgres
   
   # Check security groups
   aws ec2 describe-security-groups --group-ids $(terraform output -raw rds_security_group_id)
   ```

3. **ALB Health Check Failures:**
   ```bash
   # Check target health
   aws elbv2 describe-target-health \
     --target-group-arn $(terraform output -raw backend_target_group_arn)
   ```

### Useful Commands

```bash
# Get all outputs
terraform output

# View ECS cluster
aws ecs describe-clusters --clusters aura-cluster

# View running tasks
aws ecs list-tasks --cluster aura-cluster

# View task details
aws ecs describe-tasks --cluster aura-cluster --tasks <task-arn>
```

## Cleanup

To destroy all resources:

```bash
cd terraform
terraform destroy
```

**Warning:** This will delete all data including the database. Make sure to backup any important data first.

## Support

For issues:
1. Check CloudWatch logs
2. Verify security group rules
3. Check ECS service events
4. Review ALB target health
5. Ensure all environment variables are set correctly
