"""
Configuration for code quality service integrations.

This file contains API keys and configuration for:
- Codacy
- SonarQube (SonarCloud)
- DeepSource

Copy this file to code_quality_config_local.py and add your actual API keys.
"""

# Codacy Configuration
CODACY_API_KEY = "your_codacy_api_key_here"
CODACY_USERNAME = "charlesmsiegel"
CODACY_PROJECT = "gma"

# SonarQube/SonarCloud Configuration
SONARQUBE_TOKEN = "your_sonarqube_token_here"
SONARQUBE_URL = "https://sonarcloud.io/api"
SONARQUBE_PROJECT_KEY = "charlesmsiegel_gma"

# DeepSource Configuration
DEEPSOURCE_TOKEN = "your_deepsource_token_here"
DEEPSOURCE_USERNAME = "charlesmsiegel"
DEEPSOURCE_PROJECT = "gma"

# How to get API keys:
#
# Codacy:
# 1. Go to https://app.codacy.com/
# 2. Navigate to Organization Settings > API Tokens
# 3. Create a new API token with "Read" permissions
#
# SonarCloud:
# 1. Go to https://sonarcloud.io/
# 2. Navigate to My Account > Security
# 3. Generate a new token
#
# DeepSource:
# 1. Go to https://deepsource.io/
# 2. Navigate to Account Settings > API Tokens
# 3. Create a new token with repository access
