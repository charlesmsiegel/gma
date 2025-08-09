# GMA API Reference Documentation

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Handling](#error-handling)
4. [Campaign API](#campaign-api)
5. [Membership API](#membership-api)
6. [Invitation API](#invitation-api)
7. [User API](#user-api)
8. [Data Models](#data-models)
9. [Testing the API](#testing-the-api)

## Overview

The GMA API provides RESTful endpoints for campaign management, user authentication, and real-time collaboration features. All endpoints return JSON responses and follow consistent patterns for error handling and data formatting.

### Base URL

```
Development: http://localhost:8080/api
Production: https://your-domain.com/api
```

### API Versioning

Currently using implicit v1. Future versions will use URL versioning (`/api/v2/`).

### Content Type

All requests and responses use `application/json` content type unless otherwise specified.

### Authentication

Most endpoints require authentication via Django sessions. CSRF protection is enforced for state-changing operations.

## Authentication

### Login

**POST** `/api/auth/login/`

Authenticate user and create session.

**Request Body:**
```json
{
  "username": "user@example.com",  // Email or username
  "password": "userpassword"
}
```

**Success Response (200):**
```json
{
  "detail": "Login successful.",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "display_name": "John D.",
    "timezone": "UTC"
  }
}
```

**Error Response (400):**
```json
{
  "detail": "Invalid credentials."
}
```

### Register

**POST** `/api/auth/register/`

Create new user account.

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123",
  "password_confirm": "securepassword123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Success Response (201):**
```json
{
  "detail": "Registration successful.",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "display_name": "",
    "timezone": "UTC"
  }
}
```

### Logout

**POST** `/api/auth/logout/`

End user session.

**Success Response (200):**
```json
{
  "detail": "Logout successful."
}
```

### Current User

**GET** `/api/auth/user/`

Get current authenticated user information.

**Success Response (200):**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "display_name": "John D.",
  "timezone": "UTC",
  "date_joined": "2024-01-15T10:30:00Z"
}
```

## Error Handling

The API uses standardized error responses across all endpoints.

### Standard Error Format

```json
{
  "detail": "Error message here."
}
```

### Validation Error Format

```json
{
  "field_name": ["Error message for this field."],
  "another_field": ["Another error message."]
}
```

### HTTP Status Codes

- **200** - Success
- **201** - Created
- **204** - No Content (successful deletion)
- **400** - Bad Request (validation errors)
- **401** - Unauthorized (authentication required)
- **403** - Forbidden (insufficient permissions)
- **404** - Not Found (resource doesn't exist or access denied)
- **500** - Internal Server Error

### Security Considerations

- **Permission Denied**: Returns 404 instead of 403 to hide resource existence
- **Generic Messages**: Error messages don't reveal system internals
- **User Enumeration Prevention**: Registration/login errors are generic

## Campaign API

### List Campaigns

**GET** `/api/campaigns/`

Get paginated list of campaigns visible to the user.

**Query Parameters:**
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 25, max: 100)
- `q` - Search query (searches name, description, game_system)
- `role` - Filter by user role: `owner`, `gm`, `player`, `observer`
- `ordering` - Sort by: `created_at`, `-created_at`, `name`, `-name`

**Example Request:**
```
GET /api/campaigns/?q=vampire&role=gm&page_size=10
```

**Success Response (200):**
```json
{
  "count": 45,
  "next": "http://localhost:8080/api/campaigns/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Vampire: The Masquerade - Chicago",
      "slug": "vampire-masquerade-chicago",
      "description": "A dark tale in the Windy City",
      "game_system": "Vampire: The Masquerade",
      "is_active": true,
      "is_public": false,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-16T14:20:00Z",
      "owner": {
        "id": 2,
        "username": "gm_sarah",
        "email": "sarah@example.com",
        "display_name": "Sarah GM"
      },
      "user_role": "GM",
      "member_count": 5
    }
  ]
}
```

### Campaign Detail

**GET** `/api/campaigns/{id}/`

Get detailed campaign information including members and settings (if owner).

**Success Response (200):**
```json
{
  "id": 1,
  "name": "Vampire: The Masquerade - Chicago",
  "slug": "vampire-masquerade-chicago",
  "description": "A dark tale in the Windy City",
  "game_system": "Vampire: The Masquerade",
  "is_active": true,
  "is_public": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-16T14:20:00Z",
  "owner": {
    "id": 2,
    "username": "gm_sarah",
    "email": "sarah@example.com",
    "display_name": "Sarah GM"
  },
  "user_role": "OWNER",
  "member_count": 5,
  "memberships": [
    {
      "id": 1,
      "user": {
        "id": 3,
        "username": "player1",
        "email": "player1@example.com"
      },
      "role": "PLAYER",
      "joined_at": "2024-01-16T09:15:00Z"
    }
  ],
  "members": [
    {
      "id": 2,
      "username": "gm_sarah",
      "email": "sarah@example.com",
      "role": "OWNER"
    },
    {
      "id": 3,
      "username": "player1",
      "email": "player1@example.com",
      "role": "PLAYER"
    }
  ],
  "settings": {
    "visibility": "private",
    "status": "active"
  }
}
```

**Note:** `settings` field only included for campaign owners.

### Create Campaign

**POST** `/api/campaigns/`

Create a new campaign (authenticated users only).

**Request Body:**
```json
{
  "name": "New Campaign",
  "description": "Campaign description",
  "game_system": "D&D 5e",
  "is_public": false
}
```

**Success Response (201):**
```json
{
  "id": 2,
  "name": "New Campaign",
  "slug": "new-campaign",
  "description": "Campaign description",
  "game_system": "D&D 5e",
  "is_active": true,
  "is_public": false,
  "created_at": "2024-01-17T10:30:00Z",
  "updated_at": "2024-01-17T10:30:00Z",
  "owner": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "display_name": "John D."
  },
  "user_role": "OWNER",
  "member_count": 1
}
```

### User Search for Invitations

**GET** `/api/campaigns/{id}/search-users/`

Search for users to invite to a campaign (owner/GM only).

**Query Parameters:**
- `q` - Search query (minimum 2 characters)

**Example Request:**
```
GET /api/campaigns/1/search-users/?q=john
```

**Success Response (200):**
```json
{
  "results": [
    {
      "id": 3,
      "username": "johnsmith",
      "email": "johnsmith@example.com"
    },
    {
      "id": 4,
      "username": "johnny",
      "email": "johnny@example.com"
    }
  ]
}
```

**Notes:**
- Excludes campaign owner, existing members, and users with pending invitations
- Searches username and email fields
- Limited to 10 results
- Minimum query length: 2 characters

## Membership API

### List Campaign Members

**GET** `/api/campaigns/{id}/members/`

Get list of campaign members (campaign members only).

**Success Response (200):**
```json
{
  "results": [
    {
      "user": {
        "id": 2,
        "username": "gm_sarah",
        "email": "sarah@example.com"
      },
      "role": "OWNER",
      "joined_at": null
    },
    {
      "user": {
        "id": 3,
        "username": "player1",
        "email": "player1@example.com"
      },
      "role": "PLAYER",
      "joined_at": "2024-01-16T09:15:00Z"
    }
  ]
}
```

### Add Member

**POST** `/api/campaigns/{id}/members/`

Add a new member to campaign (owner/GM only).

**Request Body:**
```json
{
  "user_id": 3,
  "role": "PLAYER"
}
```

**Success Response (201):**
```json
{
  "user": {
    "id": 3,
    "username": "player1",
    "email": "player1@example.com"
  },
  "role": "PLAYER",
  "joined_at": "2024-01-17T11:30:00Z"
}
```

### Update Member Role

**PATCH** `/api/campaigns/{id}/members/{user_id}/`

Update a member's role (owner/GM only).

**Request Body:**
```json
{
  "role": "GM"
}
```

**Success Response (200):**
```json
{
  "user": {
    "id": 3,
    "username": "player1",
    "email": "player1@example.com"
  },
  "role": "GM",
  "joined_at": "2024-01-16T09:15:00Z"
}
```

### Remove Member

**DELETE** `/api/campaigns/{id}/members/{user_id}/`

Remove a member from campaign (owner/GM only).

**Success Response (204):** No content

### Bulk Member Operations

**POST** `/api/campaigns/{id}/members/bulk/`

Perform bulk operations on campaign members (owner/GM only).

**Add Multiple Members:**
```json
{
  "action": "add",
  "user_ids": [3, 4, 5],
  "role": "OBSERVER"
}
```

**Remove Multiple Members:**
```json
{
  "action": "remove",
  "user_ids": [3, 4]
}
```

**Change Multiple Member Roles:**
```json
{
  "action": "change_role",
  "user_ids": [3, 4],
  "role": "PLAYER"
}
```

**Success Response (200):**
```json
{
  "added": [
    {
      "user_id": 3,
      "username": "player1",
      "role": "OBSERVER"
    }
  ],
  "failed": [
    {
      "user_id": 4,
      "error": "User is already a member of this campaign"
    }
  ]
}
```

## Invitation API

### Send Invitation

**POST** `/api/campaigns/{id}/invitations/`

Send invitation to join campaign (owner/GM only).

**Request Body:**
```json
{
  "user_id": 3,
  "role": "PLAYER",
  "message": "Welcome to our vampire campaign!"
}
```

**Success Response (201):**
```json
{
  "id": 1,
  "campaign": {
    "id": 1,
    "name": "Vampire: The Masquerade - Chicago",
    "game_system": "Vampire: The Masquerade"
  },
  "invited_user": {
    "id": 3,
    "username": "player1",
    "email": "player1@example.com"
  },
  "invited_by": {
    "id": 2,
    "username": "gm_sarah",
    "email": "sarah@example.com"
  },
  "role": "PLAYER",
  "status": "PENDING",
  "message": "Welcome to our vampire campaign!",
  "created_at": "2024-01-17T10:30:00Z",
  "expires_at": "2024-01-24T10:30:00Z"
}
```

### List Campaign Invitations

**GET** `/api/campaigns/{id}/invitations/`

Get campaign invitations (owner/GM only).

**Query Parameters:**
- `status` - Filter by status: `PENDING`, `ACCEPTED`, `DECLINED`, `EXPIRED`

**Success Response (200):**
```json
{
  "results": [
    {
      "id": 1,
      "campaign": {
        "id": 1,
        "name": "Vampire: The Masquerade - Chicago",
        "game_system": "Vampire: The Masquerade"
      },
      "invited_user": {
        "id": 3,
        "username": "player1",
        "email": "player1@example.com"
      },
      "invited_by": {
        "id": 2,
        "username": "gm_sarah",
        "email": "sarah@example.com"
      },
      "role": "PLAYER",
      "status": "PENDING",
      "message": "Welcome to our vampire campaign!",
      "created_at": "2024-01-17T10:30:00Z",
      "expires_at": "2024-01-24T10:30:00Z",
      "is_expired": false
    }
  ]
}
```

### Accept Invitation

**POST** `/api/invitations/{id}/accept/`

Accept a campaign invitation.

**Success Response (200):**
```json
{
  "detail": "Invitation accepted successfully.",
  "membership": {
    "campaign": {
      "id": 1,
      "name": "Vampire: The Masquerade - Chicago",
      "game_system": "Vampire: The Masquerade"
    },
    "role": "PLAYER",
    "joined_at": "2024-01-17T11:45:00Z"
  }
}
```

### Decline Invitation

**POST** `/api/invitations/{id}/decline/`

Decline a campaign invitation.

**Success Response (200):**
```json
{
  "detail": "Invitation declined."
}
```

### List User Invitations

**GET** `/api/invitations/`

Get invitations for the current user.

**Query Parameters:**
- `status` - Filter by status: `PENDING`, `ACCEPTED`, `DECLINED`, `EXPIRED`

**Success Response (200):**
```json
{
  "results": [
    {
      "id": 1,
      "campaign": {
        "id": 1,
        "name": "Vampire: The Masquerade - Chicago",
        "game_system": "Vampire: The Masquerade"
      },
      "invited_user": {
        "id": 3,
        "username": "player1",
        "email": "player1@example.com"
      },
      "invited_by": {
        "id": 2,
        "username": "gm_sarah",
        "email": "sarah@example.com"
      },
      "role": "PLAYER",
      "status": "PENDING",
      "message": "Welcome to our vampire campaign!",
      "created_at": "2024-01-17T10:30:00Z",
      "expires_at": "2024-01-24T10:30:00Z",
      "is_expired": false
    }
  ]
}
```

## User API

### Profile

**GET** `/api/profile/`

Get current user's profile information.

**Success Response (200):**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "display_name": "John D.",
  "timezone": "America/New_York",
  "date_joined": "2024-01-15T10:30:00Z"
}
```

### Update Profile

**PUT/PATCH** `/api/profile/`

Update user profile information.

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Smith",
  "display_name": "Johnny",
  "timezone": "America/Los_Angeles",
  "email": "johnsmith@example.com"
}
```

**Success Response (200):**
```json
{
  "first_name": "John",
  "last_name": "Smith",
  "display_name": "Johnny",
  "timezone": "America/Los_Angeles",
  "email": "johnsmith@example.com"
}
```

## Data Models

### Role Choices

```python
ROLE_CHOICES = [
    ('OWNER', 'Owner'),     # Full campaign control
    ('GM', 'Game Master'),  # Game management permissions
    ('PLAYER', 'Player'),   # Standard participant
    ('OBSERVER', 'Observer') # Read-only access
]
```

### Invitation Status Choices

```python
STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('ACCEPTED', 'Accepted'),
    ('DECLINED', 'Declined'),
    ('EXPIRED', 'Expired')
]
```

### Campaign Visibility

- **Public Campaigns**: Visible to all users, can be joined based on settings
- **Private Campaigns**: Visible only to owner and members

### Invitation Lifecycle

1. **PENDING** - Invitation sent, awaiting response
2. **ACCEPTED** - User accepted and joined campaign
3. **DECLINED** - User declined invitation
4. **EXPIRED** - Invitation expired (7 days default)

## Testing the API

### Using curl

**Authentication:**
```bash
# Login
curl -X POST http://localhost:8080/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user@example.com", "password": "password"}' \
  -c cookies.txt

# Use session for subsequent requests
curl -X GET http://localhost:8080/api/campaigns/ \
  -b cookies.txt
```

**CSRF Token:**
For state-changing operations, include CSRF token:
```bash
# Get CSRF token
CSRF_TOKEN=$(curl -c cookies.txt http://localhost:8080/api/auth/user/ | jq -r .csrf_token)

# Use in POST requests
curl -X POST http://localhost:8080/api/campaigns/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -b cookies.txt \
  -d '{"name": "Test Campaign"}'
```

### Using Postman

1. **Environment Setup:**
   - Create environment with `base_url = http://localhost:8080`
   - Add `csrf_token` variable

2. **Authentication Flow:**
   - POST to `/api/auth/login/` with credentials
   - Extract session cookie automatically
   - Use session for subsequent requests

3. **CSRF Handling:**
   - Get CSRF token from login response or `/api/auth/user/`
   - Add `X-CSRFToken` header to POST/PUT/DELETE requests

### Using Python requests

```python
import requests

# Login and get session
session = requests.Session()
login_response = session.post(
    'http://localhost:8080/api/auth/login/',
    json={'username': 'user@example.com', 'password': 'password'}
)

# Get CSRF token
csrf_response = session.get('http://localhost:8080/api/auth/user/')
csrf_token = csrf_response.cookies.get('csrftoken')

# Make authenticated request
session.headers.update({'X-CSRFToken': csrf_token})
campaigns = session.get('http://localhost:8080/api/campaigns/')
print(campaigns.json())
```

---

*This API reference should be updated as new endpoints are added. Last updated: 2025-01-08*
