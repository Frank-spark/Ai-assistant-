#!/bin/bash

# Reflex Executive AI Assistant Deployment Script
# This script automates the Docker build and deployment process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="reflex-executive-assistant"
DOCKER_REGISTRY=""
IMAGE_TAG="latest"
ENVIRONMENT="development"

# Function to print colored output
print_status() {
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

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from example..."
        if [ -f env.example ]; then
            cp env.example .env
            print_warning "Please update .env file with your configuration before continuing."
            exit 1
        else
            print_error "env.example file not found. Please create a .env file with required environment variables."
            exit 1
        fi
    fi
    
    print_success "Prerequisites check completed."
}

# Function to build Docker images
build_images() {
    print_status "Building Docker images..."
    
    # Build the main application image
    docker build -t ${APP_NAME}:${IMAGE_TAG} .
    
    if [ $? -eq 0 ]; then
        print_success "Docker images built successfully."
    else
        print_error "Failed to build Docker images."
        exit 1
    fi
}

# Function to start services
start_services() {
    print_status "Starting services..."
    
    # Start all services using docker-compose
    docker-compose up -d
    
    if [ $? -eq 0 ]; then
        print_success "Services started successfully."
    else
        print_error "Failed to start services."
        exit 1
    fi
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."
    
    docker-compose down
    
    if [ $? -eq 0 ]; then
        print_success "Services stopped successfully."
    else
        print_error "Failed to stop services."
        exit 1
    fi
}

# Function to restart services
restart_services() {
    print_status "Restarting services..."
    
    docker-compose restart
    
    if [ $? -eq 0 ]; then
        print_success "Services restarted successfully."
    else
        print_error "Failed to restart services."
        exit 1
    fi
}

# Function to check service health
check_health() {
    print_status "Checking service health..."
    
    # Wait for services to be ready
    sleep 10
    
    # Check if the main application is responding
    if curl -f http://localhost:8080/health > /dev/null 2>&1; then
        print_success "Application is healthy and responding."
    else
        print_warning "Application health check failed. Services may still be starting up."
    fi
    
    # Check if Celery Flower is accessible
    if curl -f http://localhost:5555 > /dev/null 2>&1; then
        print_success "Celery Flower is accessible."
    else
        print_warning "Celery Flower is not accessible yet."
    fi
    
    # Check if Prometheus is accessible
    if curl -f http://localhost:9090 > /dev/null 2>&1; then
        print_success "Prometheus is accessible."
    else
        print_warning "Prometheus is not accessible yet."
    fi
    
    # Check if Grafana is accessible
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        print_success "Grafana is accessible."
    else
        print_warning "Grafana is not accessible yet."
    fi
}

# Function to show service status
show_status() {
    print_status "Service status:"
    docker-compose ps
    
    print_status "Service logs (last 10 lines):"
    docker-compose logs --tail=10
}

# Function to show service URLs
show_urls() {
    print_status "Service URLs:"
    echo "  Application:     http://localhost:8080"
    echo "  API Documentation: http://localhost:8080/docs"
    echo "  Celery Flower:   http://localhost:5555"
    echo "  Prometheus:      http://localhost:9090"
    echo "  Grafana:         http://localhost:3000 (admin/admin)"
    echo "  Health Check:    http://localhost:8080/health"
}

# Function to clean up
cleanup() {
    print_status "Cleaning up..."
    
    # Stop and remove containers
    docker-compose down -v
    
    # Remove images
    docker rmi ${APP_NAME}:${IMAGE_TAG} 2>/dev/null || true
    
    print_success "Cleanup completed."
}

# Function to show help
show_help() {
    echo "Reflex Executive AI Assistant Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build     - Build Docker images"
    echo "  start     - Start all services"
    echo "  stop      - Stop all services"
    echo "  restart   - Restart all services"
    echo "  status    - Show service status"
    echo "  health    - Check service health"
    echo "  urls      - Show service URLs"
    echo "  deploy    - Build and start services"
    echo "  cleanup   - Stop services and clean up"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 deploy    # Build and start all services"
    echo "  $0 status    # Show current service status"
    echo "  $0 health    # Check if services are healthy"
}

# Main script logic
case "${1:-help}" in
    "build")
        check_prerequisites
        build_images
        ;;
    "start")
        check_prerequisites
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        restart_services
        ;;
    "status")
        show_status
        ;;
    "health")
        check_health
        ;;
    "urls")
        show_urls
        ;;
    "deploy")
        check_prerequisites
        build_images
        start_services
        check_health
        show_urls
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|*)
        show_help
        ;;
esac 