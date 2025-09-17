# AWS Free Tier Deployment Guide for Aura

This guide is specifically optimized for AWS Free Tier usage, ensuring you stay within the free tier limits while running your Aura application.

## 🆓 AWS Free Tier Limits

### What's Included in Free Tier (12 months)
- **EC2**: 750 hours/month of t2.micro instances
- **RDS**: 750 hours/month of db.t2.micro, 20GB storage
- **ElastiCache**: 750 hours/month of cache.t2.micro
- **ECS Fargate**: 20GB-hours/month of vCPU, 40GB-hours/month of memory
- **Application Load Balancer**: 750 hours/month, 15GB data processing
- **NAT Gateway**: 750 hours/month, 1GB data processing
- **Data Transfer**: 1GB/month out to internet

### ⚠️ Important Free Tier Considerations

1. **NAT Gateway costs $45/month** - This is the biggest cost outside free tier
2. **Data transfer** beyond 1GB/month incurs charges
3. **Some features** like encryption, backups, and multi-AZ are not available in free tier

## 🏗️ Free Tier Optimized Architecture

### What We've Optimized

1. **RDS PostgreSQL**:
   - `db.t2.micro` instance (free tier eligible)
   - 20GB storage (free tier limit)
   - No encryption (not available in free tier)
   - No automated backups (not available in free tier)
   - Single AZ deployment

2. **ElastiCache Redis**:
   - `cache.t2.micro` instance (free tier eligible)
   - Single node (no replication for free tier)
   - No encryption (not available in free tier)

3. **ECS Fargate**:
   - 256 CPU units, 512MB memory per task (free tier limits)
   - Single instance of each service (no auto-scaling)
   - Optimized for minimal resource usage

4. **Networking**:
   - Single NAT Gateway (still costs $45/month)
   - Minimal data transfer

## 💰 Cost Breakdown

### Free Tier Eligible (0 cost for 12 months)
- **ECS Fargate**: ~$0/month (within free tier limits)
- **RDS PostgreSQL**: ~$0/month (within free tier limits)
- **ElastiCache Redis**: ~$0/month (within free tier limits)
- **Application Load Balancer**: ~$0/month (within free tier limits)

### Costs Outside Free Tier
- **NAT Gateway**: ~$45/month (750 hours + data processing)
- **Data Transfer**: ~$0.09/GB after 1GB/month
- **Total**: ~$45-50/month

## 🚀 Deployment Steps

### 1. Prerequisites
```bash
# Install AWS CLI
aws --version

# Install Terraform
terraform --version

# Configure AWS CLI
aws configure
```

### 2. Set Up Environment
```bash
# Copy and edit environment file
cp env.prod.template .env.aws
# Edit .env.aws with your values
```

### 3. Configure Terraform
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 4. Deploy Infrastructure
```bash
# Initialize Terraform
terraform init

# Review the plan (check for any non-free tier resources)
terraform plan

# Apply the infrastructure
terraform apply
```

### 5. Deploy Application
```bash
# Build and push Docker images
./aws-deploy.sh
```

## 🔧 Free Tier Optimizations Applied

### RDS Configuration
```hcl
instance_class = "db.t2.micro"  # Free tier eligible
allocated_storage = 20          # Free tier limit
storage_encrypted = false       # Not available in free tier
backup_retention_period = 0     # No backups in free tier
skip_final_snapshot = true      # Required for free tier
```

### ElastiCache Configuration
```hcl
node_type = "cache.t2.micro"           # Free tier eligible
num_cache_clusters = 1                 # Single node for free tier
automatic_failover_enabled = false     # Not available in free tier
multi_az_enabled = false              # Not available in free tier
at_rest_encryption_enabled = false    # Not available in free tier
transit_encryption_enabled = false    # Not available in free tier
```

### ECS Configuration
```hcl
cpu = 256      # Free tier limit
memory = 512   # Free tier limit
desired_count = 1  # Single instance for free tier
```

## 📊 Monitoring Free Tier Usage

### Check Your Usage
```bash
# Check ECS usage
aws ecs list-tasks --cluster aura-cluster

# Check RDS usage
aws rds describe-db-instances --db-instance-identifier aura-postgres

# Check ElastiCache usage
aws elasticache describe-replication-groups --replication-group-id aura-redis
```

### AWS Cost Explorer
1. Go to AWS Cost Explorer
2. Set date range to current month
3. Filter by service to see usage
4. Set up billing alerts for $5, $10, $25 thresholds

## ⚠️ Free Tier Limitations

### What You'll Miss
1. **No automated backups** - Manual backups only
2. **No encryption** - Data not encrypted at rest
3. **Single AZ** - No high availability
4. **No auto-scaling** - Manual scaling only
5. **Limited performance** - t2.micro instances are basic

### Workarounds
1. **Manual backups**: Create snapshots manually
2. **Application-level encryption**: Encrypt sensitive data in your app
3. **Health checks**: Monitor application health
4. **Manual scaling**: Scale up when needed
5. **Optimize code**: Ensure efficient resource usage

## 🔄 Scaling Beyond Free Tier

When you're ready to scale:

1. **Enable encryption**:
   ```hcl
   storage_encrypted = true
   at_rest_encryption_enabled = true
   transit_encryption_enabled = true
   ```

2. **Add high availability**:
   ```hcl
   multi_az_enabled = true
   num_cache_clusters = 2
   automatic_failover_enabled = true
   ```

3. **Enable auto-scaling**:
   ```hcl
   desired_count = 2
   # Add auto-scaling configuration
   ```

4. **Upgrade instance types**:
   ```hcl
   instance_class = "db.t3.small"
   node_type = "cache.t3.small"
   ```

## 🛠️ Troubleshooting Free Tier Issues

### Common Issues

1. **NAT Gateway costs**:
   - Consider using NAT Instance instead (t2.micro)
   - Or use public subnets for development

2. **Data transfer costs**:
   - Monitor data usage
   - Optimize application for minimal data transfer
   - Use CloudFront for static assets

3. **Resource limits**:
   - Monitor free tier usage
   - Set up billing alerts
   - Consider stopping services when not in use

### Cost Optimization Tips

1. **Stop services when not in use**:
   ```bash
   # Stop ECS services
   aws ecs update-service --cluster aura-cluster --service aura-backend-service --desired-count 0
   aws ecs update-service --cluster aura-cluster --service aura-frontend-service --desired-count 0
   ```

2. **Use Spot Instances** (when available):
   - Consider using Spot instances for non-critical workloads
   - Can reduce costs by up to 90%

3. **Monitor usage**:
   - Set up CloudWatch alarms
   - Use AWS Cost Explorer
   - Set up billing alerts

## 📈 Expected Performance

### Free Tier Performance
- **Backend**: ~100-200 requests/minute
- **Database**: ~100 concurrent connections
- **Redis**: ~1000 operations/second
- **Response time**: ~200-500ms

### When to Upgrade
- More than 1000 requests/minute
- Need for high availability
- Require encryption
- Need automated backups
- Performance requirements exceed free tier

## 🎯 Next Steps

1. **Deploy to free tier** using this guide
2. **Monitor usage** and costs
3. **Set up billing alerts**
4. **Plan for scaling** when needed
5. **Consider paid features** as you grow

Remember: The free tier is perfect for development, testing, and small applications. As your application grows, you can easily upgrade to paid tiers with better performance and features.
