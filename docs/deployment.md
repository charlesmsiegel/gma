# GMA Deployment Guide

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Environment Configuration](#environment-configuration)
3. [Production Settings](#production-settings)
4. [Database Setup](#database-setup)
5. [Static Files and Media](#static-files-and-media)
6. [Security Configuration](#security-configuration)
7. [Container Deployment](#container-deployment)
8. [Cloud Platform Deployment](#cloud-platform-deployment)
9. [Monitoring and Logging](#monitoring-and-logging)
10. [Backup and Recovery](#backup-and-recovery)
11. [Performance Optimization](#performance-optimization)
12. [Troubleshooting](#troubleshooting)

## Deployment Overview

The GMA application supports multiple deployment strategies:

- **Traditional Server**: Direct deployment on VPS/dedicated servers
- **Container Deployment**: Docker containers with orchestration
- **Cloud Platforms**: AWS, Google Cloud, Azure, Heroku
- **Hybrid Deployment**: Database in cloud, application on-premise

### System Requirements

**Minimum Production Requirements:**
- **CPU**: 2 cores (4 recommended)
- **RAM**: 2GB (4GB recommended)
- **Storage**: 20GB (SSD recommended)
- **Python**: 3.11+
- **PostgreSQL**: 14+ (16 recommended)
- **Redis**: 6.0+ (7.2 recommended)
- **Node.js**: 18+ (for build process)

**Recommended Production Specifications:**
- **CPU**: 4-8 cores
- **RAM**: 8-16GB
- **Storage**: 100GB+ SSD
- **Network**: 1Gbps+
- **Load Balancer**: nginx or cloud load balancer

## Environment Configuration

### Environment Variables

Create comprehensive environment configuration for production:

```bash
# .env.production
# =================

# Django Core Settings
SECRET_KEY=your-secret-key-here-64-characters-minimum
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,your-server-ip

# Database Configuration
DATABASE_URL=postgresql://username:password@db-host:5432/gma_production
DB_NAME=gma_production
DB_USER=gma_user
DB_PASSWORD=secure-database-password
DB_HOST=localhost
DB_PORT=5432

# Redis Configuration
REDIS_URL=redis://redis-host:6379/0
REDIS_HOST=redis-host
REDIS_PORT=6379
REDIS_PASSWORD=redis-password

# Security Settings
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
SECURE_SSL_REDIRECT=True
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yourmailprovider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-smtp-user
EMAIL_HOST_PASSWORD=your-smtp-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Static Files
STATIC_ROOT=/var/www/gma/static
MEDIA_ROOT=/var/www/gma/media
STATIC_URL=/static/
MEDIA_URL=/media/

# CDN Configuration (Optional)
CDN_URL=https://cdn.yourdomain.com
AWS_STORAGE_BUCKET_NAME=your-s3-bucket
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret

# Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
ENABLE_DEBUG_TOOLBAR=False

# Performance
CONN_MAX_AGE=600
DATABASE_CONN_POOL_SIZE=20
```

### Configuration Management

Use `python-decouple` for environment management:

```python
# settings/production.py
from decouple import config, Csv
from .base import *

# Security
DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# Database with connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', cast=int),
        'OPTIONS': {
            'MAX_CONNS': config('DATABASE_CONN_POOL_SIZE', default=20, cast=int),
        },
        'CONN_MAX_AGE': config('CONN_MAX_AGE', default=600, cast=int),
    }
}
```

## Production Settings

### Security Settings

```python
# settings/production.py

# Security middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static file serving
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# SSL and HTTPS
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Session security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# CSRF security
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv())

# CORS settings
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# Content Security Policy
CSP_DEFAULT_SRC = ["'self'"]
CSP_SCRIPT_SRC = ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net"]
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'", "fonts.googleapis.com"]
CSP_FONT_SRC = ["'self'", "fonts.gstatic.com"]
```

### Caching Configuration

```python
# Redis caching for production
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True,
            },
        },
        'TIMEOUT': 3600,  # 1 hour default
    }
}

# Session backend
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

### Logging Configuration

```python
# Production logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "{levelname}", "time": "{asctime}", "module": "{module}", "message": "{message}"}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/gma/django.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/gma/django_error.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'campaigns': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'api': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Database Setup

### PostgreSQL Configuration

```sql
-- Create production database and user
CREATE USER gma_user WITH PASSWORD 'secure-password';
CREATE DATABASE gma_production OWNER gma_user;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE gma_production TO gma_user;

-- Performance tuning (adjust based on server specs)
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Reload configuration
SELECT pg_reload_conf();
```

### Database Migration

```bash
# Production migration process
python manage.py collectstatic --noinput
python manage.py migrate --settings=gm_app.settings.production

# Create superuser
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@yourdomain.com', 'secure-password')" | python manage.py shell --settings=gm_app.settings.production
```

### Database Backup

```bash
#!/bin/bash
# backup_db.sh - Daily database backup script

BACKUP_DIR="/var/backups/gma"
DATE=$(date +"%Y%m%d_%H%M%S")
DB_NAME="gma_production"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create backup
pg_dump $DB_NAME | gzip > "$BACKUP_DIR/gma_backup_$DATE.sql.gz"

# Clean up old backups (keep 30 days)
find $BACKUP_DIR -name "gma_backup_*.sql.gz" -mtime +30 -delete

# Upload to cloud storage (optional)
# aws s3 cp "$BACKUP_DIR/gma_backup_$DATE.sql.gz" s3://your-backup-bucket/database/
```

## Static Files and Media

### WhiteNoise Configuration

```python
# settings/production.py
# Static files with WhiteNoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Compression
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
```

### CDN Configuration (AWS S3)

```python
# settings/production.py - S3 Configuration
if config('USE_S3', default=False, cast=bool):
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')

    # Static files
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
    STATIC_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/static/'

    # Media files
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/media/'
```

### Build Process

```bash
#!/bin/bash
# build.sh - Production build script

echo "Building React frontend..."
cd frontend
npm ci --only=production
npm run build:django

echo "Collecting Django static files..."
cd ..
python manage.py collectstatic --noinput --settings=gm_app.settings.production

echo "Build complete!"
```

## Security Configuration

### Rate Limiting

```bash
# Install django-ratelimit
pip install django-ratelimit
```

```python
# Add to API views
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

@method_decorator(ratelimit(key='ip', rate='100/h', method='POST'), name='post')
class LoginAPIView(generics.GenericAPIView):
    # Login view implementation
    pass

@method_decorator(ratelimit(key='user', rate='1000/h', method='GET'), name='get')
class CampaignListAPIView(generics.ListAPIView):
    # Campaign list implementation
    pass
```

### Security Headers (nginx)

```nginx
# /etc/nginx/sites-available/gma
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'";

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;

    # Static files
    location /static/ {
        alias /var/www/gma/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/gma/media/;
        expires 1h;
    }

    # API rate limiting
    location /api/auth/login/ {
        limit_req zone=login burst=3 nodelay;
        proxy_pass http://127.0.0.1:8080;
        include proxy_params;
    }

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8080;
        include proxy_params;
    }

    # Main application
    location / {
        proxy_pass http://127.0.0.1:8080;
        include proxy_params;
    }
}
```

## Container Deployment

### Dockerfile

```dockerfile
# Multi-stage Dockerfile for production
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production
COPY frontend/ ./
RUN npm run build:django

# Python base image
FROM python:3.11-slim AS backend-builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production image
FROM python:3.11-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN adduser --disabled-password --gecos '' gmauser

WORKDIR /app

# Copy Python dependencies
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=gmauser:gmauser . .

# Copy built frontend
COPY --from=frontend-builder --chown=gmauser:gmauser /app/frontend/build ./static/

# Set permissions
RUN chown -R gmauser:gmauser /app

USER gmauser

# Collect static files
RUN python manage.py collectstatic --noinput --settings=gm_app.settings.production

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "gm_app.wsgi:application"]
```

### Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: gma_production
      POSTGRES_USER: gma_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data/
      - ./backups:/backups
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    restart: unless-stopped

  web:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql://gma_user:${DB_PASSWORD}@db:5432/gma_production
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
      - static_files:/var/www/static
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  static_files:
```

### Deploy Script

```bash
#!/bin/bash
# deploy.sh - Production deployment script

set -e

echo "Starting deployment..."

# Pull latest code
git pull origin main

# Build and deploy containers
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate --settings=gm_app.settings.production

# Collect static files
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput --settings=gm_app.settings.production

# Health check
sleep 10
curl -f http://localhost:8080/health/ || exit 1

echo "Deployment complete!"
```

## Cloud Platform Deployment

### Heroku Deployment

```bash
# Procfile
web: gunicorn gm_app.wsgi:application --bind 0.0.0.0:$PORT
worker: python manage.py runworker
```

```python
# settings/heroku.py
import dj_database_url
from .production import *

# Database configuration
DATABASES['default'] = dj_database_url.config(conn_max_age=600)

# Redis configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('REDIS_URL')],
        },
    },
}

# Static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

```bash
# Heroku deployment commands
heroku create gma-production
heroku addons:create heroku-postgresql:standard-0
heroku addons:create heroku-redis:premium-0
heroku config:set SECRET_KEY=your-secret-key
heroku config:set DJANGO_SETTINGS_MODULE=gm_app.settings.heroku
git push heroku main
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
```

### AWS ECS Deployment

```json
{
  "family": "gma-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "gma-web",
      "image": "your-account.dkr.ecr.region.amazonaws.com/gma:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DJANGO_SETTINGS_MODULE",
          "value": "gm_app.settings.production"
        }
      ],
      "secrets": [
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:gma/secret-key"
        },
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:gma/database-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/gma",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## Monitoring and Logging

### Application Monitoring

```python
# settings/production.py - Sentry integration
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

sentry_sdk.init(
    dsn=config('SENTRY_DSN'),
    integrations=[
        DjangoIntegration(auto_enabling_instrumentation=False),
        RedisIntegration(),
    ],
    traces_sample_rate=0.1,
    send_default_pii=False,
    environment=config('ENVIRONMENT', default='production')
)
```

### Health Check Endpoint

```python
# core/views.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis

def health_check(request):
    """Comprehensive health check endpoint."""
    status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status['checks']['database'] = 'healthy'
    except Exception as e:
        status['checks']['database'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'

    # Redis check
    try:
        cache.set('health_check', 'ok', 30)
        cache.get('health_check')
        status['checks']['cache'] = 'healthy'
    except Exception as e:
        status['checks']['cache'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'

    return JsonResponse(status, status=200 if status['status'] == 'healthy' else 503)
```

### System Monitoring

```bash
# monitoring/system_check.sh
#!/bin/bash

# System metrics
echo "=== System Health Check ==="
date
echo

# CPU and Memory
echo "CPU Usage:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//'

echo "Memory Usage:"
free -m | awk 'NR==2{printf "Memory Usage: %s/%sMB (%.2f%%)\n", $3,$2,$3*100/$2 }'

echo "Disk Usage:"
df -h | grep -vE '^Filesystem|tmpfs|cdrom'

# Process check
echo "Django processes:"
ps aux | grep -E "(gunicorn|python.*manage.py)" | grep -v grep

# Network check
echo "Port check:"
netstat -tulpn | grep -E "(8080|5432|6379)"

# Log errors
echo "Recent errors:"
tail -n 20 /var/log/gma/django_error.log 2>/dev/null || echo "No error log found"
```

## Backup and Recovery

### Automated Backup System

```bash
#!/bin/bash
# backup_system.sh - Complete backup solution

BACKUP_DIR="/var/backups/gma"
DATE=$(date +"%Y%m%d_%H%M%S")
DB_NAME="gma_production"
MEDIA_DIR="/var/www/gma/media"

# Create backup directory
mkdir -p $BACKUP_DIR/{database,media,config}

echo "Starting backup process..."

# Database backup
echo "Backing up database..."
pg_dump $DB_NAME | gzip > "$BACKUP_DIR/database/gma_db_$DATE.sql.gz"

# Media files backup
echo "Backing up media files..."
tar -czf "$BACKUP_DIR/media/gma_media_$DATE.tar.gz" -C $MEDIA_DIR .

# Configuration backup
echo "Backing up configuration..."
cp /etc/nginx/sites-available/gma "$BACKUP_DIR/config/nginx_$DATE.conf"
cp .env.production "$BACKUP_DIR/config/env_$DATE"

# Create manifest
cat > "$BACKUP_DIR/manifest_$DATE.txt" << EOF
Backup Date: $(date)
Database: gma_db_$DATE.sql.gz
Media: gma_media_$DATE.tar.gz
Config: nginx_$DATE.conf, env_$DATE
EOF

# Upload to cloud storage
if [ "$UPLOAD_TO_S3" = "true" ]; then
    echo "Uploading to S3..."
    aws s3 sync $BACKUP_DIR s3://your-backup-bucket/gma-backups/
fi

# Clean old backups (keep 30 days locally, 90 days in cloud)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup complete!"
```

### Recovery Procedures

```bash
#!/bin/bash
# restore.sh - Database and media restoration

BACKUP_FILE=$1
MEDIA_BACKUP=$2

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <database_backup.sql.gz> [media_backup.tar.gz]"
    exit 1
fi

echo "Starting restoration process..."

# Stop application
docker-compose -f docker-compose.prod.yml stop web

# Restore database
echo "Restoring database..."
zcat $BACKUP_FILE | psql -U gma_user -d gma_production

# Restore media files
if [ -n "$MEDIA_BACKUP" ]; then
    echo "Restoring media files..."
    tar -xzf $MEDIA_BACKUP -C /var/www/gma/media/
fi

# Restart application
docker-compose -f docker-compose.prod.yml start web

echo "Restoration complete!"
```

## Performance Optimization

### Database Optimization

```python
# Database connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
        'OPTIONS': {
            'MAX_CONNS': 20,
        },
        'CONN_MAX_AGE': 600,
    }
}

# Query optimization
DATABASE_ROUTERS = ['path.to.ReadWriteRouter']  # Read replicas
```

### Caching Strategy

```python
# Multi-level caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_SESSION_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    }
}

# Template caching
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]
```

### Application Server Configuration

```python
# gunicorn_config.py
import multiprocessing

bind = "0.0.0.0:8080"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True
timeout = 60
keepalive = 2

# Logging
accesslog = "/var/log/gma/gunicorn_access.log"
errorlog = "/var/log/gma/gunicorn_error.log"
loglevel = "info"
```

## Troubleshooting

### Common Issues

#### Database Connection Issues

```bash
# Check database connectivity
pg_isready -h localhost -p 5432 -U gma_user

# Check active connections
psql -U gma_user -d gma_production -c "SELECT count(*) FROM pg_stat_activity;"

# Kill hanging connections
psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='gma_production' AND state='idle in transaction';"
```

#### Memory Issues

```bash
# Monitor memory usage
free -m
ps aux --sort=-%mem | head

# Check for memory leaks
valgrind --tool=memcheck python manage.py runserver
```

#### Performance Issues

```bash
# Enable query logging
tail -f /var/log/postgresql/postgresql.log | grep "SLOW QUERY"

# Monitor API response times
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8080/api/campaigns/"
```

#### SSL Certificate Issues

```bash
# Check certificate expiration
openssl x509 -in /path/to/certificate.crt -text -noout | grep "Not After"

# Test SSL configuration
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

### Log Analysis

```bash
# Real-time log monitoring
tail -f /var/log/gma/django.log

# Error pattern analysis
grep -i error /var/log/gma/django.log | tail -20

# Performance analysis
grep "took" /var/log/gma/django.log | awk '{print $NF}' | sort -n | tail -10
```

### Disaster Recovery Checklist

1. **Immediate Response**
   - Check system status and error logs
   - Verify database and cache connectivity
   - Confirm backup systems are functional

2. **Service Restoration**
   - Restore from latest backup if needed
   - Verify data integrity post-restoration
   - Test critical application functions

3. **Communication**
   - Notify stakeholders of issues and resolution
   - Document incident for post-mortem analysis
   - Update monitoring and alerting if needed

---

*This deployment guide should be customized based on your specific infrastructure requirements. Last updated: 2025-01-08*
