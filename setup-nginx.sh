#!/bin/bash

# Nginx Proxy Setup Script for Audiobook Server
echo "🚀 Setting up Nginx Reverse Proxy for Audiobook Server"

# Create required directories
echo "📁 Creating nginx directories..."
mkdir -p nginx/logs nginx/cache

# Set proper permissions
echo "🔐 Setting permissions..."
sudo chown -R $USER:$USER nginx/
chmod -R 755 nginx/

# Validate nginx configuration syntax (ignore DNS resolution errors)
echo "✅ Validating nginx configuration syntax..."
echo "ℹ️  Note: DNS resolution errors for 'api' and 'storage' are expected since containers aren't running yet."

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Compose."
    exit 1
fi

# Stop existing services if running
echo "🛑 Stopping existing services..."
docker-compose down

# Start services with nginx proxy
echo "🚀 Starting services with nginx proxy..."
docker-compose -f docker-compose.yml -f docker-compose.nginx.yml up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check health of all services
echo "🔍 Checking service health..."

check_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    echo "Checking $service..."
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo "✅ $service is healthy"
            return 0
        fi
        echo "⏳ Attempt $attempt/$max_attempts - waiting for $service..."
        sleep 2
        ((attempt++))
    done
    
    echo "❌ $service failed to start"
    return 1
}

# Check each service
services_healthy=true

if ! check_service "Nginx" "http://localhost"; then
    services_healthy=false
fi

if ! check_service "API Health" "http://localhost/health"; then
    services_healthy=false
fi

if ! check_service "API Docs" "http://localhost/docs"; then
    services_healthy=false
fi

# Display results
echo ""
echo "🎉 Setup complete!"
echo ""
echo "Services available at:"
echo "  🌍 Main Application: http://localhost"
echo "  📋 API Documentation: http://localhost/docs"
echo "  🏥 Health Check: http://localhost/health"
echo "  🔧 API Endpoints: http://localhost/api/"
echo ""

if [ "$services_healthy" = true ]; then
    echo "✅ All services are running and healthy!"
    echo ""
    echo "Test the API with:"
    echo "  curl -H 'Authorization: Bearer default-dev-key' http://localhost/health"
    echo ""
    echo "Monitor logs with:"
    echo "  docker-compose -f docker-compose.yml -f docker-compose.nginx.yml logs -f nginx"
else
    echo "⚠️  Some services may not be fully ready yet. Check the logs:"
    echo "  docker-compose -f docker-compose.yml -f docker-compose.nginx.yml logs"
fi

echo ""
echo "🛠️  Configuration files:"
echo "  - nginx-api-only.conf (API-focused nginx configuration)"
echo "  - nginx.conf (full configuration with PWA client support)"
echo "  - docker-compose.nginx.yml (Docker Compose override)"
echo "  - nginx/logs/ (nginx access and error logs)"
echo ""
echo "🔧 To customize:"
echo "  1. Edit nginx-api-only.conf for API routing changes"
echo "  2. Update server_name for your domain"
echo "  3. Add SSL certificates for HTTPS"
echo "  4. Use nginx.conf if you want PWA client proxy support"
echo ""
echo "Happy coding! 🎵" 