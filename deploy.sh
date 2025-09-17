#!/bin/bash

# Aura Production Deployment Script
set -e

echo "🚀 Starting Aura Production Deployment..."

# Check if .env.prod exists
if [ ! -f .env.prod ]; then
    echo "❌ .env.prod file not found!"
    echo "Please create .env.prod with your production environment variables."
    echo "You can use .env.prod.example as a template."
    exit 1
fi

# Load environment variables
export $(cat .env.prod | grep -v '^#' | xargs)

# Check required environment variables
required_vars=("POSTGRES_PASSWORD" "SECRET_KEY" "GOOGLE_CLIENT_ID" "GOOGLE_CLIENT_SECRET" "AMPLITUDE_API_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set in .env.prod"
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Create SSL directory if it doesn't exist
mkdir -p ssl

# Check if SSL certificates exist
if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then
    echo "⚠️  SSL certificates not found in ssl/ directory"
    echo "Please add your SSL certificates:"
    echo "  - ssl/cert.pem (your SSL certificate)"
    echo "  - ssl/key.pem (your private key)"
    echo ""
    echo "For development, you can generate self-signed certificates:"
    echo "  openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes"
    exit 1
fi

echo "✅ SSL certificates found"

# Build and start services
echo "🔨 Building and starting services..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Check service health
echo "🔍 Checking service health..."

# Check backend health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed"
    docker-compose -f docker-compose.prod.yml logs backend
    exit 1
fi

# Check frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is healthy"
else
    echo "❌ Frontend health check failed"
    docker-compose -f docker-compose.prod.yml logs frontend
    exit 1
fi

echo "🎉 Deployment completed successfully!"
echo ""
echo "Your application is now running at:"
echo "  Frontend: https://yourdomain.com"
echo "  Backend API: https://yourdomain.com/api"
echo "  Health Check: https://yourdomain.com/health"
echo ""
echo "To view logs:"
echo "  docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "To stop the application:"
echo "  docker-compose -f docker-compose.prod.yml down"
