# `with_user()` Context Manager

A convenient context manager that automatically loads credentials from the `UserCredentialsStore`.

## Overview

`with_user()` eliminates the need to manually load credentials in your code. It automatically:
1. Loads credentials from the store (or environment variables)
2. Validates that the host is set (requires `with_connection()` first)
3. Sets credentials for the current context

## Usage

### Basic Usage

```python
from malevich_sdk.core_api.connection import with_connection
from malevich_sdk.core_api.credentials import with_user

# Use with_connection() first, then with_user()
with with_connection("https://core.mtp.group"):
    with with_user():
        # Credentials are automatically loaded and set
        # Your code here...
        pass
```

### Before and After

**Before (manual credentials):**
```python
from malevich_sdk.core_api.connection import with_connection
from malevich_sdk.core_api.credentials import with_credentials

username = 'centre-x1jk'
password = 'kSGnhIfwOkfOwPSfAba8o5aN7x0Xvf4h'

with with_credentials((username, password)), with_connection("https://core.mtp.group"):
    # Your code
    pass
```

**After (automatic credentials):**
```python
from malevich_sdk.core_api.connection import with_connection
from malevich_sdk.core_api.credentials import with_user

with with_connection("https://core.mtp.group"):
    with with_user():
        # Credentials loaded automatically!
        pass
```

### Accessing Credentials

The context manager yields the username and password if you need them:

```python
with with_connection("https://core.mtp.group"):
    with with_user() as (username, password):
        print(f"Logged in as: {username}")
```

## Requirements

### 1. Host Must Be Set First

`with_connection()` **must** be called before `with_user()`:

```python
# ✅ CORRECT
with with_connection("https://core.mtp.group"):
    with with_user():
        pass

# ❌ WRONG - will raise RuntimeError
with with_user():
    pass
```

**Error if host not set:**
```
RuntimeError: Host is not set. Please use with_connection() before with_user().
Example: with with_connection('https://core.mtp.group'): with with_user(): ...
```

### 2. Credentials Must Be Available

Credentials must be either:
- Stored in `~/.malevich/credentials.json` (via `malevich-sdk creds add core`)
- Set as environment variables (`MALEVICH_USER`, `MALEVICH_PASSWORD`)

**Error if no credentials:**
```
RuntimeError: No credentials found. Please add credentials using:
malevich-sdk creds add core <username> <password>
or set environment variables: MALEVICH_USER, MALEVICH_PASSWORD
```

## Setting Up Credentials

### Option 1: CLI (Recommended)

```bash
malevich-sdk creds add core myuser mypassword
```

### Option 2: Environment Variables

```bash
export MALEVICH_USER="myuser"
export MALEVICH_PASSWORD="mypassword"
```

### Option 3: Programmatically

```python
from malevich_sdk.usp.credstore import UserCredentialsStore

store = UserCredentialsStore()
store.add_core_credentials(
    user="myuser",
    password="mypassword",
    host="https://core.mtp.group"
)
```

## Complete Example

```python
from malevich_sdk.core_api.connection import with_connection
from malevich_sdk.core_api.credentials import with_user
from malevich_sdk import run, Pipeline

# Ensure credentials are set first (one-time setup)
# $ malevich-sdk creds add core myuser mypassword

# Use in your code
with with_connection("https://core.mtp.group"):
    with with_user():
        # Now you can use any SDK functions that require auth
        pipeline = Pipeline.create("my-pipeline")
        result = run(pipeline, input_data=...)
```

## Error Handling

```python
from malevich_sdk.core_api.connection import with_connection
from malevich_sdk.core_api.credentials import with_user

try:
    with with_connection("https://core.mtp.group"):
        with with_user() as (username, password):
            print(f"Connected as {username}")
            # Your code here
except RuntimeError as e:
    # Handle missing credentials or connection
    print(f"Error: {e}")
```

## Environment Variable Priority

Environment variables take precedence over stored credentials:

1. **MALEVICH_USER / MALEVICH_PASSWORD** (highest priority)
2. Stored credentials in `~/.malevich/credentials.json`

This is useful for CI/CD or temporary overrides without modifying stored credentials.

## Benefits

✅ **Convenience** - No need to manually load credentials  
✅ **Security** - Credentials not hardcoded in source  
✅ **Validation** - Ensures host is set before use  
✅ **Flexibility** - Works with stored credentials or env vars  
✅ **Clean Code** - Less boilerplate in your scripts  

## See Also

- [UserCredentialsStore](../usp/README.md) - Credential storage system
- [CLI Commands](../../CLI_USAGE.md) - Managing credentials via CLI
- `with_connection()` - Setting the host URL
- `with_credentials()` - Manual credential setting

