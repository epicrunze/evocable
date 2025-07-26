#!/bin/bash
# Network Setup Script for Evocable Separated Docker Compose

set -e

NETWORK_NAME="evocable-network"
MAIN_COMPOSE="docker-compose.yml"
NGINX_COMPOSE="docker-compose.nginx.yml"

echo "🌐 Evocable Docker Network Management"
echo "=================================="

# Function to create the external network
create_network() {
    echo "📡 Creating external Docker network: $NETWORK_NAME"
    
    if docker network ls | grep -q "$NETWORK_NAME"; then
        echo "✅ Network $NETWORK_NAME already exists"
    else
        docker network create "$NETWORK_NAME"
        echo "✅ Network $NETWORK_NAME created successfully"
    fi
}

# Function to start main API services
start_api() {
    echo "🚀 Starting main API services..."
    docker-compose -f "$MAIN_COMPOSE" up -d
    echo "✅ API services started"
}

# Function to start nginx
start_nginx() {
    echo "🔧 Starting nginx reverse proxy..."
    docker-compose -f "$NGINX_COMPOSE" up -d
    echo "✅ Nginx started"
}

# Function to start everything
start_all() {
    create_network
    start_api
    start_nginx
    echo ""
    echo "🎉 All services started!"
    echo "📍 API available at: https://server.epicrunze.com"
    echo "📍 Direct API (if needed): http://localhost (through nginx only)"
    echo "📍 Health check: https://server.epicrunze.com/health"
}

# Function to stop services
stop_all() {
    echo "🛑 Stopping all services..."
    docker-compose -f "$NGINX_COMPOSE" down
    docker-compose -f "$MAIN_COMPOSE" down
    echo "✅ All services stopped"
}

# Function to show logs
show_logs() {
    local service=$1
    if [ "$service" = "nginx" ]; then
        docker-compose -f "$NGINX_COMPOSE" logs -f
    elif [ "$service" = "api" ]; then
        docker-compose -f "$MAIN_COMPOSE" logs -f
    else
        echo "📋 Main API Services Logs:"
        docker-compose -f "$MAIN_COMPOSE" logs --tail=50
        echo ""
        echo "📋 Nginx Logs:"
        docker-compose -f "$NGINX_COMPOSE" logs --tail=50
    fi
}

# Function to show status
show_status() {
    echo "🔍 Service Status:"
    echo ""
    echo "📊 Main API Services:"
    docker-compose -f "$MAIN_COMPOSE" ps
    echo ""
    echo "📊 Nginx Service:"
    docker-compose -f "$NGINX_COMPOSE" ps
    echo ""
    echo "🌐 Network Status:"
    docker network inspect "$NETWORK_NAME" --format='{{.Name}}: {{len .Containers}} containers connected' 2>/dev/null || echo "❌ Network not found"
}

# Function to rebuild services
rebuild() {
    local target=$1
    echo "🔨 Rebuilding services..."
    stop_all
    
    if [ "$target" = "nginx" ]; then
        docker-compose -f "$NGINX_COMPOSE" build --no-cache
    elif [ "$target" = "api" ]; then
        docker-compose -f "$MAIN_COMPOSE" build --no-cache
    else
        docker-compose -f "$MAIN_COMPOSE" build --no-cache
        docker-compose -f "$NGINX_COMPOSE" build --no-cache
    fi
    
    start_all
}

# Function to clean up
cleanup() {
    echo "🧹 Cleaning up..."
    stop_all
    docker-compose -f "$MAIN_COMPOSE" down -v --remove-orphans
    docker-compose -f "$NGINX_COMPOSE" down -v --remove-orphans
    
    read -p "Remove external network? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker network remove "$NETWORK_NAME" 2>/dev/null || echo "Network already removed or doesn't exist"
    fi
    
    echo "✅ Cleanup complete"
}

# Main menu
case "${1:-menu}" in
    "network")
        create_network
        ;;
    "start")
        start_all
        ;;
    "start-api")
        create_network
        start_api
        ;;
    "start-nginx")
        create_network
        start_nginx
        ;;
    "stop")
        stop_all
        ;;
    "logs")
        show_logs "${2:-all}"
        ;;
    "status")
        show_status
        ;;
    "rebuild")
        rebuild "${2:-all}"
        ;;
    "cleanup")
        cleanup
        ;;
    "menu"|*)
        echo "Usage: $0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  network      Create the external Docker network"
        echo "  start        Start all services (API + Nginx)"
        echo "  start-api    Start only the main API services"
        echo "  start-nginx  Start only the nginx reverse proxy"
        echo "  stop         Stop all services"
        echo "  logs [service]  Show logs (service: api, nginx, or all)"
        echo "  status       Show status of all services"
        echo "  rebuild [target]  Rebuild and restart (target: api, nginx, or all)"
        echo "  cleanup      Stop services and clean up volumes/networks"
        echo ""
        echo "Examples:"
        echo "  $0 start           # Start everything"
        echo "  $0 start-api       # Start only API services"
        echo "  $0 logs nginx      # Show nginx logs"
        echo "  $0 rebuild api     # Rebuild only API services"
        ;;
esac 