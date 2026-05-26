# Authentication

Synzept auth is implemented as a single email/password JWT system with refresh-token rotation.

## Ownership

| Responsibility | Location |
|---|---|
| Routes | `backend/app/api/v1/auth.py` |
| Auth service | `backend/app/services/auth_service.py` |
| Password/JWT utilities | `backend/app/core/security.py` |
| Current user dependency | `backend/app/core/dependencies.py` |
| User model | `backend/app/models/user.py` |
| Profile model | `backend/app/models/user_profile.py` |
| Refresh token model | `backend/app/models/refresh_token.py` |
| Schemas | `backend/app/schemas/auth.py` |

## Flow

### Signup

```text
POST /api/v1/auth/signup
  -> validate email/password schema
  -> check duplicate email
  -> hash password with passlib/bcrypt
  -> create users row
  -> create user_profiles row
  -> create access token
  -> create refresh token
  -> store refresh token hash
```

### Login

```text
POST /api/v1/auth/login
  -> find active user by email
  -> verify password hash
  -> create access token
  -> create refresh token
  -> store refresh token hash
```

### Refresh

```text
POST /api/v1/auth/refresh-token
  -> decode refresh JWT
  -> find non-revoked stored token hash
  -> revoke existing refresh token
  -> issue new token pair
```

`/api/v1/auth/refresh` remains available for backward compatibility.

### Protected Routes

```text
Authorization: Bearer <access_token>
  -> decode JWT
  -> require token type access
  -> load active non-deleted user
  -> inject User into route
```

## Security Notes

- Plain passwords are never stored.
- Refresh tokens are stored as SHA-256 hashes.
- Refresh tokens rotate on use.
- Production rejects the development JWT secret.
- `get_current_user` rejects missing, invalid, expired, inactive, or deleted users.

## Current Limitations

- Email verification field exists but verification email flow is not implemented.
- Google OAuth code exists from earlier implementation but is not part of this V1 auth foundation task.
- MFA, permissions, teams, and enterprise auth are out of scope for V1 foundation.
