# Hardcoded Values to Convert to Environment Variables

This document tracks all hardcoded configuration values that should be converted to environment variables for production deployment.

## Database Configuration
**Location**: `gm_app/settings.py:94-98`
```python
"NAME": os.environ.get("DB_NAME", "gm_app_db"),  # Default value hardcoded
"USER": os.environ.get("DB_USER", "postgres"),   # Default value hardcoded
"PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),  # Default value hardcoded
"HOST": os.environ.get("DB_HOST", "localhost"),  # Default value hardcoded
"PORT": os.environ.get("DB_PORT", "5432"),      # Default value hardcoded
```

## CORS Configuration
**Location**: `gm_app/settings.py:275-277`
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React development server - hardcoded
]
```

## CSRF Trusted Origins
**Location**: `gm_app/settings.py:282-284`
```python
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",  # Hardcoded
]
```

## Redis Configuration
**Location**: `gm_app/settings.py:192`
```python
"LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),  # Default hardcoded
```

## Channel Layers Redis Configuration
**Location**: `gm_app/settings.py:206-209`
```python
"hosts": [
    (
        os.environ.get("REDIS_HOST", "127.0.0.1"),  # Default hardcoded
        int(os.environ.get("REDIS_PORT", 6379)),    # Default hardcoded
    )
],
```

## Debug Mode
**Location**: `gm_app/settings.py:28`
```python
DEBUG = True  # Should be environment-based for production
```

## Allowed Hosts
**Location**: `gm_app/settings.py:30`
```python
ALLOWED_HOSTS = []  # Should include production domains
```

## Secret Key
**Location**: `gm_app/settings.py:16`
```python
from .secrets import SECRET_KEY  # Currently in separate file, should be env var
```

## Frontend API Base URL
**Location**: `frontend/src/services/api.ts:5`
```typescript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080/api';
// Default hardcoded to localhost:8080
```

## React Bundle URL in Django Template
**Location**: `templates/base.html:57-59`
```html
{% if debug %}
    <script src="http://localhost:3000/static/js/bundle.js"></script>
{% endif %}
```

## Makefile Paths
**Location**: `Makefile:4-6`
```makefile
GMA_ENV_PATH = /home/janothar/miniconda3/envs/gma  # Hardcoded path
PG_BIN = $(GMA_ENV_PATH)/bin
PG_DATA = $(GMA_ENV_PATH)/var/postgres
```

## Frontend Package.json Proxy
**Location**: `frontend/package.json` (if exists)
```json
"proxy": "http://localhost:8080"  # If present
```

## TODO for Production Deployment

1. Create `.env.example` file with all required environment variables
2. Use `python-decouple` or `django-environ` for environment variable management
3. Create separate settings files for development/staging/production
4. Implement proper secret management (AWS Secrets Manager, HashiCorp Vault, etc.)
5. Use environment-specific Docker compose files
6. Configure CI/CD pipeline to inject environment variables

## Notes

- Keep development defaults for local development convenience
- Ensure all production values are properly secured
- Document all required environment variables in deployment documentation
- Consider using a configuration management system for complex deployments
