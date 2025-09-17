#!/bin/bash

# Health check script for Aura production deployment

echo "🔍 Checking Aura application health..."

# Check if services are running
echo "📊 Checking Docker services..."
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "🏥 Health checks:"

# Check backend health
echo -n "Backend API: "
if curl -f -s http://localhost:8000/health > /dev/null; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

# Check frontend
echo -n "Frontend: "
if curl -f -s http://localhost:3000 > /dev/null; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

# Check database
echo -n "Database: "
if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

# Check Redis
echo -n "Redis: "
if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

echo ""
echo "📈 Resource usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

echo ""
echo "📋 Recent logs (last 10 lines):"
docker-compose -f docker-compose.prod.yml logs --tail=10
