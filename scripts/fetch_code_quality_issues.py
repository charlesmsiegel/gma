#!/usr/bin/env python3
"""
Fetch code quality issues from multiple services (Codacy, SonarQube, DeepSource).

This script fetches issues from various code quality services and generates
comprehensive reports for the project.

Usage:
    python scripts/fetch_code_quality_issues.py --service codacy
    python scripts/fetch_code_quality_issues.py --service sonarqube
    python scripts/fetch_code_quality_issues.py --service deepsource
    python scripts/fetch_code_quality_issues.py --all

Requirements:
    - API keys configured in gm_app/secrets.py
    - requests library
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

import requests


class CodeQualityFetcher:
    """Base class for code quality service integrations."""

    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.session = requests.Session()

    def fetch_issues(self) -> List[Dict[str, Any]]:
        """Fetch issues from the service. Override in subclasses."""
        raise NotImplementedError

    def format_issues(self, issues: List[Dict[str, Any]]) -> str:
        """Format issues for markdown output. Override in subclasses."""
        raise NotImplementedError


class CodacyFetcher(CodeQualityFetcher):
    """Fetcher for Codacy issues."""

    def __init__(self, config: Dict[str, str]):
        super().__init__(config)
        self.base_url = "https://app.codacy.com/api/v3"
        self.username = config.get("CODACY_USERNAME", "charlesmsiegel")
        self.project = config.get("CODACY_PROJECT", "gma")
        self.api_key = config.get("CODACY_API_KEY")

        if not self.api_key:
            raise ValueError("CODACY_API_KEY not found in configuration")

        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
        )

    def fetch_issues(self) -> List[Dict[str, Any]]:
        """Fetch issues from Codacy API."""
        issues = []

        print(f"Fetching Codacy issues for {self.username}/{self.project}...")

        # Use the correct POST endpoint for searching issues
        url = f"{self.base_url}/analysis/organizations/gh/{self.username}/repositories/{self.project}/issues/search"
        print(f"  Using endpoint: {url}")

        # Request body for searching issues
        request_body = {
            "levels": ["Error", "Warning", "Info"],  # All severity levels
            "limit": 500,  # Maximum results per request
        }

        try:
            response = self.session.post(url, json=request_body)
            response.raise_for_status()

            data = response.json()
            print(
                f"  API Response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}"
            )

            # Handle different response structures
            if isinstance(data, list):
                issues = data
            elif isinstance(data, dict):
                issues = data.get("data", data.get("issues", data.get("results", [])))
            else:
                issues = []

            print(f"  Success! Fetched {len(issues)} issues")

            # Handle pagination if present
            if isinstance(data, dict) and "pagination" in data:
                pagination = data["pagination"]
                next_cursor = None

                # Handle different cursor structures
                if isinstance(pagination, dict):
                    if "cursor" in pagination:
                        cursor_info = pagination["cursor"]
                        if isinstance(cursor_info, dict):
                            next_cursor = cursor_info.get("next")
                        else:
                            next_cursor = cursor_info
                    elif "next" in pagination:
                        next_cursor = pagination["next"]

                while next_cursor:
                    request_body["cursor"] = next_cursor

                    response = self.session.post(url, json=request_body)
                    response.raise_for_status()

                    data = response.json()
                    more_issues = data.get(
                        "data", data.get("issues", data.get("results", []))
                    )

                    if not more_issues:
                        break

                    issues.extend(more_issues)
                    print(f"  Fetched additional {len(more_issues)} issues")

                    pagination = data.get("pagination", {})
                    next_cursor = None

                    if isinstance(pagination, dict):
                        if "cursor" in pagination:
                            cursor_info = pagination["cursor"]
                            if isinstance(cursor_info, dict):
                                next_cursor = cursor_info.get("next")
                            else:
                                next_cursor = (
                                    cursor_info
                                    if cursor_info != request_body.get("cursor")
                                    else None
                                )
                        elif "next" in pagination:
                            next_cursor = pagination["next"]

        except requests.exceptions.RequestException as e:
            print(f"  Failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"  Response status: {e.response.status_code}")
                print(f"  Response: {e.response.text[:500]}...")

        print(f"Total Codacy issues fetched: {len(issues)}")
        return issues

    def format_issues(self, issues: List[Dict[str, Any]]) -> str:
        """Format Codacy issues for markdown output."""
        if not issues:
            return "No Codacy issues found.\n"

        # Group by severity
        severity_groups = {"Error": [], "Warning": [], "Info": []}

        for issue in issues:
            # Codacy uses patternInfo.level for severity
            severity = "Info"  # Default
            if "patternInfo" in issue and isinstance(issue["patternInfo"], dict):
                severity = issue["patternInfo"].get("level", "Info")

            if severity not in severity_groups:
                severity_groups[severity] = []
            severity_groups[severity].append(issue)

        # Group by category (using patternInfo.category)
        category_groups = {}
        for issue in issues:
            category = "Other"  # Default
            if "patternInfo" in issue and isinstance(issue["patternInfo"], dict):
                category = issue["patternInfo"].get("category", "Other")

            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(issue)

        output = [
            "# Codacy Code Quality Issues",
            "",
            f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Total Issues**: {len(issues)}",
            "",
            "## Issue Summary",
            "",
            "### By Severity",
        ]

        for severity, severity_issues in severity_groups.items():
            if severity_issues:
                output.append(f"- **{severity}**: {len(severity_issues)} issues")

        output.extend(["", "### By Category"])

        for category, category_issues in sorted(category_groups.items()):
            output.append(f"- **{category}**: {len(category_issues)} issues")

        output.extend(["", "## Detailed Issues", ""])

        # Output detailed issues by severity
        severity_icons = {"Error": "🔴", "Warning": "🟠", "Info": "🔵"}

        for severity in ["Error", "Warning", "Info"]:
            severity_issues = severity_groups[severity]
            if not severity_issues:
                continue

            icon = severity_icons.get(severity, "⚪")
            output.extend([f"### {icon} {severity} Level Issues", ""])

            for i, issue in enumerate(severity_issues, 1):
                # Extract fields according to Codacy API structure
                file_path = issue.get("filePath", "Unknown file")
                line_number = issue.get("lineNumber", "Unknown line")
                message = issue.get("message", "No message")

                # Tool info
                tool = "Unknown tool"
                if "toolInfo" in issue and isinstance(issue["toolInfo"], dict):
                    tool = issue["toolInfo"].get("name", "Unknown tool")

                # Category from pattern info
                category = "Unknown category"
                if "patternInfo" in issue and isinstance(issue["patternInfo"], dict):
                    category = issue["patternInfo"].get("category", "Unknown category")

                output.extend(
                    [
                        f"#### {i}. {message} ({file_path}:{line_number})",
                        f"- **Tool**: {tool}",
                        f"- **Category**: {category}",
                        f"- **File**: `{file_path}`",
                        f"- **Line**: {line_number}",
                        "",
                    ]
                )

        return "\n".join(output)


class SonarQubeFetcher(CodeQualityFetcher):
    """Fetcher for SonarQube issues."""

    def __init__(self, config: Dict[str, str]):
        super().__init__(config)
        self.base_url = config.get("SONARQUBE_URL", "https://sonarcloud.io/api")
        self.project_key = config.get("SONARQUBE_PROJECT_KEY", "charlesmsiegel_gma")
        self.token = config.get("SONARQUBE_TOKEN")

        if not self.token:
            raise ValueError("SONARQUBE_TOKEN not found in configuration")

        self.session.auth = (self.token, "")
        self.session.headers.update({"Accept": "application/json"})

    def fetch_issues(self) -> List[Dict[str, Any]]:
        """Fetch issues from SonarQube API."""
        issues = []
        page = 1
        page_size = 500

        print(f"Fetching SonarQube issues for project {self.project_key}...")

        while True:
            url = f"{self.base_url}/issues/search"
            params = {
                "componentKeys": self.project_key,
                "ps": page_size,  # Page size
                "p": page,  # Page number
                "resolved": "false",  # Only unresolved issues
            }

            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                page_issues = data.get("issues", [])

                if not page_issues:
                    break

                issues.extend(page_issues)
                print(f"  Fetched page {page}: {len(page_issues)} issues")

                # Check if there are more pages
                paging = data.get("paging", {})
                if page * page_size >= paging.get("total", 0):
                    break

                page += 1

            except requests.exceptions.RequestException as e:
                print(f"Error fetching SonarQube issues: {e}")
                if hasattr(e, "response") and e.response is not None:
                    print(f"Response: {e.response.text}")
                break

        print(f"Total SonarQube issues fetched: {len(issues)}")
        return issues

    def format_issues(self, issues: List[Dict[str, Any]]) -> str:
        """Format SonarQube issues for markdown output."""
        if not issues:
            return "No SonarQube issues found.\n"

        # Group by severity
        severity_groups = {
            "BLOCKER": [],
            "CRITICAL": [],
            "MAJOR": [],
            "MINOR": [],
            "INFO": [],
        }

        for issue in issues:
            severity = issue.get("severity", "INFO")
            if severity not in severity_groups:
                severity_groups[severity] = []
            severity_groups[severity].append(issue)

        # Group by type
        type_groups = {}
        for issue in issues:
            issue_type = issue.get("type", "OTHER")
            if issue_type not in type_groups:
                type_groups[issue_type] = []
            type_groups[issue_type].append(issue)

        output = [
            f"# SonarQube Code Quality Issues",
            "",
            f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Total Issues**: {len(issues)}",
            "",
            f"## Issue Summary",
            "",
            f"### By Severity",
        ]

        for severity, severity_issues in severity_groups.items():
            if severity_issues:
                output.append(f"- **{severity}**: {len(severity_issues)} issues")

        output.extend(["", f"### By Type"])

        for issue_type, type_issues in sorted(type_groups.items()):
            output.append(f"- **{issue_type}**: {len(type_issues)} issues")

        output.extend(["", f"## Detailed Issues", ""])

        # Output detailed issues by severity
        severity_icons = {
            "BLOCKER": "🚫",
            "CRITICAL": "🔴",
            "MAJOR": "🟠",
            "MINOR": "🟡",
            "INFO": "🔵",
        }

        for severity in ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"]:
            severity_issues = severity_groups[severity]
            if not severity_issues:
                continue

            icon = severity_icons.get(severity, "⚪")
            output.extend([f"### {icon} {severity} Level Issues", ""])

            for i, issue in enumerate(severity_issues, 1):
                component = issue.get("component", "").replace(
                    f"{self.project_key}:", ""
                )
                line = issue.get("line", "Unknown line")
                message = issue.get("message", "No message")
                rule = issue.get("rule", "Unknown rule")
                issue_type = issue.get("type", "Unknown type")

                output.extend(
                    [
                        f"#### {i}. {message}",
                        f"- **Rule**: {rule}",
                        f"- **Type**: {issue_type}",
                        f"- **File**: `{component}`",
                        f"- **Line**: {line}",
                        "",
                    ]
                )

        return "\n".join(output)


class DeepSourceFetcher(CodeQualityFetcher):
    """Fetcher for DeepSource issues using GraphQL API."""

    def __init__(self, config: Dict[str, str]):
        super().__init__(config)
        self.graphql_url = "https://api.deepsource.io/graphql/"
        self.username = config.get("DEEPSOURCE_USERNAME", "charlesmsiegel")
        self.project = config.get("DEEPSOURCE_PROJECT", "gma")
        self.token = config.get("DEEPSOURCE_TOKEN")

        if not self.token:
            raise ValueError("DEEPSOURCE_TOKEN not found in configuration")

        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "accept": "application/json",
                "content-type": "application/json",
            }
        )

    def fetch_issues(self) -> List[Dict[str, Any]]:
        """Fetch issues from DeepSource GraphQL API."""
        issues = []

        print(f"Fetching DeepSource issues for {self.username}/{self.project}...")

        # GraphQL query to get all issues (simplified based on available fields)
        query = {
            "query": """
            query($name: String!, $login: String!, $first: Int, $after: String) {
                repository(name: $name, login: $login, vcsProvider: GITHUB) {
                    name
                    issues(first: $first, after: $after) {
                        edges {
                            node {
                                issue {
                                    title
                                    description
                                    shortcode
                                }
                            }
                            cursor
                        }
                        totalCount
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                    }
                }
            }
            """,
            "variables": {
                "name": self.project,
                "login": self.username,
                "first": 100,  # Fetch 100 issues per request
                "after": None,
            },
        }

        try:
            # Fetch first page
            response = self.session.post(self.graphql_url, json=query)
            response.raise_for_status()

            data = response.json()

            if "errors" in data:
                print(f"GraphQL errors: {data['errors']}")
                return issues

            repository_data = data.get("data", {}).get("repository", {})
            issues_data = repository_data.get("issues", {})

            # Extract issues from first page
            edges = issues_data.get("edges", [])
            for edge in edges:
                issues.append(edge["node"])

            print(f"Fetched initial {len(edges)} issues")

            # Handle pagination
            page_info = issues_data.get("pageInfo", {})
            while page_info.get("hasNextPage", False):
                query["variables"]["after"] = page_info.get("endCursor")

                response = self.session.post(self.graphql_url, json=query)
                response.raise_for_status()

                data = response.json()

                if "errors" in data:
                    print(f"GraphQL errors on pagination: {data['errors']}")
                    break

                repository_data = data.get("data", {}).get("repository", {})
                issues_data = repository_data.get("issues", {})

                edges = issues_data.get("edges", [])
                for edge in edges:
                    issues.append(edge["node"])

                print(f"Fetched additional {len(edges)} issues")

                page_info = issues_data.get("pageInfo", {})

            total_count = issues_data.get("totalCount", len(issues))
            print(
                f"Total DeepSource issues fetched: {len(issues)} out of {total_count}"
            )

        except requests.exceptions.RequestException as e:
            print(f"Error fetching DeepSource issues: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"Response: {e.response.text}")

        return issues

    def format_issues(self, issues: List[Dict[str, Any]]) -> str:
        """Format DeepSource issues for markdown output."""
        if not issues:
            return "No DeepSource issues found.\n"

        # Group issues by shortcode/rule (since we don't have analyzer info in simplified query)
        rule_groups = {}
        for issue in issues:
            issue_data = issue.get("issue", {})
            shortcode = issue_data.get("shortcode", "Unknown")
            if shortcode not in rule_groups:
                rule_groups[shortcode] = []
            rule_groups[shortcode].append(issue)

        # Categorize issues based on shortcode patterns (best effort classification)
        type_groups = {
            "security": [],
            "bug": [],
            "style": [],
            "performance": [],
            "other": [],
        }

        for issue in issues:
            issue_data = issue.get("issue", {})
            shortcode = issue_data.get("shortcode", "").lower()
            title = issue_data.get("title", "").lower()

            # Simple classification based on common patterns
            if any(
                keyword in shortcode or keyword in title
                for keyword in ["security", "inject", "xss", "csrf", "auth"]
            ):
                type_groups["security"].append(issue)
            elif any(
                keyword in shortcode or keyword in title
                for keyword in ["bug", "error", "exception", "fail"]
            ):
                type_groups["bug"].append(issue)
            elif any(
                keyword in shortcode or keyword in title
                for keyword in ["style", "format", "lint", "import", "docstring"]
            ):
                type_groups["style"].append(issue)
            elif any(
                keyword in shortcode or keyword in title
                for keyword in ["performance", "slow", "inefficient", "loop"]
            ):
                type_groups["performance"].append(issue)
            else:
                type_groups["other"].append(issue)

        output = [
            f"# DeepSource Code Quality Issues",
            "",
            f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Total Issues**: {len(issues)}",
            "",
            f"## Issue Summary",
            "",
            f"### By Type",
        ]

        type_icons = {
            "security": "🔐",
            "bug": "🐛",
            "style": "🎨",
            "performance": "⚡",
            "other": "🔍",
        }

        for type_name, type_issues in type_groups.items():
            if type_issues:
                icon = type_icons.get(type_name, "⚪")
                output.append(
                    f"- {icon} **{type_name.title()}**: {len(type_issues)} issues"
                )

        output.extend(["", f"### By Rule"])

        for rule, rule_issues in sorted(rule_groups.items()):
            if len(rule_issues) > 1:
                output.append(f"- **{rule}**: {len(rule_issues)} occurrences")

        output.extend(["", f"## All Issues", ""])

        # Output all issues in order
        for i, issue in enumerate(issues, 1):
            issue_data = issue.get("issue", {})

            title = issue_data.get("title", "No title")
            description = issue_data.get("description", "No description")
            shortcode = issue_data.get("shortcode", "Unknown")

            # Clean up description (remove excessive whitespace and limit length)
            if description:
                description = " ".join(description.split())  # Normalize whitespace
                if len(description) > 300:
                    description = description[:300] + "..."

            output.extend(
                [
                    f"### {i}. {title}",
                    f"- **Rule**: `{shortcode}`",
                    f"- **Description**: {description}",
                    "",
                ]
            )

        return "\n".join(output)


def load_config() -> Dict[str, str]:
    """Load configuration from secrets.py."""
    config = {}

    # Add current directory to Python path for imports
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    # Try to import from Django settings
    try:
        # Set Django settings module
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gm_app.settings")

        import django

        # Try to configure Django
        try:
            django.setup()
        except Exception:
            # Django might already be configured
            pass

        # Import secrets from multiple sources
        try:
            import gm_app.secrets as secrets

            config.update(
                {
                    "CODACY_API_KEY": getattr(secrets, "CODACY_API_KEY", None),
                    "SONARQUBE_TOKEN": getattr(secrets, "SONARQUBE_TOKEN", None),
                    "DEEPSOURCE_TOKEN": getattr(secrets, "DEEPSOURCE_TOKEN", None),
                }
            )
        except ImportError as e:
            print(f"Warning: Could not import gm_app.secrets: {e}")

        # Try local configuration file
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            sys.path.insert(0, script_dir)

            try:
                import code_quality_config_local as local_config

                config.update(
                    {
                        "CODACY_API_KEY": getattr(
                            local_config, "CODACY_API_KEY", config.get("CODACY_API_KEY")
                        ),
                        "SONARQUBE_TOKEN": getattr(
                            local_config,
                            "SONARQUBE_TOKEN",
                            config.get("SONARQUBE_TOKEN"),
                        ),
                        "DEEPSOURCE_TOKEN": getattr(
                            local_config,
                            "DEEPSOURCE_TOKEN",
                            config.get("DEEPSOURCE_TOKEN"),
                        ),
                        "CODACY_USERNAME": getattr(
                            local_config,
                            "CODACY_USERNAME",
                            config.get("CODACY_USERNAME", "charlesmsiegel"),
                        ),
                        "CODACY_PROJECT": getattr(
                            local_config,
                            "CODACY_PROJECT",
                            config.get("CODACY_PROJECT", "gma"),
                        ),
                        "SONARQUBE_URL": getattr(
                            local_config,
                            "SONARQUBE_URL",
                            config.get("SONARQUBE_URL", "https://sonarcloud.io/api"),
                        ),
                        "SONARQUBE_PROJECT_KEY": getattr(
                            local_config,
                            "SONARQUBE_PROJECT_KEY",
                            config.get("SONARQUBE_PROJECT_KEY", "charlesmsiegel_gma"),
                        ),
                        "DEEPSOURCE_USERNAME": getattr(
                            local_config,
                            "DEEPSOURCE_USERNAME",
                            config.get("DEEPSOURCE_USERNAME", "charlesmsiegel"),
                        ),
                        "DEEPSOURCE_PROJECT": getattr(
                            local_config,
                            "DEEPSOURCE_PROJECT",
                            config.get("DEEPSOURCE_PROJECT", "gma"),
                        ),
                    }
                )
            except ImportError:
                # Local config file doesn't exist, that's OK
                pass

        except Exception as e:
            print(f"Warning: Error loading local config: {e}")

    except ImportError:
        print("Warning: Django not available")

    # Override with environment variables if present
    config.update(
        {
            "CODACY_API_KEY": os.environ.get(
                "CODACY_API_KEY", config.get("CODACY_API_KEY")
            ),
            "SONARQUBE_TOKEN": os.environ.get(
                "SONARQUBE_TOKEN", config.get("SONARQUBE_TOKEN")
            ),
            "DEEPSOURCE_TOKEN": os.environ.get(
                "DEEPSOURCE_TOKEN", config.get("DEEPSOURCE_TOKEN")
            ),
            "CODACY_USERNAME": os.environ.get("CODACY_USERNAME", "charlesmsiegel"),
            "CODACY_PROJECT": os.environ.get("CODACY_PROJECT", "gma"),
            "SONARQUBE_URL": os.environ.get(
                "SONARQUBE_URL", "https://sonarcloud.io/api"
            ),
            "SONARQUBE_PROJECT_KEY": os.environ.get(
                "SONARQUBE_PROJECT_KEY", "charlesmsiegel_gma"
            ),
            "DEEPSOURCE_USERNAME": os.environ.get(
                "DEEPSOURCE_USERNAME", "charlesmsiegel"
            ),
            "DEEPSOURCE_PROJECT": os.environ.get("DEEPSOURCE_PROJECT", "gma"),
        }
    )

    return config


def main():
    """Main function to run the code quality issue fetcher."""
    parser = argparse.ArgumentParser(
        description="Fetch code quality issues from multiple services"
    )
    parser.add_argument(
        "--service",
        choices=["codacy", "sonarqube", "deepsource"],
        help="Specific service to fetch from",
    )
    parser.add_argument("--all", action="store_true", help="Fetch from all services")
    parser.add_argument(
        "--output-dir", default=".", help="Output directory for reports"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format",
    )

    args = parser.parse_args()

    if not args.service and not args.all:
        parser.error("Must specify either --service or --all")

    config = load_config()

    # Determine which services to run
    services = []
    if args.all:
        services = ["codacy", "sonarqube", "deepsource"]
    else:
        services = [args.service]

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Fetch from each service
    for service_name in services:
        print(f"\n{'='*50}")
        print(f"Fetching issues from {service_name.upper()}")
        print(f"{'='*50}")

        try:
            if service_name == "codacy":
                fetcher = CodacyFetcher(config)
            elif service_name == "sonarqube":
                fetcher = SonarQubeFetcher(config)
            elif service_name == "deepsource":
                fetcher = DeepSourceFetcher(config)
            else:
                continue

            issues = fetcher.fetch_issues()

            try:
                if args.format == "markdown":
                    content = fetcher.format_issues(issues)
                    filename = f"{service_name.upper()}.md"
                else:  # json
                    content = json.dumps(issues, indent=2)
                    filename = f"{service_name}_issues.json"
            except Exception as format_error:
                print(f"Error formatting {service_name} issues: {format_error}")
                # Save raw JSON as fallback
                content = json.dumps(issues, indent=2)
                filename = f"{service_name}_raw_issues.json"

            output_path = os.path.join(args.output_dir, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"Issues written to: {output_path}")

        except Exception as e:
            print(f"Error processing {service_name}: {e}")
            import traceback

            traceback.print_exc()
            continue

    print(f"\n{'='*50}")
    print("Code quality issue fetching completed!")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
