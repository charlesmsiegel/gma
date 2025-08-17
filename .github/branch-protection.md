# Branch Protection Configuration

This document explains how to configure GitHub branch protection rules to ensure CI checks pass before PRs can be merged.

## Required Branch Protection Rules

Configure these settings for the `main` branch in GitHub:

### Settings → Branches → Add Rule

1. **Branch name pattern**: `main`

2. **Protect matching branches** (check all that apply):
   - ✅ **Require a pull request before merging**
     - ✅ Require approvals: `1`
     - ✅ Dismiss stale PR approvals when new commits are pushed
     - ✅ Require review from code owners (if CODEOWNERS file exists)

   - ✅ **Require status checks to pass before merging**
     - ✅ Require branches to be up to date before merging
     - **Required status checks** (add these as they become available):
       - `test` (from test-and-coverage.yml)
       - `integration-test` (from test-and-coverage.yml)

   - ✅ **Require conversation resolution before merging**

   - ✅ **Restrict pushes that create files that exceed 100MB**

   - ✅ **Do not allow bypassing the above settings**

### Optional Advanced Settings

- **Require linear history**: ✅ (prevents merge commits, requires rebase/squash)
- **Allow force pushes**: ❌ (prevents history rewriting)
- **Allow deletions**: ❌ (prevents accidental branch deletion)

## How to Apply These Settings

### Via GitHub Web Interface

1. Go to your repository on GitHub
2. Navigate to Settings → Branches
3. Click "Add Rule"
4. Follow the settings above

### Via GitHub CLI

```bash
# Install GitHub CLI if not already installed
# Configure branch protection
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["test","integration-test"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions=null
```

## Workflow Integration

The branch protection rules work with our CI workflows:

- **test-and-coverage.yml**: Provides the `test` status check
  - Runs on push/PR to main/develop
  - Must pass for PR merge
  - Includes coverage requirements (80% minimum)

- **claude-code-review.yml**: Provides automated code review
  - Runs on PR open/synchronize
  - Doesn't block merge but provides valuable feedback

- **claude.yml**: Responds to @claude mentions
  - Provides on-demand assistance with issues/PRs

## Pre-commit Integration

Pre-commit hooks (configured in `.pre-commit-config.yaml`) run locally and include:

- Code formatting (black, isort)
- Linting (flake8)
- Type checking (mypy)
- Security scanning (bandit)
- Template linting (djlint)

These run before commits are made, catching issues early before CI.

## Troubleshooting

If CI checks are failing and blocking PRs:

1. **Check the workflow runs** in the Actions tab
2. **Fix issues locally** using the same tools:

   ```bash
   # Run pre-commit to fix formatting
   pre-commit run --all-files

   # Run tests locally
   make test

   # Check coverage
   make test-coverage
   ```

3. **Push fixes** to update the PR
4. **Wait for CI to re-run** and verify green status

## Emergency Override

Repository administrators can bypass protection rules if needed:

- Check "Include administrators" to enforce rules for all users
- Uncheck to allow admin override in emergencies
