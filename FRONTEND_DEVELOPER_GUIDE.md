# iTalkVoIP Frontend Developer Guide

## Overview

This backend is a Django + Django REST Framework application that serves:

- User registration and OTP verification
- User login via OTP
- Token refresh and logout
- Domain discovery
- Domain selection and SIP extension provisioning
- Admin authentication
- Admin reporting and domain management

Base URLs:

- API: `http://localhost:3000/api/v1`
- Django Admin: `http://localhost:3000/admin/`

All API payloads are JSON unless noted otherwise.

## Authentication Model

There are two application roles:

- `USER`
- `ADMIN`

The API uses bearer access tokens for protected requests:

```http
Authorization: Bearer <accessToken>
```

The backend returns both:

- `accessToken`
- `refreshToken`

Recommended frontend handling:

1. Store the access token in memory when possible.
2. Treat the refresh token as sensitive and store it carefully.
3. On `401` during an authenticated request, attempt `POST /auth/refresh`.
4. If refresh fails, force sign-out and redirect to the appropriate login screen.

## User Authentication Flow

### 1. Register

Endpoint:

- `POST /auth/register`

Request body:

```json
{
  "email": "user@example.com"
}
```

Success response:

```json
{
  "message": "OTP sent to email",
  "email": "user@example.com",
  "expiresInMinutes": 10
}
```

### 2. Resend Registration OTP

Endpoint:

- `POST /auth/register/resend-otp`

Request body:

```json
{
  "email": "user@example.com"
}
```

### 3. Verify Registration OTP

Endpoint:

- `POST /auth/verify-registration`

Request body:

```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

Success response includes tokens:

```json
{
  "message": "Email verified successfully",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "isVerified": true
  },
  "tokens": {
    "accessToken": "jwt",
    "refreshToken": "token",
    "session": {
      "id": "uuid",
      "expiresAt": "timestamp"
    }
  }
}
```

## Login Flow

### 1. Request Login OTP

Endpoint:

- `POST /auth/login/request-otp`

Request body:

```json
{
  "email": "user@example.com"
}
```

### 2. Resend Login OTP

Endpoint:

- `POST /auth/login/resend-otp`

Request body:

```json
{
  "email": "user@example.com"
}
```

### 3. Verify Login OTP

Endpoint:

- `POST /auth/login/verify-otp`

Request body:

```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

Response shape mirrors registration verification and returns tokens.

## Session Management

### Refresh Access Token

Endpoint:

- `POST /auth/refresh`

Request body:

```json
{
  "refreshToken": "your-refresh-token"
}
```

### Logout

Endpoint:

- `POST /auth/logout`

Request body:

```json
{
  "refreshToken": "your-refresh-token"
}
```

## User Domain and Extension APIs

### List Active Domains

Endpoint:

- `GET /domains`

No auth required.

Example response:

```json
{
  "data": [
    {
      "id": "uuid",
      "identifier": "us-east",
      "label": "US East"
    }
  ]
}
```

### Select Domain and Provision Extension

Endpoint:

- `POST /onboarding/domain`

Headers:

```http
Authorization: Bearer <accessToken>
```

Request body:

```json
{
  "domainId": "uuid-of-domain"
}
```

Example response:

```json
{
  "domain": {
    "id": "uuid",
    "identifier": "us-east",
    "label": "US East"
  },
  "extension": {
    "number": 1000,
    "password": "generated-password"
  },
  "alreadyProvisioned": false
}
```

### Get Provisioned Extension

Endpoint:

- `GET /onboarding/extension`

Headers:

```http
Authorization: Bearer <accessToken>
```

## Admin APIs

### Admin Login

Endpoint:

- `POST /auth/admin/login`

Request body:

```json
{
  "email": "eritten@niveel.com",
  "password": "1234"
}
```

Success response:

```json
{
  "message": "Admin login successful",
  "admin": {
    "id": "uuid",
    "email": "eritten@niveel.com"
  },
  "tokens": {
    "accessToken": "jwt",
    "refreshToken": "token",
    "session": {
      "id": "uuid",
      "expiresAt": "timestamp"
    }
  }
}
```

### Admin Dashboard

- `GET /admin/dashboard`

Returns aggregate counts:

- users
- domains
- provisionedExtensions

### Admin Domains

- `GET /admin/domains`
- `POST /admin/domains`
- `PATCH /admin/domains/<domain_id>`

Create domain body:

```json
{
  "identifier": "eu-west",
  "label": "EU West",
  "extensionStart": 1000
}
```

Patch body fields are optional:

```json
{
  "label": "EU West Updated",
  "isActive": true,
  "extensionStart": 2000
}
```

### Admin Users

- `GET /admin/users`

## Frontend Integration Notes

Recommended screens:

- Registration
- Registration OTP verification
- Login request OTP
- Login OTP verification
- Domain selection
- Extension details
- Admin login
- Admin dashboard
- Admin domains
- Admin users

Recommended UX behavior:

- Disable submit buttons during requests.
- Show countdown timers for OTP expiration and resend states.
- Normalize email input to lowercase before submit.
- Preserve the email value between OTP request and OTP verification screens.
- Handle `401`, `403`, and `404` with explicit user-friendly messages.

## Error Handling Expectations

Typical API failure classes:

- `400` validation problems
- `401` invalid credentials or invalid token
- `403` permission or verification issues
- `404` missing user, domain, or extension
- `409` conflict conditions such as invalid account type

Frontend recommendation:

- Show field-level errors when validation details are present.
- Fall back to a generic toast or alert using `detail` or `message`.

## Suggested Frontend API Layer

Create a single API client wrapper that:

- Applies the base URL
- Sends JSON headers
- Injects bearer tokens automatically
- Retries once on refresh flow when appropriate
- Centralizes parsing of API errors

## Local Development Notes

- Local API base URL: `http://localhost:3000/api/v1`
- Local Django admin: `http://localhost:3000/admin/`
- Current admin account:
  - Email: `eritten@niveel.com`
  - Password: `1234`

## Release Checklist for Frontend

- Confirm auth flows against real API responses
- Verify resend OTP states
- Verify refresh token flow
- Verify domain provisioning success and already-provisioned response
- Verify admin role separation from user flows
- Verify loading, empty, and error states for admin lists
