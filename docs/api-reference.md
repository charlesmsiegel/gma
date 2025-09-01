# GMA API Reference Documentation

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Handling](#error-handling)
4. [Campaign API](#campaign-api)
5. [Membership API](#membership-api)
6. [Invitation API](#invitation-api)
7. [User API](#user-api)
8. [Session Management API](#session-management-api)
9. [Character API](#character-api)
10. [Location API](#location-api)
11. [Item API](#item-api)
12. [Prerequisite API](#prerequisite-api)
13. [Scene API](#scene-api)
14. [Scene Message History API](#scene-message-history-api)
15. [WebSocket Chat API](#websocket-chat-api)
16. [Source Reference API](#source-reference-api)
17. [Data Models](#data-models)
18. [Testing the API](#testing-the-api)

## Overview

The GMA API provides RESTful endpoints for campaign management, user authentication, and real-time scene chat communication. All endpoints return JSON responses and follow consistent patterns for error handling and data formatting. The real-time chat system uses WebSocket connections for live message broadcasting with comprehensive rate limiting and permission controls.

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

## Session Management API

The Session Management API provides comprehensive user session tracking, security monitoring, and session lifecycle management capabilities. This API enables monitoring of user sessions across devices, detection of suspicious activity, and secure session termination.

### List User Sessions

**GET** `/api/auth/sessions/`

Get all active sessions for the authenticated user.

**Success Response (200):**
```json
[
  {
    "id": 1,
    "device_type": "desktop",
    "browser": "Chrome",
    "operating_system": "Windows",
    "location": "San Francisco, CA",
    "ip_address": "192.168.1.100",
    "is_active": true,
    "remember_me": false,
    "created_at": "2024-01-15T10:30:00Z",
    "last_activity": "2024-01-15T15:45:00Z",
    "current_session": true
  },
  {
    "id": 2,
    "device_type": "mobile",
    "browser": "Safari",
    "operating_system": "iOS",
    "location": "New York, NY",
    "ip_address": "203.0.113.45",
    "is_active": true,
    "remember_me": true,
    "created_at": "2024-01-14T08:15:00Z",
    "last_activity": "2024-01-15T12:20:00Z",
    "current_session": false
  }
]
```

### Get Current Session

**GET** `/api/auth/session/current/`

Get detailed information about the current session including recent security events.

**Success Response (200):**
```json
{
  "id": 1,
  "device_type": "desktop",
  "browser": "Chrome/120.0",
  "operating_system": "Windows 11",
  "location": "San Francisco, CA",
  "ip_address": "192.168.1.100",
  "device_fingerprint": "a1b2c3d4e5f6...",
  "is_active": true,
  "remember_me": false,
  "created_at": "2024-01-15T10:30:00Z",
  "last_activity": "2024-01-15T15:45:00Z",
  "session_expires": "2024-01-15T22:30:00Z",
  "recent_security_events": [
    {
      "event_type": "login_success",
      "timestamp": "2024-01-15T10:30:00Z",
      "ip_address": "192.168.1.100",
      "details": {}
    }
  ]
}
```

### Terminate Session

**DELETE** `/api/auth/sessions/{session_id}/`

Terminate a specific user session. Users can only terminate their own sessions.

**Path Parameters:**
- `session_id` (integer): ID of the session to terminate

**Success Response (204):**
No content returned on successful termination.

**Error Responses:**

**404 Not Found:**
```json
{
  "error": "Session not found or access denied"
}
```

### Terminate All Sessions

**POST** `/api/auth/sessions/all/`

Terminate all sessions except the current one.

**Success Response (200):**
```json
{
  "terminated_sessions": 3,
  "message": "All other sessions terminated successfully"
}
```

### Extend Session

**POST** `/api/auth/sessions/extend/`

Extend the current session expiry time.

**Request Body:**
```json
{
  "hours": 24
}
```

**Success Response (200):**
```json
{
  "message": "Session extended successfully",
  "new_expiry": "2024-01-16T22:30:00Z",
  "extended_by_hours": 24
}
```

**Error Responses:**

**400 Bad Request:**
```json
{
  "error": "Invalid extension period. Must be between 1 and 720 hours"
}
```

### Session Security Features

The Session Management API includes comprehensive security monitoring:

#### Device Tracking
- **Device Fingerprinting**: Unique device identification based on browser, OS, and hardware characteristics
- **Location Detection**: Geographic location tracking based on IP address
- **Browser Analysis**: Detailed browser and operating system identification

#### Security Monitoring
- **IP Address Changes**: Detection and logging of IP address changes within sessions
- **User Agent Changes**: Monitoring for significant browser/device changes
- **Concurrent Session Limits**: Automatic enforcement of maximum concurrent sessions per user
- **Geographic Anomalies**: Detection of impossible travel patterns
- **Session Hijacking Protection**: Risk scoring and automatic session termination

#### Audit Logging
All session security events are logged with the following event types:
- `login_success` - Successful user login
- `login_failed` - Failed login attempt
- `logout` - User logout
- `session_hijack_attempt` - Suspected session hijacking
- `suspicious_activity` - General suspicious activity
- `ip_address_changed` - IP address change detected
- `user_agent_changed` - User agent string changed
- `session_extended` - Session expiry extended
- `session_terminated` - Session manually terminated
- `concurrent_session_limit` - Too many concurrent sessions
- `password_changed` - Password changed (invalidates sessions)
- `account_locked` - Account locked due to security

#### Risk Assessment
The system calculates risk scores (0.0-10.0) based on:
- Event type severity
- Geographic location changes
- Device fingerprint mismatches
- Time-based access patterns
- Concurrent session patterns

Risk thresholds:
- **Low Risk (0.0-3.9)**: Normal activity, no action taken
- **Medium Risk (4.0-6.9)**: Increased monitoring, possible alerts
- **High Risk (7.0-8.9)**: Security alert sent to user
- **Critical Risk (9.0+)**: Automatic session termination

## Character API

### List Characters

**GET** `/api/characters/`

Get list of characters. Supports filtering by campaign and character type. The Character model uses multiple manager instances for efficient filtering:

**Manager Architecture (Backend):**
- `Character.objects`: Primary manager (excludes soft-deleted)
- `Character.npcs`: Only NPCs, excludes soft-deleted **[New in #175]**
- `Character.pcs`: Only PCs, excludes soft-deleted **[New in #175]**
- `Character.all_objects`: Includes soft-deleted characters

**Character Status System (Issue #180):**
Characters now include a comprehensive status workflow:
- **DRAFT**: Initial character creation state
- **SUBMITTED**: Character submitted for GM approval
- **APPROVED**: Character approved for campaign play
- **INACTIVE**: Temporarily inactive character
- **RETIRED**: Permanently retired character
- **DECEASED**: Character marked as deceased

**Query Parameters:**
- `campaign_id` (optional): Filter characters by campaign ID
- `npc` (optional): Filter by character type (`true` for NPCs, `false` for PCs)
- `player_owner` (optional): Filter by player owner ID
- `status` (optional): Filter by character status (`DRAFT`, `SUBMITTED`, `APPROVED`, `INACTIVE`, `RETIRED`, `DECEASED`)

**Success Response (200):**
```json
{
  "results": [
    {
      "id": 1,
      "name": "Aria Nightwhisper",
      "description": "A mysterious mage skilled in the arts of Mind and Spirit.",
      "game_system": "Mage: The Ascension",
      "npc": false,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-20T14:45:00Z",
      "campaign": {
        "id": 1,
        "name": "Chronicles of the Technocracy",
        "game_system": "Mage: The Ascension"
      },
      "player_owner": {
        "id": 2,
        "username": "player1",
        "email": "player1@example.com"
      },
      "character_type": "MageCharacter",
      "status": "APPROVED",
      "is_deleted": false,
      "deleted_at": null,
      "deleted_by": null,
      "arete": 2,
      "quintessence": 5,
      "paradox": 1,
      "willpower": 4,
      "owned_locations": [
        {
          "id": 15,
          "name": "Aria's Sanctum",
          "description": "Hidden magical workspace"
        },
        {
          "id": 23,
          "name": "The Mystic Eye Bookshop",
          "description": "Occult bookstore and meeting place"
        }
      ]
    },
    {
      "id": 2,
      "name": "Dr. Morrison",
      "description": "A Technocratic operative and medical researcher.",
      "game_system": "Mage: The Ascension",
      "npc": true,
      "created_at": "2024-01-16T09:15:00Z",
      "updated_at": "2024-01-16T09:15:00Z",
      "campaign": {
        "id": 1,
        "name": "Chronicles of the Technocracy",
        "game_system": "Mage: The Ascension"
      },
      "player_owner": {
        "id": 1,
        "username": "gamemaster",
        "email": "gm@example.com"
      },
      "character_type": "MageCharacter",
      "status": "APPROVED",
      "is_deleted": false,
      "deleted_at": null,
      "deleted_by": null,
      "arete": 4,
      "quintessence": 10,
      "paradox": 0,
      "willpower": 6
    }
  ],
  "count": 2
}
```

### Get Character

**GET** `/api/characters/{id}/`

Get detailed information about a specific character.

**Success Response (200):**
```json
{
  "id": 1,
  "name": "Aria Nightwhisper",
  "description": "A mysterious mage skilled in the arts of Mind and Spirit.",
  "game_system": "Mage: The Ascension",
  "npc": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:45:00Z",
  "campaign": {
    "id": 1,
    "name": "Chronicles of the Technocracy",
    "game_system": "Mage: The Ascension"
  },
  "player_owner": {
    "id": 2,
    "username": "player1",
    "email": "player1@example.com"
  },
  "character_type": "MageCharacter",
  "status": "APPROVED",
  "is_deleted": false,
  "deleted_at": null,
  "deleted_by": null,
  "arete": 2,
  "quintessence": 5,
  "paradox": 1,
  "willpower": 4,
  "owned_locations": [
    {
      "id": 15,
      "name": "Aria's Sanctum",
      "description": "Hidden magical workspace",
      "campaign": 1,
      "parent": null,
      "owner_display": "Aria Nightwhisper (PC)"
    },
    {
      "id": 23,
      "name": "The Mystic Eye Bookshop",
      "description": "Occult bookstore and meeting place",
      "campaign": 1,
      "parent": null,
      "owner_display": "Aria Nightwhisper (PC)"
    }
  ]
}
```

### Create Character

**POST** `/api/characters/`

Create a new character. Requires campaign membership.

**Request Body:**
```json
{
  "name": "New Character",
  "description": "Character background and description",
  "npc": false,
  "campaign": 1,
  "character_type": "MageCharacter",
  "willpower": 3,
  "arete": 1,
  "quintessence": 0,
  "paradox": 0
}
```

**Success Response (201):**
```json
{
  "id": 3,
  "name": "New Character",
  "description": "Character background and description",
  "game_system": "Mage: The Ascension",
  "npc": false,
  "created_at": "2024-01-21T16:30:00Z",
  "updated_at": "2024-01-21T16:30:00Z",
  "campaign": {
    "id": 1,
    "name": "Chronicles of the Technocracy",
    "game_system": "Mage: The Ascension"
  },
  "player_owner": {
    "id": 2,
    "username": "player1",
    "email": "player1@example.com"
  },
  "character_type": "MageCharacter",
  "status": "DRAFT",
  "is_deleted": false,
  "deleted_at": null,
  "deleted_by": null,
  "arete": 1,
  "quintessence": 0,
  "paradox": 0,
  "willpower": 3
}
```

### Update Character

**PUT** `/api/characters/{id}/`

Update an existing character. Only character owner, campaign owner, or GM can update.

**Request Body:**
```json
{
  "name": "Updated Character Name",
  "description": "Updated description",
  "npc": true,
  "arete": 2,
  "willpower": 4
}
```

### Delete Character

**DELETE** `/api/characters/{id}/`

Soft delete a character. Only character owner, campaign owner, or GM can delete (based on campaign settings).

**Success Response (204):** No content

### Character Status Transitions

**POST** `/api/characters/{id}/submit-for-approval/`

Submit character for GM approval (character owners only).

**Success Response (200):**
```json
{
  "detail": "Character submitted for approval.",
  "status": "SUBMITTED"
}
```

**POST** `/api/characters/{id}/approve/`

Approve character for campaign play (GMs/owners only).

**Success Response (200):**
```json
{
  "detail": "Character approved.",
  "status": "APPROVED"
}
```

**POST** `/api/characters/{id}/reject/`

Reject character back to draft (GMs/owners only).

**Success Response (200):**
```json
{
  "detail": "Character rejected.",
  "status": "DRAFT"
}
```

**POST** `/api/characters/{id}/deactivate/`

Deactivate approved character (GMs/owners only).

**Success Response (200):**
```json
{
  "detail": "Character deactivated.",
  "status": "INACTIVE"
}
```

**POST** `/api/characters/{id}/activate/`

Reactivate inactive character (GMs/owners only).

**Success Response (200):**
```json
{
  "detail": "Character activated.",
  "status": "APPROVED"
}
```

**POST** `/api/characters/{id}/retire/`

Retire character from campaign (owners + GMs/owners).

**Success Response (200):**
```json
{
  "detail": "Character retired.",
  "status": "RETIRED"
}
```

**POST** `/api/characters/{id}/mark-deceased/`

Mark character as deceased (GMs/owners only).

**Success Response (200):**
```json
{
  "detail": "Character marked as deceased.",
  "status": "DECEASED"
}
```

### Character Audit Trail

**GET** `/api/characters/{id}/audit-log/`

Get character audit trail including status transitions.

**Success Response (200):**
```json
{
  "results": [
    {
      "id": 1,
      "action": "UPDATE",
      "field_changes": {
        "status": {
          "old": "DRAFT",
          "new": "SUBMITTED"
        }
      },
      "changed_by": {
        "id": 2,
        "username": "player1"
      },
      "timestamp": "2024-01-20T14:45:00Z"
    }
  ]
}
```

**Character Filtering Examples:**

```bash
# Get all NPCs in a campaign
GET /api/characters/?campaign_id=1&npc=true

# Get all PCs owned by a specific player
GET /api/characters/?player_owner=2&npc=false

# Get all approved characters in a campaign
GET /api/characters/?campaign_id=1&status=APPROVED

# Get all characters pending approval
GET /api/characters/?campaign_id=1&status=SUBMITTED

# Get all draft characters owned by a player
GET /api/characters/?player_owner=2&status=DRAFT

# Get all characters in a campaign (all statuses)
GET /api/characters/?campaign_id=1
```

**Backend Manager Usage (New in #175):**

The Character model provides dedicated manager instances for efficient queries:

```python
# NEW: Direct manager instances (recommended)
Character.npcs.all()                    # Only NPCs, auto-excludes soft-deleted
Character.pcs.all()                     # Only PCs, auto-excludes soft-deleted

# NEW: Filter with additional criteria
Character.npcs.filter(campaign=campaign)         # NPCs in specific campaign
Character.pcs.filter(player_owner=user)          # PCs owned by user
Character.npcs.filter(game_system="Mage")        # NPCs of specific game system

# NEW: Polymorphic inheritance support
Character.npcs.instance_of(MageCharacter)        # Only Mage NPCs
Character.pcs.instance_of(VampireCharacter)      # Only Vampire PCs

# EXISTING: Backward compatibility preserved
Character.objects.npcs()                         # Same as Character.npcs.all()
Character.objects.player_characters()            # Same as Character.pcs.all()
Character.objects.filter(npc=True)               # Manual filtering still works
```

**Performance Benefits:**
- Automatic soft-delete filtering at manager level
- Optimized database queries using indexed fields
- Full polymorphic inheritance support
- Reduced application-level filtering logic

## Location API

### Character-Location Ownership Relationship (Issue #186)

The Location model supports character ownership, enabling typical RPG scenarios like NPCs owning taverns or players owning strongholds.

**Key Features:**

- Both Player Characters (PCs) and Non-Player Characters (NPCs) can own locations
- Locations can be unowned (owned_by = null)
- Cross-campaign validation ensures characters can only own locations in their own campaign
- Permission system integration for location editing rights

**API Access Patterns:**

**Character's Owned Locations (via Character API):**
```bash
# Get character with owned locations included
GET /api/characters/{id}/

# Example response includes owned_locations field:
{
  "id": 1,
  "name": "Aria Nightwhisper",
  "owned_locations": [
    {
      "id": 15,
      "name": "Aria's Sanctum",
      "description": "Hidden magical workspace",
      "campaign": 1,
      "parent": null,
      "owner_display": "Aria Nightwhisper (PC)"
    }
  ]
}
```

**Future Location Endpoints (Not Yet Implemented):**
```bash
# List all locations in a campaign
GET /api/locations/?campaign_id=1

# Get locations by ownership
GET /api/locations/?campaign_id=1&owned_by=character_id

# Get unowned locations (available for acquisition)
GET /api/locations/?campaign_id=1&owned_by__isnull=true

# Get locations owned by NPCs
GET /api/locations/?campaign_id=1&owned_by__npc=true

# Get locations owned by PCs
GET /api/locations/?campaign_id=1&owned_by__npc=false
```

**Location Model Structure:**
```json
{
  "id": 15,
  "name": "The Prancing Pony",
  "description": "Famous inn in Bree",
  "campaign": {
    "id": 1,
    "name": "Lord of the Rings Campaign"
  },
  "parent": null,
  "children": [
    {
      "id": 16,
      "name": "Common Room"
    },
    {
      "id": 17,
      "name": "Private Dining Room"
    }
  ],
  "owned_by": {
    "id": 42,
    "name": "Barliman Butterbur",
    "npc": true,
    "campaign": 1
  },
  "owner_display": "Barliman Butterbur (NPC)",
  "created_by": {
    "id": 1,
    "username": "gamemaster"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:45:00Z"
}
```

**Ownership Business Rules:**

- Characters can only own locations within their own campaign
- Location ownership affects edit/delete permissions for players
- Players can edit locations owned by their characters
- GMs and campaign owners can edit all locations regardless of ownership
- Ownership transfers are performed by updating the `owned_by` field

**Common Usage Scenarios:**

**NPC Business Ownership:**
```python
# Tavern keeper owns multiple properties
tavern_keeper = Character.objects.get(name="Innkeeper Bob")
properties = tavern_keeper.owned_locations.all()
# Returns: ["The Red Dragon Inn", "Inn Stables", "Private Quarters"]
```

**Player Character Real Estate:**
```python
# Player character acquires stronghold
player_char = Character.objects.get(name="Lord Aragorn")
stronghold = Location.objects.get(name="Minas Tirith")
stronghold.owned_by = player_char
stronghold.save()
```

**Property Portfolio Analysis:**
```python
# Get all character-owned locations in campaign
owned_locations = Location.objects.filter(
    campaign=campaign,
    owned_by__isnull=False
).select_related('owned_by')

# Group by character type
npc_properties = owned_locations.filter(owned_by__npc=True)
pc_properties = owned_locations.filter(owned_by__npc=False)
```

## Item API

### Item Management System

The Item API provides comprehensive equipment and treasure management capabilities for campaigns, featuring soft delete functionality, single character ownership, polymorphic type support, and role-based permissions.

#### Implementation Status

**Database & Models:**
- ✅ **Item Model**: Fully implemented with polymorphic inheritance support
- ✅ **Soft Delete Pattern**: Complete implementation with audit trails
- ✅ **Single Character Ownership**: Character ownership with transfer tracking
- ✅ **Permission System**: Role-based access control integration
- ✅ **Admin Interface**: 6 bulk operations with comprehensive management

**API Implementation:**
- ✅ **REST Endpoints**: Complete CRUD operations implemented
- ✅ **Serializers**: ItemSerializer and ItemCreateUpdateSerializer
- ✅ **URL Configuration**: Full URL routing configured
- ✅ **Permission Integration**: Role-based access control enforced

**Testing Coverage:**
- ✅ **59 Comprehensive API Tests**: Endpoint validation, permissions, filtering
- ✅ **Additional Model Tests**: 109+ tests for model validation, soft delete, admin operations
- ✅ **Security Testing**: Permission boundaries and information leakage prevention
- ✅ **Polymorphic Support**: Ready for future item type extensions

### Authentication

All Item API endpoints require authentication. Users must be campaign members to access items.

### Item CRUD Operations

#### List Items

**GET** `/api/items/`

List items in a campaign with advanced filtering and search capabilities.

**Required Query Parameters:**
- `campaign_id` (integer): Campaign ID to filter items by

**Optional Query Parameters:**
- `owner` (integer|"null"): Filter by character owner ID, or "null" for unowned items
- `created_by` (integer): Filter by user creator ID
- `quantity_min` (integer): Minimum quantity filter (≥1)
- `quantity_max` (integer): Maximum quantity filter (≥1)
- `q` (string): Search in item name and description
- `include_deleted` (boolean): Include soft-deleted items (default: false)
- `ordering` (string): Sort by `name`, `-name`, `quantity`, `-quantity`, `created_at`, `-created_at`, `updated_at`, `-updated_at`, `id`, `-id`
- `page` (integer): Page number for pagination
- `page_size` (integer): Items per page (max 100, default 20)

**Request Example:**
```bash
GET /api/items/?campaign_id=1&owner=5&q=sword&quantity_min=1&ordering=name
```

**Success Response (200):**
```json
{
  "count": 25,
  "next": "http://localhost:8080/api/items/?campaign_id=1&page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Enchanted Longsword",
      "description": "A finely crafted magical longsword with frost enchantment",
      "quantity": 1,
      "campaign": {
        "id": 1,
        "name": "Adventures in Mystara"
      },
      "owner": {
        "id": 5,
        "name": "Sir Gareth",
        "character_type": "PlayerCharacter"
      },
      "created_by": {
        "id": 2,
        "username": "gamemaster",
        "display_name": "Game Master"
      },
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "last_transferred_at": "2024-01-15T11:45:00Z",
      "is_deleted": false,
      "deleted_at": null,
      "deleted_by": null,
      "polymorphic_ctype": {
        "app_label": "items",
        "model": "item"
      }
    }
  ]
}
```

**Error Responses:**
- **400 Bad Request**: Missing or invalid campaign_id
- **404 Not Found**: Campaign doesn't exist or user lacks access
- **401 Unauthorized**: Authentication required

#### Create Item

**POST** `/api/items/`

Create a new item in a campaign.

**Request Body:**
```json
{
  "name": "Health Potion",
  "description": "Restores 2d8+2 hit points when consumed",
  "quantity": 5,
  "campaign": 1,
  "owner": 3
}
```

**Required Fields:**
- `name` (string): Item name
- `quantity` (integer): Quantity (≥1)
- `campaign` (integer): Campaign ID

**Optional Fields:**
- `description` (string): Item description
- `owner` (integer|null): Character owner ID (must be in same campaign)

**Success Response (201):**
```json
{
  "id": 15,
  "name": "Health Potion",
  "description": "Restores 2d8+2 hit points when consumed",
  "quantity": 5,
  "campaign": {
    "id": 1,
    "name": "Adventures in Mystara"
  },
  "owner": {
    "id": 3,
    "name": "Lyra the Healer",
    "character_type": "PlayerCharacter"
  },
  "created_by": {
    "id": 1,
    "username": "player1",
    "display_name": "Alice"
  },
  "created_at": "2024-01-15T12:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z",
  "last_transferred_at": null,
  "is_deleted": false,
  "deleted_at": null,
  "deleted_by": null,
  "polymorphic_ctype": {
    "app_label": "items",
    "model": "item"
  }
}
```

**Error Responses:**
- **400 Bad Request**: Validation errors in request data
- **403 Forbidden**: Observers cannot create items
- **404 Not Found**: Campaign doesn't exist or user lacks access
- **401 Unauthorized**: Authentication required

#### Get Item Details

**GET** `/api/items/{id}/`

Retrieve detailed information about a specific item.

**Success Response (200):**
```json
{
  "id": 1,
  "name": "Enchanted Longsword",
  "description": "A finely crafted magical longsword with frost enchantment",
  "quantity": 1,
  "campaign": {
    "id": 1,
    "name": "Adventures in Mystara"
  },
  "owner": {
    "id": 5,
    "name": "Sir Gareth",
    "character_type": "PlayerCharacter"
  },
  "created_by": {
    "id": 2,
    "username": "gamemaster",
    "display_name": "Game Master"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "last_transferred_at": "2024-01-15T11:45:00Z",
  "is_deleted": false,
  "deleted_at": null,
  "deleted_by": null,
  "polymorphic_ctype": {
    "app_label": "items",
    "model": "item"
  }
}
```

**Error Responses:**
- **404 Not Found**: Item doesn't exist or user lacks access
- **401 Unauthorized**: Authentication required

#### Update Item

**PUT** `/api/items/{id}/`

Update an existing item (full update).

**Request Body:**
```json
{
  "name": "Enchanted Longsword +2",
  "description": "A masterwork magical longsword with enhanced frost enchantment",
  "quantity": 1,
  "owner": 7
}
```

**Success Response (200):**
```json
{
  "id": 1,
  "name": "Enchanted Longsword +2",
  "description": "A masterwork magical longsword with enhanced frost enchantment",
  "quantity": 1,
  "campaign": {
    "id": 1,
    "name": "Adventures in Mystara"
  },
  "owner": {
    "id": 7,
    "name": "Dame Victoria",
    "character_type": "PlayerCharacter"
  },
  "created_by": {
    "id": 2,
    "username": "gamemaster",
    "display_name": "Game Master"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T14:20:00Z",
  "last_transferred_at": "2024-01-15T14:20:00Z",
  "is_deleted": false,
  "deleted_at": null,
  "deleted_by": null,
  "polymorphic_ctype": {
    "app_label": "items",
    "model": "item"
  }
}
```

**Error Responses:**
- **400 Bad Request**: Validation errors in request data
- **404 Not Found**: Item doesn't exist, is deleted, or user lacks access
- **401 Unauthorized**: Authentication required

#### Delete Item (Soft Delete)

**DELETE** `/api/items/{id}/`

Soft delete an item. The item is marked as deleted but remains in the database for potential restoration.

**Success Response (204):**
No content returned.

**Error Responses:**
- **404 Not Found**: Item doesn't exist, is already deleted, or user lacks access
- **401 Unauthorized**: Authentication required

### Permission System

Items inherit the campaign permission structure with role-based access control:

#### Permission Hierarchy
- **OWNER**: Full access to all campaign items
- **GM**: Full access to all campaign items
- **PLAYER**: Can view all items, create/edit/delete own items
- **OBSERVER**: Can view all items, cannot create/edit/delete

#### Permission Rules
- Users can only access items in campaigns they are members of
- Item creators can always delete their own items regardless of role
- Superusers have full access to all items
- Soft-deleted items are only visible to users with delete permissions

#### Security Features
- Returns 404 instead of 403 to hide resource existence from non-members
- Campaign membership validation prevents unauthorized access
- Character ownership validation ensures owners belong to the same campaign

### Single Character Ownership

The Item API supports single character ownership with transfer tracking:

#### Ownership Features
- **One Owner**: Each item can be owned by exactly one character or remain unowned
- **Transfer Tracking**: `last_transferred_at` timestamp updated when ownership changes
- **Campaign Scoping**: Character owners must belong to the same campaign as the item
- **Safe Deletion**: Items become unowned when their owner character is deleted

#### Ownership Management
```json
// Transfer ownership
{
  "owner": 5  // Character ID in same campaign
}

// Remove ownership
{
  "owner": null
}

// Query unowned items
GET /api/items/?campaign_id=1&owner=null
```

### Polymorphic Type Support

The Item API is designed for extensibility with polymorphic inheritance:

#### Current Implementation
- All items use the base `Item` model
- `polymorphic_ctype` field indicates the model type
- Ready for future specialization into item subtypes

#### Future Extensions
The API will support specialized item types:
- `WeaponItem`: Combat statistics and properties
- `ArmorItem`: Protection values and restrictions
- `ConsumableItem`: Usage limits and effects
- `MagicItem`: Magical properties and requirements

#### Polymorphic Response
```json
{
  "polymorphic_ctype": {
    "app_label": "items",
    "model": "item"
  }
}
```

### Common Use Cases

#### Campaign Inventory Management
```bash
# List all campaign items
GET /api/items/?campaign_id=1

# Search for weapons
GET /api/items/?campaign_id=1&q=sword

# Find items owned by specific character
GET /api/items/?campaign_id=1&owner=5
```

#### Item Filtering and Search
```bash
# Find high-value items (quantity-based filtering)
GET /api/items/?campaign_id=1&quantity_min=5

# Search with pagination
GET /api/items/?campaign_id=1&page=2&page_size=50

# Include deleted items (for restoration)
GET /api/items/?campaign_id=1&include_deleted=true
```

#### Character Equipment Management
```bash
# Transfer item to character
PUT /api/items/15/
{
  "owner": 7
}

# Remove item from character
PUT /api/items/15/
{
  "owner": null
}
```

## Prerequisite API

### Prerequisite System Overview

The Prerequisite API provides comprehensive requirement validation and management for character advancement, item usage, spell casting, and other game mechanics. The system supports complex logical requirements with intuitive helper functions, a powerful checking engine, and visual building tools.

#### Implementation Status

**Core System (Issues #188-192):**
- ✅ **Requirement Helpers (Issue #188)**: Helper functions for building JSON requirements
- ✅ **Checking Engine (Issue #189)**: Comprehensive validation engine with recursive checking
- ✅ **Visual Builder UI (Issue #190)**: Django form widget integration
- ✅ **Drag-Drop Interface (Issue #191)**: Advanced JavaScript interface with accessibility
- ✅ **Admin Interface (Issue #192)**: Full Django admin integration with bulk operations

**API Implementation Status:**
- 🚧 **Future Implementation**: REST endpoints planned for Phase 3
- ✅ **Helper Functions**: Available for programmatic use
- ✅ **Model Integration**: Prerequisite models with GenericForeignKey support
- ✅ **Checking System**: RequirementChecker class for validation operations

### Python API Usage

The prerequisite system is currently available through Python APIs for server-side use:

#### Helper Functions

```python
from prerequisites.helpers import trait_req, has_item, any_of, all_of, count_with_tag

# Simple requirements
strength_req = trait_req("strength", minimum=3)
sword_req = has_item("weapons", name="Magic Sword")

# Complex logical combinations
combat_req = any_of(
    trait_req("strength", minimum=4),
    trait_req("dexterity", minimum=4)
)

advanced_req = all_of(
    trait_req("arete", minimum=3),
    has_item("foci", name="Crystal Orb"),
    count_with_tag("spheres", "elemental", minimum=2)
)
```

**Available Helper Functions:**
- `trait_req(name, minimum=None, maximum=None, exact=None)`: Character trait requirements
- `has_item(field, id=None, name=None, **kwargs)`: Item possession requirements
- `any_of(*requirements)`: Logical OR combinations
- `all_of(*requirements)`: Logical AND combinations
- `count_with_tag(model, tag, minimum=None, maximum=None)`: Tagged object counting

#### Requirement Checking

```python
from prerequisites.checkers import RequirementChecker
from characters.models import Character

# Initialize checker
checker = RequirementChecker()

# Get character
character = Character.objects.get(id=1)

# Check simple requirement
result = checker.check_requirement(character, strength_req)
print(f"Passed: {result.passed}")
print(f"Message: {result.message}")

# Check complex requirement with detailed results
result = checker.check_requirement(character, advanced_req)
if not result.passed:
    print("Failed requirements:")
    for detail in result.details:
        if not detail.passed:
            print(f"  - {detail.requirement_type}: {detail.message}")
```

**RequirementCheckResult Properties:**
- `passed`: Boolean indicating if requirement was met
- `message`: Human-readable description of the result
- `details`: List of sub-requirement results for complex requirements
- `requirement_type`: Type of requirement checked (trait, has, any, all, count_tag)

#### Model Integration

```python
from prerequisites.models import Prerequisite, PrerequisiteCheckResult

# Create standalone prerequisite
prereq = Prerequisite.objects.create(
    description="Combat mastery required",
    requirements=all_of(
        trait_req("strength", minimum=3),
        trait_req("melee", minimum=2)
    )
)

# Attach prerequisite to any model
character_prereq = Prerequisite.objects.create(
    description="Advanced training needed",
    requirements=has_item("training", name="Master Class"),
    content_object=character
)

# Check prerequisite against character
result = checker.check_requirement(character, prereq.requirements)

# Log result for audit trail
check_result = PrerequisiteCheckResult.objects.create(
    content_object=item_requiring_prereq,
    character=character,
    requirements=prereq.requirements,
    result=result.passed,
    failure_reasons=result.get_failure_reasons() if not result.passed else []
)
```

### Planned REST API Endpoints (Future Implementation)

The following REST API endpoints are planned for Phase 3 implementation:

#### Prerequisite Management

**List Prerequisites**
```http
GET /api/prerequisites/
```

Query Parameters:
- `content_type`: Filter by attached object type
- `object_id`: Filter by attached object ID
- `search`: Search in descriptions
- `limit`: Pagination limit (default: 20)
- `offset`: Pagination offset

Response:
```json
{
    "count": 25,
    "next": "/api/prerequisites/?offset=20",
    "previous": null,
    "results": [
        {
            "id": 1,
            "description": "Combat mastery required",
            "requirements": {
                "all": [
                    {"trait": {"name": "strength", "min": 3}},
                    {"trait": {"name": "melee", "min": 2}}
                ]
            },
            "content_type": "characters.character",
            "object_id": 123,
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    ]
}
```

**Create Prerequisite**
```http
POST /api/prerequisites/
```

Request Body:
```json
{
    "description": "Advanced spell mastery",
    "requirements": {
        "all": [
            {"trait": {"name": "arete", "min": 4}},
            {"count_tag": {"model": "spheres", "tag": "forces", "minimum": 3}}
        ]
    },
    "content_type": "items.item",
    "object_id": 456
}
```

**Retrieve Prerequisite**
```http
GET /api/prerequisites/{id}/
```

**Update Prerequisite**
```http
PUT /api/prerequisites/{id}/
PATCH /api/prerequisites/{id}/
```

**Delete Prerequisite**
```http
DELETE /api/prerequisites/{id}/
```

#### Requirement Validation

**Check Single Requirement**
```http
POST /api/prerequisites/{id}/check/
```

Request Body:
```json
{
    "character_id": 123
}
```

Response:
```json
{
    "passed": false,
    "message": "Character does not meet all requirements",
    "details": [
        {
            "requirement_type": "trait",
            "passed": true,
            "message": "Strength requirement met (4 >= 3)"
        },
        {
            "requirement_type": "trait",
            "passed": false,
            "message": "Melee requirement not met (1 < 2)"
        }
    ],
    "checked_at": "2024-01-15T14:25:30Z"
}
```

**Bulk Requirement Checking**
```http
POST /api/prerequisites/bulk-check/
```

Request Body:
```json
{
    "character_id": 123,
    "prerequisite_ids": [1, 2, 3, 4, 5]
}
```

Response:
```json
{
    "character_id": 123,
    "results": [
        {
            "prerequisite_id": 1,
            "passed": true,
            "message": "All requirements met"
        },
        {
            "prerequisite_id": 2,
            "passed": false,
            "message": "Missing required item",
            "details": [...]
        }
    ],
    "checked_at": "2024-01-15T14:30:00Z"
}
```

#### Requirement Templates

**List Templates**
```http
GET /api/prerequisites/templates/
```

**Apply Template**
```http
POST /api/prerequisites/templates/{template_id}/apply/
```

Request Body:
```json
{
    "content_type": "items.item",
    "object_ids": [123, 124, 125],
    "description_override": "Custom description"
}
```

#### Character Eligibility

**Find Eligible Objects**
```http
GET /api/characters/{id}/eligible-for/
```

Query Parameters:
- `content_type`: Filter by object type (items.item, locations.location, etc.)
- `campaign_id`: Limit to specific campaign
- `include_details`: Include requirement checking details

Response:
```json
{
    "character_id": 123,
    "eligible_objects": [
        {
            "content_type": "items.item",
            "object_id": 456,
            "object_name": "Master's Sword",
            "eligible": true,
            "requirements_met": [
                {
                    "prerequisite_id": 1,
                    "passed": true,
                    "message": "Combat mastery achieved"
                }
            ]
        }
    ]
}
```

### JavaScript Integration

The prerequisite system includes comprehensive JavaScript components for visual requirement building:

#### Drag-Drop Builder

```javascript
// Initialize drag-drop builder
const builder = new PrerequisiteBuilder({
    container: '#requirement-builder',
    initialData: existingRequirements,
    onChange: (requirements) => {
        // Handle requirement changes
        console.log('New requirements:', requirements);
    }
});

// Get current requirements
const currentRequirements = builder.getRequirements();

// Validate requirements
const isValid = builder.validateRequirements();

// Reset builder
builder.reset();
```

#### Visual Widget Integration

```javascript
// Initialize visual widget for forms
const widget = new PrerequisiteWidget({
    fieldName: 'requirements',
    initialValue: existingData,
    placeholder: 'Build your requirements...'
});

// Integrate with Django forms
widget.attachToField('id_requirements');
```

### Admin Interface Integration

The prerequisite system provides comprehensive admin interface support:

#### Admin Widget Integration

```python
from prerequisites.widgets import PrerequisiteBuilderWidget

class MyModelAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.JSONField: {'widget': PrerequisiteBuilderWidget}
    }
```

#### Bulk Operations

The admin interface supports several bulk operations:
- Copy prerequisites to multiple objects
- Bulk validation against character sets
- Template application across objects
- Export/import for requirement backup

### Error Handling

The prerequisite system follows GMA's standard error handling patterns:

**Validation Errors (400)**
```json
{
    "error": "Invalid requirement structure",
    "details": {
        "requirements": [
            "Missing required field: 'name' in trait requirement"
        ]
    }
}
```

**Permission Errors (404)**
```json
{
    "error": "Prerequisite not found"
}
```

**Character Not Found (404)**
```json
{
    "error": "Character not found"
}
```

### Security Considerations

- **Campaign Scoping**: Prerequisites respect campaign membership boundaries
- **Permission Validation**: Only authorized users can modify requirements
- **Input Sanitization**: All JSON inputs are validated and sanitized
- **XSS Prevention**: Safe rendering in admin interfaces
- **Audit Trail**: Complete logging of requirement checks and modifications

## Scene API

### Scene Management System

The Scene API provides comprehensive scene management capabilities for campaigns, featuring role-based permissions, participant management, and status transition validation. Scenes represent structured gameplay sessions with defined participants and status workflows.

#### Implementation Status

**Database & Models:**
- ✅ **Scene Model**: Fully implemented with status workflow and participant management
- ✅ **Database Indexes**: Optimized for query performance with composite indexes
- ✅ **Custom Manager**: SceneManager with QuerySet methods for efficient data access
- ✅ **Status Validation**: ACTIVE → CLOSED → ARCHIVED workflow with transition validation

**API Implementation:**
- ✅ **REST Endpoints**: Complete CRUD operations with ViewSet architecture
- ✅ **Serializers**: Three-tier serializer architecture (SceneSerializer, SceneDetailSerializer, SceneCreateUpdateSerializer)
- ✅ **Permission Integration**: Role-based access control (OWNER/GM manage, all members view)
- ✅ **Custom Actions**: add_participant, remove_participant, change_status endpoints

**Testing Coverage:**
- ✅ **Comprehensive API Tests**: Endpoint validation, permissions, filtering, and security
- ✅ **Model Tests**: Status transitions, participant management, validation
- ✅ **Permission Tests**: Role-based access control across all endpoints

### Authentication

All Scene API endpoints require authentication. Users must be campaign members to access scenes.

### Scene CRUD Operations

#### List Scenes

**GET** `/api/scenes/`

List scenes in campaigns with filtering, search, and pagination capabilities.

**Query Parameters:**
- `campaign_id` (integer): Filter scenes by campaign ID (supports both 'campaign_id' and 'campaign')
- `status` (string): Filter by scene status (`ACTIVE`, `CLOSED`, `ARCHIVED`)
- `participant_id` (integer): Filter scenes by participant character ID (supports both 'participant_id' and 'participant')
- `search` (string): Search in scene name and description
- `ordering` (string): Sort by `name`, `status`, `created_at`, `updated_at` (prefix with `-` for descending)
- `page` (integer): Page number for pagination
- `page_size` (integer): Items per page (max 100, default 20)

**Request Example:**
```bash
GET /api/scenes/?campaign_id=1&status=ACTIVE&participant_id=5&ordering=-created_at
```

**Success Response (200):**
```json
{
  "count": 15,
  "next": "http://localhost:8080/api/scenes/?campaign_id=1&page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "The Tavern Meeting",
      "description": "Characters meet at the Prancing Pony to discuss their next move",
      "status": "ACTIVE",
      "status_display": "Active",
      "campaign": {
        "id": 1,
        "name": "Lord of the Rings Campaign",
        "slug": "lord-of-rings-campaign"
      },
      "participants": [
        {
          "id": 5,
          "name": "Aragorn",
          "character_type": "Character",
          "npc": false,
          "player_owner": {
            "id": 2,
            "username": "player1"
          }
        },
        {
          "id": 8,
          "name": "Gandalf",
          "character_type": "Character",
          "npc": true,
          "player_owner": {
            "id": 1,
            "username": "gamemaster"
          }
        }
      ],
      "participant_count": 2,
      "created_by": {
        "id": 1,
        "username": "gamemaster",
        "display_name": "Game Master"
      },
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-16T14:20:00Z"
    }
  ]
}
```

**Error Responses:**
- **401 Unauthorized**: Authentication required
- **404 Not Found**: No scenes found (campaign doesn't exist or user lacks access)

#### Create Scene

**POST** `/api/scenes/`

Create a new scene in a campaign (OWNER/GM only).

**Request Body:**
```json
{
  "name": "The Council of Elrond",
  "description": "The characters attend the council to decide the fate of the Ring",
  "campaign": 1,
  "participants": [5, 8, 12],
  "status": "ACTIVE"
}
```

**Required Fields:**
- `name` (string): Scene name (max 200 characters)
- `campaign` (integer): Campaign ID

**Optional Fields:**
- `description` (string): Scene description
- `participants` (array): Array of character IDs to add as participants
- `status` (string): Scene status (defaults to "ACTIVE")

**Success Response (201):**
```json
{
  "id": 15,
  "name": "The Council of Elrond",
  "description": "The characters attend the council to decide the fate of the Ring",
  "status": "ACTIVE",
  "status_display": "Active",
  "campaign": {
    "id": 1,
    "name": "Lord of the Rings Campaign",
    "slug": "lord-of-rings-campaign"
  },
  "participants": [
    {
      "id": 5,
      "name": "Aragorn",
      "character_type": "Character",
      "npc": false,
      "player_owner": {
        "id": 2,
        "username": "player1"
      }
    }
  ],
  "participant_count": 3,
  "created_by": {
    "id": 1,
    "username": "gamemaster",
    "display_name": "Game Master"
  },
  "created_at": "2024-01-17T15:30:00Z",
  "updated_at": "2024-01-17T15:30:00Z"
}
```

**Error Responses:**
- **400 Bad Request**: Validation errors in request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Only OWNER/GM can create scenes
- **404 Not Found**: Campaign doesn't exist or user lacks access

#### Get Scene Details

**GET** `/api/scenes/{id}/`

Retrieve detailed information about a specific scene.

**Success Response (200):**
```json
{
  "id": 1,
  "name": "The Tavern Meeting",
  "description": "Characters meet at the Prancing Pony to discuss their next move",
  "status": "ACTIVE",
  "status_display": "Active",
  "campaign": {
    "id": 1,
    "name": "Lord of the Rings Campaign",
    "slug": "lord-of-rings-campaign"
  },
  "participants": [
    {
      "id": 5,
      "name": "Aragorn",
      "character_type": "Character",
      "npc": false,
      "player_owner": {
        "id": 2,
        "username": "player1"
      }
    }
  ],
  "participant_count": 1,
  "created_by": {
    "id": 1,
    "username": "gamemaster",
    "display_name": "Game Master"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-16T14:20:00Z",
  "can_manage": true,
  "can_participate": true
}
```

**Additional Fields (SceneDetailSerializer):**
- `can_manage` (boolean): Whether current user can manage this scene (OWNER/GM)
- `can_participate` (boolean): Whether current user can participate (all members)

**Error Responses:**
- **401 Unauthorized**: Authentication required
- **404 Not Found**: Scene doesn't exist or user lacks access

#### Update Scene

**PUT/PATCH** `/api/scenes/{id}/`

Update an existing scene (OWNER/GM only).

**Request Body:**
```json
{
  "name": "Updated Scene Name",
  "description": "Updated description",
  "participants": [5, 8],
  "status": "CLOSED"
}
```

**Note:** The `campaign` field is read-only for updates.

**Success Response (200):**
```json
{
  "id": 1,
  "name": "Updated Scene Name",
  "description": "Updated description",
  "status": "CLOSED",
  "status_display": "Closed",
  "campaign": {
    "id": 1,
    "name": "Lord of the Rings Campaign",
    "slug": "lord-of-rings-campaign"
  },
  "participants": [
    {
      "id": 5,
      "name": "Aragorn",
      "character_type": "Character",
      "npc": false,
      "player_owner": {
        "id": 2,
        "username": "player1"
      }
    }
  ],
  "participant_count": 2,
  "created_by": {
    "id": 1,
    "username": "gamemaster",
    "display_name": "Game Master"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-17T16:45:00Z"
}
```

**Error Responses:**
- **400 Bad Request**: Validation errors (including invalid status transitions)
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Only OWNER/GM can update scenes
- **404 Not Found**: Scene doesn't exist or user lacks access

#### Delete Scene

**DELETE** `/api/scenes/{id}/`

Delete a scene (OWNER/GM only).

**Success Response (204):**
No content returned.

**Error Responses:**
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Only OWNER/GM can delete scenes
- **404 Not Found**: Scene doesn't exist or user lacks access

### Scene Participant Management

#### Add Participant

**POST** `/api/scenes/{id}/add_participant/`

Add a character to the scene as a participant.

**Request Body:**
```json
{
  "character_id": 5
}
```

**Permission Rules:**
- **OWNER/GM**: Can add any character from the campaign
- **PLAYER/OBSERVER**: Can only add their own characters

**Success Response (200):**
```json
{
  "detail": "Aragorn added to scene.",
  "character": {
    "id": 5,
    "name": "Aragorn",
    "npc": false,
    "player_owner": {
      "id": 2,
      "username": "player1"
    }
  }
}
```

**Error Responses:**
- **400 Bad Request**: Character ID missing, character already participating, or validation errors
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: User lacks permission to add this character
- **404 Not Found**: Scene or character doesn't exist, or user lacks access

#### Remove Participant

**DELETE** `/api/scenes/{id}/participants/{character_id}/`

Remove a character from scene participation.

**Permission Rules:**
- **OWNER/GM**: Can remove any participant
- **PLAYER/OBSERVER**: Can only remove their own characters

**Success Response (200):**
```json
{
  "detail": "Aragorn removed from scene.",
  "character_id": 5
}
```

**Error Responses:**
- **400 Bad Request**: Character not participating in scene
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: User lacks permission to remove this character
- **404 Not Found**: Scene or character doesn't exist, or user lacks access

### Scene Status Management

#### Change Status

**POST** `/api/scenes/{id}/change_status/`

Change the scene's status with validation (OWNER/GM only).

**Request Body:**
```json
{
  "status": "CLOSED"
}
```

**Status Workflow:**
- **ACTIVE** → **CLOSED**: Close an active scene
- **CLOSED** → **ARCHIVED**: Archive a closed scene
- **ARCHIVED**: Terminal status, cannot be changed

**Invalid Transitions:**
- ACTIVE → ARCHIVED (must close first)
- CLOSED → ACTIVE (cannot reactivate)
- ARCHIVED → Any (terminal state)

**Success Response (200):**
```json
{
  "detail": "Scene status changed to Closed.",
  "status": "CLOSED",
  "status_display": "Closed"
}
```

**Status Unchanged Response (200):**
```json
{
  "detail": "Status unchanged.",
  "status": "ACTIVE",
  "status_display": "Active"
}
```

**Error Responses:**
- **400 Bad Request**: Invalid status or transition
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Only OWNER/GM can change status
- **404 Not Found**: Scene doesn't exist or user lacks access

### Permission System

Scenes inherit the campaign permission structure with role-based access control:

#### Permission Hierarchy
- **OWNER**: Full access to all campaign scenes
- **GM**: Full access to all campaign scenes
- **PLAYER**: Can view scenes, manage own character participation
- **OBSERVER**: Can view scenes, manage own character participation

#### Permission Rules
- Users can only access scenes in campaigns they are members of
- Scene creation/editing/deletion restricted to OWNER/GM roles
- All campaign members can participate in scenes and manage their own character participation
- Status changes restricted to OWNER/GM roles

#### Security Features
- Returns 404 instead of 403 to hide resource existence from non-members
- Campaign membership validation prevents unauthorized access
- Character ownership validation for participant management
- Status transition validation prevents invalid workflow states

### Query Optimization

The Scene API includes several performance optimizations:

#### Database Optimizations
- **Composite Indexes**: campaign + created_at, campaign + status, status + created_at
- **Select Related**: Optimized loading of campaign and created_by relationships
- **Prefetch Related**: Efficient loading of participants with their player_owner data
- **Custom QuerySet**: SceneQuerySet with optimized methods for common access patterns

#### API Optimizations
- **Pagination**: Configurable page sizes with sensible defaults (20 items, max 100)
- **Field Selection**: Different serializers for list vs detail views
- **Query Efficiency**: Minimized database queries through strategic prefetching
- **Participant Count**: Uses prefetched data when available to avoid additional queries

### Common Use Cases

#### Campaign Scene Management
```bash
# List all active scenes in a campaign
GET /api/scenes/?campaign_id=1&status=ACTIVE

# Find scenes with specific participant
GET /api/scenes/?campaign_id=1&participant_id=5

# Search scenes by content
GET /api/scenes/?search=tavern
```

#### Scene Workflow Management
```bash
# Create new active scene
POST /api/scenes/
{
  "name": "New Adventure",
  "campaign": 1,
  "participants": [5, 8]
}

# Close active scene
POST /api/scenes/15/change_status/
{
  "status": "CLOSED"
}

# Archive closed scene
POST /api/scenes/15/change_status/
{
  "status": "ARCHIVED"
}
```

#### Participant Management
```bash
# Add character to scene
POST /api/scenes/15/add_participant/
{
  "character_id": 12
}

# Remove character from scene
DELETE /api/scenes/15/participants/12/
```

### Scene Message History API

#### Get Message History

**GET** `/api/scenes/{id}/messages/`

Retrieve message history for a scene with advanced filtering, pagination, and permission-based visibility.

**Path Parameters:**
- `id` (integer): Scene ID

**Query Parameters:**
- `message_type` (string): Filter by message type(s) - supports single type or comma-separated list (`PUBLIC`, `OOC`, `PRIVATE`, `SYSTEM`)
- `type` (string): Alias for `message_type` parameter
- `character_id` (integer): Filter messages by character
- `sender_id` (integer): Filter messages by sender user
- `search` (string): Search message content (case-insensitive)
- `since` (ISO datetime): Messages after this timestamp
- `until` (ISO datetime): Messages before this timestamp
- `page` (integer): Page number for pagination
- `page_size` (integer): Items per page (max 100, default 20)

**Permission-Based Filtering:**
- **Campaign Owners/GMs**: Can see all message types including private messages
- **Players/Observers**: Can see PUBLIC, OOC, SYSTEM messages, and private messages where they are sender or recipient

**Request Examples:**
```bash
# Get recent public messages
GET /api/scenes/15/messages/?message_type=PUBLIC&page=1&page_size=50

# Search for specific content
GET /api/scenes/15/messages/?search=dragon&message_type=PUBLIC,OOC

# Get messages from specific character
GET /api/scenes/15/messages/?character_id=23&since=2024-01-15T10:00:00Z

# Get multiple message types with date range
GET /api/scenes/15/messages/?type=PUBLIC,PRIVATE&until=2024-01-20T18:00:00Z
```

**Success Response (200):**
```json
{
  "count": 156,
  "next": "http://localhost:8080/api/scenes/15/messages/?page=2",
  "previous": null,
  "results": [
    {
      "id": 89,
      "content": "I cast *Fireball* at the approaching enemies!",
      "message_type": "PUBLIC",
      "created_at": "2024-01-15T14:30:25.123456Z",
      "character": {
        "id": 23,
        "name": "Gandalf the Grey",
        "npc": false
      },
      "sender": {
        "id": 5,
        "username": "playerone",
        "display_name": "Player One"
      },
      "recipients": [],
      "scene": {
        "id": 15,
        "name": "Battle at Helm's Deep",
        "status": "ACTIVE"
      }
    },
    {
      "id": 88,
      "content": "((Rolling initiative...))",
      "message_type": "OOC",
      "created_at": "2024-01-15T14:29:10.654321Z",
      "character": null,
      "sender": {
        "id": 1,
        "username": "gamemaster",
        "display_name": "GM"
      },
      "recipients": [],
      "scene": {
        "id": 15,
        "name": "Battle at Helm's Deep",
        "status": "ACTIVE"
      }
    },
    {
      "id": 87,
      "content": "Secret plan discussed with Aragorn",
      "message_type": "PRIVATE",
      "created_at": "2024-01-15T14:25:45.987654Z",
      "character": {
        "id": 23,
        "name": "Gandalf the Grey",
        "npc": false
      },
      "sender": {
        "id": 5,
        "username": "playerone",
        "display_name": "Player One"
      },
      "recipients": [
        {
          "id": 7,
          "username": "playertwo",
          "display_name": "Player Two"
        }
      ],
      "scene": {
        "id": 15,
        "name": "Battle at Helm's Deep",
        "status": "ACTIVE"
      }
    }
  ]
}
```

**Error Responses:**

**401 Unauthorized:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**404 Not Found:**
```json
{
  "detail": "Scene not found."
}
```

**Message Type Reference:**
- **PUBLIC**: In-character messages requiring character attribution
- **OOC**: Out-of-character messages from players (no character required)
- **PRIVATE**: Private messages between specific users with recipient list
- **SYSTEM**: GM/Owner-only system messages for game mechanics

### WebSocket Chat API

The real-time chat system uses WebSocket connections for live message broadcasting.

**WebSocket Endpoint:**
```
ws://localhost:8080/ws/scenes/{scene_id}/chat/
```

**Authentication:** Required - users must be authenticated and have scene access

**Message Format:**

**Send Message:**
```json
{
  "type": "chat_message",
  "message": {
    "content": "Hello, adventurers!",
    "message_type": "PUBLIC",
    "character": 23,
    "recipients": []  // For PRIVATE messages only
  }
}
```

**Receive Message:**
```json
{
  "type": "chat.message",
  "message_type": "PUBLIC",
  "content": "Hello, adventurers!",
  "character": {
    "id": 23,
    "name": "Gandalf the Grey"
  },
  "sender": {
    "id": 5,
    "username": "playerone"
  },
  "recipients": [],
  "timestamp": "2024-01-15T14:30:25.123456Z",
  "id": 89
}
```

**Rate Limiting:**
- **Default Users**: 10 messages per minute
- **Staff Users**: 30 messages per minute
- **System Messages**: 100 messages per minute

**Error Handling:**
```json
{
  "type": "error",
  "error": "Rate limit exceeded. Try again in 45 seconds."
}
```

**Heartbeat (Connection Health):**
```json
// Send
{
  "type": "heartbeat"
}

// Receive
{
  "type": "heartbeat_response"
}
```

## Source Reference API

### Book and SourceReference Models

The system includes comprehensive source reference capabilities through two related models: `Book` for tracking RPG source books, and `SourceReference` for linking any model to books with page and chapter details.

#### Book Model

**Database Implementation:**
- ✅ **Model**: Fully implemented with validation and test coverage
- ✅ **Database Schema**: Optimized with indexes and constraints
- ✅ **Test Coverage**: 25 comprehensive tests covering all features
- ❌ **API Endpoints**: Not yet implemented
- ❌ **Admin Interface**: Not yet configured

**Future API Endpoints:**
- `GET /api/books/` - List RPG source books with filtering
- `GET /api/books/{id}/` - Get detailed book information
- `POST /api/books/` - Create new book reference (admin only)
- `PUT /api/books/{id}/` - Update book information (admin only)
- `DELETE /api/books/{id}/` - Remove book reference (admin only)
- `GET /api/books/{id}/references/` - Get all source references for a book

**Book Model Structure:**
```json
{
  "id": 1,
  "title": "Mage: The Ascension 20th Anniversary Edition",
  "abbreviation": "M20",
  "system": "Mage: The Ascension",
  "edition": "20th Anniversary",
  "publisher": "Onyx Path Publishing",
  "isbn": "978-1-58846-475-3",
  "url": "https://www.drivethrurpg.com/product/149562/Mage-the-Ascension-20th-Anniversary-Edition",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### SourceReference Model

**Database Implementation:**
- ✅ **Model**: Fully implemented with GenericForeignKey support
- ✅ **Database Schema**: Performance-optimized with compound indexes
- ✅ **Test Coverage**: 50 comprehensive tests covering all scenarios
- ❌ **API Endpoints**: Not yet implemented
- ❌ **Admin Interface**: Not yet configured

**Future API Endpoints:**
- `GET /api/source-references/` - List source references with filtering
- `GET /api/source-references/{id}/` - Get specific source reference
- `POST /api/source-references/` - Create new source reference
- `PUT /api/source-references/{id}/` - Update source reference
- `DELETE /api/source-references/{id}/` - Remove source reference
- `GET /api/{model}/{id}/sources/` - Get all source references for any object

**SourceReference Model Structure:**
```json
{
  "id": 1,
  "book": {
    "id": 1,
    "title": "Mage: The Ascension 20th Anniversary Edition",
    "abbreviation": "M20",
    "system": "Mage: The Ascension"
  },
  "content_type": "characters.character",
  "object_id": 42,
  "content_object": {
    "id": 42,
    "name": "Alexis the Technomancer",
    "type": "MageCharacter"
  },
  "page_number": 65,
  "chapter": "Character Creation",
  "created_at": "2024-01-15T14:22:00Z",
  "updated_at": "2024-01-15T14:22:00Z"
}
```

**Query Parameters (Future Implementation):**

Books API:
- `system` - Filter by game system
- `search` - Search title and abbreviation
- `publisher` - Filter by publisher
- `ordering` - Sort by `system`, `title`, `abbreviation`, `created_at`

Source References API:
- `book` - Filter by book ID
- `book__system` - Filter by book's game system
- `content_type` - Filter by content type
- `page_number` - Filter by page number range
- `chapter` - Search chapter names
- `ordering` - Sort by `book__abbreviation`, `page_number`, `created_at`

**Future Integration Patterns:**

```json
// Character with source references
{
  "id": 42,
  "name": "Alexis the Technomancer",
  "source_references": [
    {
      "book": "M20",
      "page_number": 65,
      "chapter": "Character Creation"
    },
    {
      "book": "M20",
      "page_number": 205,
      "chapter": "Forces Sphere"
    }
  ]
}

// Equipment with source attribution
{
  "id": 15,
  "name": "Wand of Fireballs",
  "source_references": [
    {
      "book": "M20",
      "page_number": 384,
      "chapter": "Wonders and Talismans"
    }
  ]
}

// Spell with multiple sources
{
  "id": 8,
  "name": "Mind Reading",
  "source_references": [
    {
      "book": "M20",
      "page_number": 520,
      "chapter": "Mind Sphere"
    },
    {
      "book": "MIND",
      "page_number": 78,
      "chapter": "Advanced Techniques"
    }
  ]
}
```

**Implementation Status:**
- ✅ **Database Models**: Both models fully implemented with comprehensive validation
- ✅ **Test Coverage**: 75 total tests covering all features and edge cases
- ✅ **Performance Optimization**: Database indexes for efficient queries
- ✅ **Data Integrity**: Proper foreign keys and cascade deletion
- ❌ **API Endpoints**: Awaiting API implementation
- ❌ **Admin Interface**: Awaiting admin configuration
- ❌ **Frontend Integration**: Depends on API implementation

**Development Notes:**

When implementing source reference API endpoints:
- **Security**: Read-only access for most users, admin-only modification
- **Performance**: Use `select_related()` and `prefetch_related()` for efficient queries
- **Filtering**: Support complex filtering by book, content type, and page ranges
- **Validation**: Ensure positive page numbers and valid content type relationships
- **Integration**: Provide helper endpoints for adding sources to existing objects

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

### Character Model

**Core Fields:**
- `id`: Integer, primary key
- `name`: String (max 100 chars), unique per campaign
- `description`: Text, optional character background
- `game_system`: String, inherited from campaign
- `npc`: Boolean, character type flag
  - `false`: Player Character (PC) - controlled by players
  - `true`: Non-Player Character (NPC) - controlled by GMs
- `status`: String, character workflow status
  - `DRAFT`: Initial creation state
  - `SUBMITTED`: Awaiting approval
  - `APPROVED`: Approved for campaign play
  - `INACTIVE`: Temporarily inactive
  - `RETIRED`: Permanently retired
  - `DECEASED`: Marked as deceased
- `created_at`: Timestamp, character creation time
- `updated_at`: Timestamp, last modification time

**Relationships:**
- `campaign`: Foreign key to Campaign model
- `player_owner`: Foreign key to User model (character controller)
- `created_by`: Foreign key to User model (audit trail)
- `modified_by`: Foreign key to User model (audit trail)
- `owned_locations`: Reverse relationship to Location model (Issue #186)
  - Returns all locations owned by this character
  - Supports both PC and NPC ownership
  - Automatically filters to same campaign as character

**Polymorphic Fields (game-system specific):**
- `character_type`: String, polymorphic type identifier
  - `"Character"`: Base character
  - `"WoDCharacter"`: World of Darkness character
  - `"MageCharacter"`: Mage: The Ascension character

**World of Darkness Characters (WoDCharacter):**
- `willpower`: Integer (1-10), character's willpower rating

**Mage Characters (MageCharacter):**
- `arete`: Integer (1-10), mage's Arete rating
- `quintessence`: Integer (0+), current quintessence points
- `paradox`: Integer (0+), current paradox points

**Soft Delete Fields:**
- `is_deleted`: Boolean, soft delete flag
- `deleted_at`: Timestamp, deletion time (null if active)
- `deleted_by`: Foreign key to User, who deleted the character

**Manager Instances (New in #175):**
- `Character.objects`: Primary manager (excludes soft-deleted characters)
- `Character.all_objects`: Includes soft-deleted characters
- `Character.npcs`: Only NPCs, excludes soft-deleted
- `Character.pcs`: Only PCs, excludes soft-deleted

**Manager Benefits:**
- Automatic filtering reduces query complexity
- Performance optimized with database indexes
- Full polymorphic inheritance support
- Backward compatibility preserved

**Business Rules:**
- Character names must be unique within a campaign
- Player must be campaign member to own characters
- NPC creation limited to GMs and campaign owners
- Character limits apply only to PCs, not NPCs
- **Status Workflow Rules:**
  - Characters start in DRAFT status
  - Only character owners can submit for approval
  - Only GMs/owners can approve, reject, deactivate, or mark deceased
  - Character owners can retire their own characters
  - GMs/owners can retire any character
  - RETIRED and DECEASED are terminal states
- Audit trail tracks all character changes including status transitions
- Manager-level filtering automatically excludes soft-deleted characters

**Status Transition Matrix:**
```
DRAFT      → SUBMITTED (character owners)
SUBMITTED  → APPROVED (GMs/owners) | DRAFT (GMs/owners - rejection)
APPROVED   → INACTIVE (GMs/owners) | RETIRED (owners + GMs/owners) | DECEASED (GMs/owners)
INACTIVE   → APPROVED (GMs/owners)
RETIRED    → No transitions (terminal)
DECEASED   → No transitions (terminal)
```

### Character Status Choices

```python
STATUS_CHOICES = [
    ('DRAFT', 'Draft'),
    ('SUBMITTED', 'Submitted'),
    ('APPROVED', 'Approved'),
    ('INACTIVE', 'Inactive'),
    ('RETIRED', 'Retired'),
    ('DECEASED', 'Deceased')
]
```

### Character Status Lifecycle

1. **DRAFT** - Character in creation/editing phase
2. **SUBMITTED** - Character submitted for GM approval
3. **APPROVED** - Character approved for campaign play
4. **INACTIVE** - Character temporarily unavailable
5. **RETIRED** - Character permanently retired from campaign
6. **DECEASED** - Character marked as deceased

### Location Model (Issue #186)

**Core Fields:**
- `id`: Integer, primary key
- `name`: String (max 100 chars), location name
- `description`: Text, optional location description
- `created_at`: Timestamp, location creation time
- `updated_at`: Timestamp, last modification time

**Relationships:**
- `campaign`: Foreign key to Campaign model
- `parent`: Foreign key to self (for hierarchy support)
- `children`: Reverse relationship to child locations (related_name: "children")
- `owned_by`: Foreign key to Character model (Issue #186)
- `created_by`: Foreign key to User model (audit trail)
- `modified_by`: Foreign key to User model (audit trail)

**Character Ownership Features:**

- `owned_by`: Foreign key to Character model, optional
  - `null=True`: Locations can be unowned
  - `on_delete=SET_NULL`: Ownership cleared when character deleted
  - `related_name="owned_locations"`: Reverse relationship on Character
- `owner_display`: Property returning formatted ownership string
  - Format: "Character Name (PC|NPC)" or "Unowned"

**Hierarchy Support:**

- `parent`: Self-referential foreign key for location hierarchy
- `sub_locations`: Alias property for `children` relationship
- Maximum depth validation (10 levels)
- Circular reference prevention
- Orphan handling on parent deletion

**Business Rules:**

- Location names must be unique within a campaign
- Characters can only own locations within their own campaign
- Location hierarchy limited to 10 levels deep
- Parent location must be in same campaign
- Ownership affects permission system (edit/delete rights)

**Permission Integration:**

- All campaign members can view locations
- Campaign members can create locations
- Owners/GMs can edit all locations
- Players can edit their own created locations + character-owned locations
- Same rules apply for deletion permissions

**Validation Rules:**

- Cross-campaign ownership validation
- Circular reference prevention in hierarchy
- Maximum depth enforcement
- Self-parent prevention

### Book Model

**Core Fields:**
- `id`: Integer, primary key
- `title`: String (max 200 chars), unique book title
- `abbreviation`: String (max 20 chars), unique short reference
- `system`: String (max 100 chars), game system identifier
- `edition`: String (max 50 chars), optional edition information
- `publisher`: String (max 100 chars), optional publisher name
- `isbn`: String (max 17 chars), optional ISBN-10 or ISBN-13
- `url`: URLField, optional purchase or information URL

**Business Rules:**
- Book titles must be unique across all systems
- Abbreviations must be unique across all systems
- System field is required for categorization
- Optional fields default to empty string
- Ordering by system, then title

**Usage Examples:**
- **Title**: "Mage: The Ascension 20th Anniversary Edition"
- **Abbreviation**: "M20"
- **System**: "Mage: The Ascension"
- **Edition**: "20th Anniversary"
- **Publisher**: "Onyx Path Publishing"
- **ISBN**: "978-1-58846-475-3"
- **URL**: "https://www.drivethrurpg.com/product/149562/..."

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

*This API reference should be updated as new endpoints are added. Last updated: 2025-08-24*
