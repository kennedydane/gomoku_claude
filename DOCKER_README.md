# Gomoku Docker Setup Guide

This document provides comprehensive information about the Docker Compose configuration for the Gomoku game project.

## Quick Start

### Development Environment

1. **Initial Setup**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit .env with your preferred settings
   vim .env
   
   # Start development environment
   ./docker-manager.sh dev-start
   ```

2. **Access Services**
   - **Backend API**: http://localhost:8000
   - **pgAdmin**: http://localhost:5050
   - **PostgreSQL**: localhost:5432

### Production Environment

1. **Setup**
   ```bash
   # Copy production environment template
   cp .env.prod.example .env.prod
   
   # Edit with production values
   vim .env.prod
   
   # Start production environment
   ./docker-manager.sh prod-start
   ```

## Architecture Overview

### Services

#### PostgreSQL Database (`postgres`)
- **Image**: `postgres:16-alpine`
- **Purpose**: Primary database for the Gomoku application
- **Security Features**:
  - SCRAM-SHA-256 authentication
  - Non-root user execution
  - Resource limits applied
  - Port exposure controlled by environment

#### pgAdmin (`pgladmin`)
- **Image**: `dpage/pgladmin4:8`
- **Purpose**: Web-based PostgreSQL administration
- **Availability**: Development and admin profiles only
- **Pre-configured**: Automatically connects to Gomoku database

#### Backend API (`backend` / `backend-dev`)
- **Purpose**: FastAPI application server
- **Variants**:
  - `backend`: Production build with security hardening
  - `backend-dev`: Development build with hot-reload

### Networks

#### Backend Network (`gomoku_backend`)
- **Type**: Internal bridge network
- **Purpose**: Database and API communication
- **Security**: No external access
- **Subnet**: 172.20.1.0/24

#### Frontend Network (`gomoku_frontend`)
- **Type**: Bridge network  
- **Purpose**: API and future frontend communication
- **Subnet**: 172.20.2.0/24

### Volumes

#### Persistent Volumes
- `postgres_data`: Database files
- `pgladmin_data`: pgAdmin configuration and logs

#### Development Volumes
- `backend_dev_cache`: MyPy cache for development
- `backend_static`: Static files served by the API

## Security Features

### Environment Variables
- All sensitive data moved to environment variables
- Separate `.env` files for development and production
- No hardcoded credentials in docker-compose.yml

### Container Security
- Non-root users in all containers
- Read-only root filesystem for production backend
- Security options: `no-new-privileges`
- Resource limits prevent resource exhaustion
- Minimal base images (Alpine/Slim)

### Network Security
- Internal networks for service-to-service communication
- PostgreSQL port exposure controlled by environment
- pgAdmin only available in development profile

### Data Security
- Volume mounts use read-only flags where appropriate
- Temporary filesystems for sensitive temporary data
- Proper file permissions and ownership

## Development vs Production

### Development Features
- Hot-reload enabled for backend
- All debugging tools available
- PostgreSQL port exposed for external tools
- pgAdmin available for database management
- Generous resource limits
- Debug logging enabled

### Production Features
- Multi-worker uvicorn setup
- Read-only root filesystem
- No unnecessary port exposure
- Optimized resource limits
- Production logging levels
- Security hardening enabled

## Management Commands

The `docker-manager.sh` script provides convenient commands:

```bash
# Start development environment
./docker-manager.sh dev-start

# Start production environment  
./docker-manager.sh prod-start

# Show service status
./docker-manager.sh status

# View logs
./docker-manager.sh logs [service]

# Open shell in service
./docker-manager.sh shell <service>

# Database operations
./docker-manager.sh migrate  # Run migrations
./docker-manager.sh backup   # Create database backup

# Cleanup
./docker-manager.sh cleanup  # Remove everything
```

## Environment Configuration

### Development (.env)
```env
COMPOSE_PROFILES=development
POSTGRES_PASSWORD=dev_password
PGADMIN_DEFAULT_PASSWORD=admin_password
SECRET_KEY=dev-secret-key
DEBUG=true
```

### Production (.env.prod)
```env
COMPOSE_PROFILES=production
POSTGRES_PASSWORD=secure_production_password
SECRET_KEY=production_secret_key_32_chars
DEBUG=false
# Note: POSTGRES_PORT not set (no exposure)
```

## Health Checks

All services include comprehensive health checks:

- **PostgreSQL**: `pg_isready` command
- **Backend**: HTTP health endpoint check
- **Configurable**: Intervals, timeouts, retries, and start periods

## Resource Management

### PostgreSQL
- Memory: 256MB reserved, 512MB limit
- CPU: 0.25 reserved, 0.5 limit

### Backend Production
- Memory: 512MB reserved, 1GB limit  
- CPU: 0.5 reserved, 1.0 limit

### Backend Development
- Memory: Unlimited (for development tools)
- CPU: 2.0 limit

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check what's using the port
   lsof -i :8000
   
   # Change port in .env
   API_PORT=8001
   ```

2. **Permission Issues**
   ```bash
   # Fix volume permissions
   sudo chown -R $USER:$USER data/
   ```

3. **Database Connection Issues**
   ```bash
   # Check database logs
   ./docker-manager.sh logs postgres
   
   # Verify network connectivity
   docker-compose exec backend-dev ping postgres
   ```

4. **Memory Issues**
   ```bash
   # Check resource usage
   ./docker-manager.sh status
   
   # Adjust limits in docker-compose.yml
   ```

### Log Locations

- **Application Logs**: `./backend/logs/`
- **Container Logs**: `docker-compose logs [service]`
- **System Logs**: `/var/log/` (inside containers)

## Best Practices

### Development
- Use volume mounts for hot-reloading
- Enable debug logging
- Use separate development database
- Keep containers running for faster iteration

### Production
- Use specific image tags (not `latest`)
- Implement proper secrets management
- Monitor resource usage
- Regular security updates
- Use external database for scalability

### Security
- Regular credential rotation
- Keep images updated
- Use least-privilege principles
- Monitor for vulnerabilities
- Implement proper logging and monitoring

## Migration from Original Setup

If upgrading from the original configuration:

1. **Backup Data**
   ```bash
   ./docker-manager.sh backup
   ```

2. **Update Environment**
   ```bash
   cp .env.example .env
   # Edit with your current values
   ```

3. **Test New Configuration**
   ```bash
   ./docker-manager.sh dev-start
   ```

4. **Verify Services**
   ```bash
   ./docker-manager.sh status
   curl http://localhost:8000/health
   ```

## Future Enhancements

Planned improvements:
- Integration with container orchestration (Kubernetes)
- Enhanced monitoring and observability
- Automated backup strategies
- CI/CD pipeline integration
- Load balancing for multiple backend instances

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review container logs: `./docker-manager.sh logs`
3. Verify environment configuration
4. Check resource usage: `./docker-manager.sh status`