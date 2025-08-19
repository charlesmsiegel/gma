#!/usr/bin/env python3
"""
Test API keys and endpoints for code quality services.

This script tests the API keys and endpoints for Codacy, SonarQube, and DeepSource
to help troubleshoot connection issues.

Usage:
    python scripts/test_api_keys.py
"""

import os
import sys

import requests


def test_codacy_api():
    """Test Codacy API connection."""
    print("\n🔍 Testing Codacy API...")

    # Try to get API key
    try:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, current_dir)
        import gm_app.secrets as secrets

        api_key = getattr(secrets, "CODACY_API_KEY", None)
    except ImportError:
        api_key = os.environ.get("CODACY_API_KEY")

    if not api_key:
        print("❌ No Codacy API key found")
        return False

    print(f"✓ API key found: {api_key[:10]}...")

    # Test different endpoints and auth methods
    username = "charlesmsiegel"
    project = "gma"

    session = requests.Session()

    # Test 1: Bearer token authentication
    print("  Testing Bearer token authentication...")
    session.headers.update(
        {"Accept": "application/json", "Authorization": f"Bearer {api_key}"}
    )

    url = f"https://app.codacy.com/api/v3/organizations/gh/{username}/repositories/{project}"
    try:
        response = session.get(url)
        print(f"    GET {url}")
        print(f"    Status: {response.status_code}")
        if response.status_code == 200:
            print("    ✓ Bearer auth works!")
            return True
        elif response.status_code == 401:
            print("    ❌ Bearer auth failed (401 Unauthorized)")
        else:
            print(f"    Response: {response.text[:200]}...")
    except Exception as e:
        print(f"    Exception: {e}")

    # Test 2: api-token header authentication
    print("  Testing api-token header authentication...")
    session.headers.update(
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "api-token": api_key,
        }
    )
    session.headers.pop("Authorization", None)

    try:
        response = session.get(url)
        print(f"    GET {url}")
        print(f"    Status: {response.status_code}")
        if response.status_code == 200:
            print("    ✓ api-token header works!")
            return True
        elif response.status_code == 401:
            print("    ❌ api-token auth failed (401 Unauthorized)")
        else:
            print(f"    Response: {response.text[:200]}...")
    except Exception as e:
        print(f"    Exception: {e}")

    # Test 3: Try issues search endpoint
    print("  Testing issues search endpoint...")
    search_url = f"https://app.codacy.com/api/v3/analysis/organizations/gh/{username}/repositories/{project}/issues/search"
    try:
        response = session.post(search_url, json={"levels": ["Error"], "limit": 1})
        print(f"    POST {search_url}")
        print(f"    Status: {response.status_code}")
        if response.status_code == 200:
            print("    ✓ Issues search works!")
            return True
        else:
            print(f"    Response: {response.text[:200]}...")
    except Exception as e:
        print(f"    Exception: {e}")

    return False


def test_sonarqube_api():
    """Test SonarQube/SonarCloud API connection."""
    print("\n🔍 Testing SonarCloud API...")

    # Try to get API token
    try:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, current_dir)
        import gm_app.secrets as secrets

        token = getattr(secrets, "SONARQUBE_TOKEN", None)
    except:
        token = os.environ.get("SONARQUBE_TOKEN")

    if not token:
        print("❌ No SonarCloud token found")
        return False

    print(f"✓ Token found: {token[:10]}...")

    # Test the API
    session = requests.Session()
    session.auth = (token, "")
    session.headers.update({"Accept": "application/json"})

    project_key = "charlesmsiegel_gma"
    url = f"https://sonarcloud.io/api/issues/search"

    try:
        response = session.get(
            url,
            params={
                "componentKeys": project_key,
                "ps": 1,  # Just get 1 issue for testing
                "resolved": "false",
            },
        )
        print(f"  GET {url}")
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            issue_count = data.get("paging", {}).get("total", 0)
            print(f"  ✓ SonarCloud API works! Found {issue_count} issues")
            return True
        elif response.status_code == 401:
            print("  ❌ Authentication failed (401 Unauthorized)")
        elif response.status_code == 403:
            print("  ❌ Permission denied (403 Forbidden)")
        else:
            print(f"  Response: {response.text[:200]}...")

    except Exception as e:
        print(f"  Exception: {e}")

    return False


def test_deepsource_api():
    """Test DeepSource API connection."""
    print("\n🔍 Testing DeepSource API...")

    # Try to get API token
    try:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, current_dir)
        import gm_app.secrets as secrets

        token = getattr(secrets, "DEEPSOURCE_TOKEN", None)
    except:
        token = os.environ.get("DEEPSOURCE_TOKEN")

    if not token:
        print("❌ No DeepSource token found")
        return False

    print(f"✓ Token found: {token[:10]}...")

    # Test the API
    session = requests.Session()
    session.headers.update(
        {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    )

    username = "charlesmsiegel"
    project = "gma"
    url = f"https://api.deepsource.io/v1/repos/{username}/{project}/"

    try:
        response = session.get(url)
        print(f"  GET {url}")
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            print("  ✓ DeepSource API works!")
            return True
        elif response.status_code == 401:
            print("  ❌ Authentication failed (401 Unauthorized)")
        elif response.status_code == 404:
            print("  ❌ Repository not found (404) - may not be set up in DeepSource")
        else:
            print(f"  Response: {response.text[:200]}...")

    except Exception as e:
        print(f"  Exception: {e}")

    return False


def main():
    """Test all API integrations."""
    print("🚀 Testing Code Quality Service APIs")
    print("=" * 50)

    results = {
        "codacy": test_codacy_api(),
        "sonarcloud": test_sonarqube_api(),
        "deepsource": test_deepsource_api(),
    }

    print("\n📊 Summary:")
    print("=" * 20)

    for service, success in results.items():
        status = "✓ Working" if success else "❌ Failed"
        print(f"{service.capitalize()}: {status}")

    if not any(results.values()):
        print(f"\n💡 No services are working. Please check:")
        print("1. API keys are correctly configured in gm_app/secrets.py")
        print("2. Repository is properly set up in each service")
        print("3. API tokens have the correct permissions")

        print(f"\n📝 How to get API keys:")
        print("• Codacy: https://app.codacy.com/ → Organization Settings → API Tokens")
        print(
            "• SonarCloud: https://sonarcloud.io/ → My Account → Security → Generate Token"
        )
        print("• DeepSource: https://deepsource.io/ → Account Settings → API Tokens")


if __name__ == "__main__":
    main()
