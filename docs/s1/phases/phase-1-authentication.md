# Phase 1 — Authentication and Platform Stability

## Files changed

- `src/lib/api.ts`: single-flight refresh-token rotation and recoverable network behavior
- `src/stores/auth.ts`: atomic email, signup, Google, and logout state transitions
- `backend/app/services/auth_service.py`: active-user validation during refresh
- `backend/tests/test_auth_foundation.py`: active/inactive refresh coverage
- `android/app/build.gradle`, `android/app/src/main/java/com/synzept/app/MainActivity.java`: secure custom-tab mobile session with browser fallback

## APIs

No new API was required. The existing contracts remain canonical:

- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/google`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- authenticated `/api/billing/*`

## Verification

- Email signup/login and password hashing
- Google token verification, new-user creation, and existing-email linking
- Refresh rotation, naive UTC expiry, inactive-user rejection, and concurrent client refresh collapse
- Logout revocation and local cleanup
- Missing/invalid bearer rejection
- Authenticated billing boundary
- Android release compilation and mobile entry routing
- Web production build and responsive login route

Live Google popup and live Razorpay checkout require the production OAuth origin/client ID and payment credentials. Run those final smoke checks after deploying the same commit to staging.

## Deployment

Deploy backend first, then web, then the Android internal track. No database migration is required. Configure matching `GOOGLE_CLIENT_ID` and `NEXT_PUBLIC_GOOGLE_CLIENT_ID`, production CORS origin, JWT secret, Razorpay credentials, and the existing Android signing key.

## Remaining tasks

- Execute one live Google login against the configured production OAuth client.
- Execute one live Razorpay test/live-mode transaction in the intended environment.
- Move refresh tokens to server-set HttpOnly cookies in a future security release; current storage remains backward compatible for web and the Android browser session.
