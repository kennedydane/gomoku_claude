#!/bin/bash

# Gomoku Docker Management Script
# This script helps manage the Docker Compose environment for different scenarios

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from .env.example..."
        cp .env.example .env
        print_info "Please edit .env file with your actual values before continuing."
        exit 1
    fi
}

# Function to create required directories
create_directories() {
    print_info "Creating required directories..."
    mkdir -p data/postgres data/pgadmin backend/logs
    chmod 755 data/postgres data/pgadmin backend/logs
    print_success "Directories created successfully."
}

# Function to start development environment
dev_start() {
    print_info "Starting development environment..."
    check_env_file
    create_directories
    
    export COMPOSE_PROFILES=development
    docker-compose up -d postgres pgadmin backend-dev
    
    print_success "Development environment started!"
    print_info "Services available at:"
    echo "  - Backend API: http://localhost:8000"
    echo "  - pgAdmin: http://localhost:5050"
    echo "  - PostgreSQL: localhost:5432"
}

# Function to start production environment
prod_start() {
    print_info "Starting production environment..."
    
    if [ ! -f .env.prod ]; then
        print_error ".env.prod file not found. Please create it from .env.prod.example"
        exit 1
    fi
    
    create_directories
    
    export COMPOSE_FILE=docker-compose.yml
    docker-compose --env-file .env.prod up -d postgres backend
    
    print_success "Production environment started!"
    print_info "Services available at:"
    echo "  - Backend API: http://localhost:8000"
    print_warning "PostgreSQL port is not exposed in production mode."
}

# Function to stop all services
stop_all() {
    print_info "Stopping all services..."
    docker-compose down
    print_success "All services stopped."
}

# Function to clean up everything
cleanup() {
    print_warning "This will remove all containers, networks, and volumes!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v --remove-orphans
        docker system prune -f
        print_success "Cleanup completed."
    else
        print_info "Cleanup cancelled."
    fi
}

# Function to show logs
show_logs() {
    service=${1:-}
    if [ -z "$service" ]; then
        print_info "Showing logs for all services..."
        docker-compose logs -f
    else
        print_info "Showing logs for $service..."
        docker-compose logs -f "$service"
    fi
}

# Function to show status
show_status() {
    print_info "Docker Compose Status:"
    docker-compose ps
    echo
    print_info "Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# Function to run database migrations
run_migrations() {
    print_info "Running database migrations..."
    docker-compose exec backend-dev alembic upgrade head
    print_success "Migrations completed."
}

# Function to backup database
backup_database() {
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_file="backup_gomoku_${timestamp}.sql"
    
    print_info "Creating database backup: $backup_file"
    docker-compose exec postgres pg_dump -U gomoku_user gomoku_db > "$backup_file"
    print_success "Database backup created: $backup_file"
}

# Function to show help
show_help() {
    echo "Gomoku Docker Management Script"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  dev-start     Start development environment (default)"
    echo "  prod-start    Start production environment"
    echo "  stop          Stop all services"
    echo "  restart       Restart all services"
    echo "  status        Show service status and resource usage"
    echo "  logs [service] Show logs for all services or specific service"
    echo "  shell <service> Open shell in service container"
    echo "  migrate       Run database migrations"
    echo "  backup        Create database backup"
    echo "  cleanup       Remove all containers, networks, and volumes"
    echo "  help          Show this help message"
    echo
    echo "Examples:"
    echo "  $0                    # Start development environment"
    echo "  $0 logs postgres      # Show PostgreSQL logs"
    echo "  $0 shell backend-dev  # Open shell in development backend"
}

# Main script logic
case "${1:-dev-start}" in
    "dev-start"|"dev"|"development")
        dev_start
        ;;
    "prod-start"|"prod"|"production")
        prod_start
        ;;
    "stop")
        stop_all
        ;;
    "restart")
        stop_all
        sleep 2
        dev_start
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs "$2"
        ;;
    "shell")
        if [ -z "$2" ]; then
            print_error "Please specify a service name"
            exit 1
        fi
        docker-compose exec "$2" /bin/sh
        ;;
    "migrate")
        run_migrations
        ;;
    "backup")
        backup_database
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac