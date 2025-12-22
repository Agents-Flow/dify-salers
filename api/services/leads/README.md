# Social Media Automation Services

This module provides high-concurrency social media automation services for Instagram and Twitter/X platforms.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Layer 1: Third-party API Services       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Apify      │  │  RapidAPI    │  │ SocialData   │       │
│  │ (Scraping)   │  │ (X/IG API)   │  │  (Backup)    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                  Layer 2: HTTP API Direct Layer             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  instagrapi (Instagram)  │  twikit (X/Twitter)       │   │
│  │  - Mobile API simulation │  - Web/Mobile API         │   │
│  │  - No browser required   │  - No browser required    │   │
│  │  - Follow/DM/Like        │  - Follow/DM/Like         │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│               Layer 3: Lightweight Browser Pool             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  10-20 browser instances (Playwright)                │   │
│  │  - Initial login only                                │   │
│  │  - CAPTCHA handling                                  │   │
│  │  - Cookie extraction                                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Memory Comparison

| Approach | Memory per Account | 1000 Accounts | Feasibility |
|----------|-------------------|---------------|-------------|
| Browser (Playwright) | 300-500MB | **300-500GB** | ❌ Not feasible |
| HTTP API (instagrapi/twikit) | 1-5MB | **1-5GB** | ✅ Feasible |
| Third-party API | 0 (per-call billing) | **0** | ✅ Feasible |

## Services

### InstagramAPIService

Browser-less Instagram automation using the `instagrapi` library.

```python
from services.leads import create_instagram_api_service

# Create service
service = create_instagram_api_service()

# Login
session = await service.login("username", "password", proxy="http://proxy:port")

# Follow user
result = await service.follow_user("username", "target_user_id")

# Send DM
result = await service.send_dm("username", ["user_id"], "Hello!")

# Get followers
followers = await service.get_followers("username", "kol_user_id", amount=100)
```

### TwitterAPIService

Browser-less Twitter/X automation using the `twikit` library.

```python
from services.leads import create_twitter_api_service

# Create service
service = create_twitter_api_service()

# Login
session = await service.login("username", "email", "password")

# Follow user
result = await service.follow_user("username", "target_user_id")

# Send DM
result = await service.send_dm("username", "user_id", "Hello!")
```

### SessionManagerService

Redis-based session persistence for login cookies/tokens.

```python
from services.leads import create_session_manager_service

# Create manager
manager = create_session_manager_service()

# Store session
await manager.store_session(
    platform="instagram",
    username="user123",
    session_data={"cookies": {...}},
    user_id="12345",
)

# Retrieve session
session = await manager.get_session("instagram", "user123")

# List all sessions
sessions = await manager.list_sessions("instagram")
```

### BrowserPoolService

Lightweight browser pool for login-only scenarios.

```python
from services.leads import create_browser_pool_service

# Create pool (10-20 instances recommended)
pool = create_browser_pool_service(pool_size=10)
await pool.start()

# Extract cookies for HTTP API use
result = await pool.extract_cookies_for_api(
    platform="instagram",
    username="user123",
    password="password",
)

if result.success:
    # Use result.cookies with HTTP API service
    pass

await pool.stop()
```

### AutomationExecutorService

Orchestrates follow, unfollow, and DM operations with rate limiting.

```python
from services.leads import create_automation_executor_service

# Create executor with HTTP API services
executor = create_automation_executor_service(
    instagram_api_service=instagram_api,
    twitter_api_service=twitter_api,
    session_manager=session_manager,
    scheduler_service=scheduler,
)

# Start session (uses HTTP API)
context = await executor.start_session(
    account_id="acc_1",
    username="user123",
    password="password",
    platform="instagram",
    use_http_api=True,
)

# Execute follow
result = await executor.execute_follow(context, "target_username")

# Execute batch follow
result = await executor.execute_batch_follow(
    task_id="task_1",
    account_id="acc_1",
    target_usernames=["user1", "user2", "user3"],
)
```

## Running 1000 Concurrent Sessions

```python
from services.leads import run_concurrent_sessions

# Prepare accounts and targets
accounts = [
    {"username": f"user_{i}", "password": f"pass_{i}"}
    for i in range(1000)
]
targets = [
    {"user_id": f"target_{i}"}
    for i in range(1000)
]

# Run concurrently
result = await run_concurrent_sessions(
    accounts=accounts,
    action_type="follow",
    targets=targets,
    max_concurrent=100,
    platform="instagram",
)

print(f"Success: {result['success']}")
print(f"Failed: {result['failed']}")
print(f"Rate Limited: {result['rate_limited']}")
```

## Installation

```bash
# Install dependencies
pip install instagrapi twikit playwright

# Install Playwright browsers (only needed for login fallback)
playwright install chromium
```

## Configuration

Set the following environment variables:

```bash
# Redis for session persistence
REDIS_HOST=localhost
REDIS_PORT=6379

# Proxy configuration (optional)
PROXY_HOST=proxy.example.com
PROXY_PORT=8080
PROXY_USERNAME=user
PROXY_PASSWORD=pass
```

## Testing

```bash
# Run unit tests
pytest api/tests/integration_tests/leads/test_concurrent_sessions.py -v

# Run benchmarks
pytest api/tests/integration_tests/leads/test_concurrent_sessions.py -v -k benchmark
```

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| instagrapi blocked by Instagram | Backup libraries (instabot, instagram_private_api) |
| Stricter account risk control | Residential proxies + device fingerprint simulation |
| API changes | Monitor library updates, prepare browser fallback |
| Legal compliance | Only use authorized accounts, follow platform ToS |

## Files

- `instagram_api_service.py` - Instagram HTTP API client
- `twitter_api_service.py` - Twitter/X HTTP API client
- `session_manager_service.py` - Redis session persistence
- `browser_pool_service.py` - Lightweight browser pool
- `automation_executor_service.py` - Orchestration layer

