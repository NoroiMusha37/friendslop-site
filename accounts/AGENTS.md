# accounts

## Purpose

Users, roles and statuses, JWT auth endpoints (`/api/v1/auth/...`), admin user management (`/api/v1/users/`) and the permission classes every app uses.

## Ownership

- `models.py`: custom `User`; admin = `is_superuser`, pending = `approved_at` is null, banned = approved but inactive
- `services.py`: approve / reject / ban / unban, the only place user status changes; each takes the acting admin (`by`) and logs the change
- `views.py`, `urls.py`, `serializers.py`, `filters.py`: auth and user management endpoints
- `throttling.py`: `LoggedScopedRateThrottle`, DRF's rate limit that logs every refused request
- `permissions.py`: `IsAdmin`, `IsAdminOrReadOnly`, `IsRegularUser`, `IsAuthorOrAdmin`
- `admin.py`: Django admin page with the same status actions

## Local Contracts

- Admin means `is_superuser`. DRF's `IsAdminUser` checks `is_staff`, so other apps use the classes in `permissions.py`
- Status changes go through `services.py`, shared by the API and the Django admin actions, so both follow the same rules
- Admins can't be banned or deleted (API and Django admin)
- Login and sign-up are rate limited per client address (`DEFAULT_THROTTLE_RATES` in settings); refused requests and failed logins are logged with the client address

## Work Guidance

## Verification

- `docker compose run --rm web pytest accounts`

## Child DOX Index

None.
