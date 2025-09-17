# Aura Production Deployment Guide

This guide will help you deploy the Aura application to production using Docker.

## Prerequisites

1. **Server Requirements:**
   - Ubuntu 20.04+ or similar Linux distribution
   - Docker and Docker Compose installed
   - At least 2GB RAM and 10GB disk space
   - Domain name pointing to your server

2. **SSL Certificates:**
   - SSL certificate and private key for your domain
   - Or use Let's Encrypt for free SSL certificates

3. **Environment Variables:**
   - All required API keys and secrets

## Quick Deployment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jindalsaj/aura.git
   cd aura
   ```

2. **Create production environment file:**
   ```bash
   cp .env.prod.example .env.prod
   # Edit .env.prod with your actual values
   ```

3. **Add SSL certificates:**
   ```bash
   mkdir ssl
   # Add your SSL certificates:
   # - ssl/cert.pem (your SSL certificate)
   # - ssl/key.pem (your private key)
   ```

4. **Deploy:**
   ```bash
   ./deploy.sh
   ```

## Manual Deployment Steps

### 1. Environment Setup

Create `.env.prod` with the following variables:

```bash
# Database
POSTGRES_DB=aura_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-password

# Security
SECRET_KEY=your-very-secure-secret-key

# CORS
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Plaid
PLAID_CLIENT_ID=your-plaid-client-id
PLAID_SECRET=your-plaid-secret
PLAID_ENV=production

# Amplitude
AMPLITUDE_API_KEY=32508d20fbb76ee720aade9a896e02e0

# Frontend
REACT_APP_API_URL=https://api.yourdomain.com
```

### 2. SSL Certificates

#### Option A: Let's Encrypt (Recommended)
```bash
# Install certbot
sudo apt install certbot

# Generate certificates
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
sudo chown $USER:$USER ssl/*
```

#### Option B: Self-signed (Development only)
```bash
mkdir ssl
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes
```

### 3. Deploy with Docker Compose

```bash
# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Check service health
curl https://yourdomain.com/health
```

## Service Architecture

The production deployment includes:

- **PostgreSQL**: Database with persistent storage
- **Redis**: Caching and session storage
- **Backend**: FastAPI application with 4 workers
- **Frontend**: React app served by Nginx
- **Nginx**: Reverse proxy with SSL termination and rate limiting

## Monitoring and Maintenance

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Update Application
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Backup Database
```bash
# Create backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres aura_db > backup.sql

# Restore backup
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres aura_db < backup.sql
```

### Scale Services
```bash
# Scale backend workers
docker-compose -f docker-compose.prod.yml up -d --scale backend=3
```

## Security Considerations

1. **Environment Variables**: Never commit `.env.prod` to version control
2. **SSL Certificates**: Keep certificates secure and renew before expiration
3. **Database**: Use strong passwords and consider network restrictions
4. **Rate Limiting**: Configured in Nginx to prevent abuse
5. **Firewall**: Only expose ports 80 and 443

## Troubleshooting

### Common Issues

1. **SSL Certificate Errors:**
   - Ensure certificates are in PEM format
   - Check file permissions (should be readable by Docker)

2. **Database Connection Issues:**
   - Verify PostgreSQL is running: `docker-compose -f docker-compose.prod.yml ps`
   - Check database logs: `docker-compose -f docker-compose.prod.yml logs postgres`

3. **Backend Health Check Fails:**
   - Check backend logs: `docker-compose -f docker-compose.prod.yml logs backend`
   - Verify environment variables are set correctly

4. **Frontend Not Loading:**
   - Check if frontend container is running
   - Verify REACT_APP_API_URL is correct

### Performance Optimization

1. **Database Optimization:**
   - Add database indexes for frequently queried fields
   - Configure connection pooling

2. **Caching:**
   - Redis is configured for session storage
   - Consider adding application-level caching

3. **CDN:**
   - Use a CDN for static assets
   - Configure proper cache headers

## Support

For deployment issues:
1. Check the logs: `docker-compose -f docker-compose.prod.yml logs`
2. Verify all environment variables are set
3. Ensure SSL certificates are valid
4. Check server resources (CPU, memory, disk space)
