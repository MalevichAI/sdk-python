# UserCredentialsStore

A simple credential storage system for managing different types of authentication credentials.

## Features

- ✅ Multiple credential types (Core API, Image Registry)
- ✅ Environment variable overrides
- ✅ Secure file storage with restricted permissions (0600)
- ✅ Multiple registry support
- ✅ Type-safe with dataclasses
- ✅ No external dependencies (keyring-free)

## Storage Location

Credentials are stored in: `~/.malevich/credentials.json`

## Credential Types

### Core Credentials
```python
{
    "type": "core",
    "user": "username",
    "password": "password",
    "host": "https://core.mtp.group"
}
```

### Image Credentials
```python
{
    "type": "image",
    "ref": "ghcr.io/malevichai",
    "user": "username",
    "token": "ghp_token123"
}
```

## Usage

### Basic Usage

```python
from malevich_sdk.usp import UserCredentialsStore

# Initialize
store = UserCredentialsStore()

# Add Core API credentials
store.add_core_credentials(
    user="myuser",
    password="mypass",
    host="https://core.mtp.group"
)

# Add image registry credentials
store.add_image_credentials(
    ref="ghcr.io/malevichai",
    user="bot-user",
    token="ghp_1234567890"
)

# Retrieve credentials
core_creds = store.get_core_credentials()
if core_creds:
    print(f"User: {core_creds.user}")
    print(f"Password: {core_creds.password}")
    print(f"Host: {core_creds.host}")

# Get credentials for specific registry
ghcr_creds = store.get_image_credentials("ghcr.io/malevichai")
if ghcr_creds:
    print(f"Registry: {ghcr_creds.ref}")
    print(f"User: {ghcr_creds.user}")
    print(f"Token: {ghcr_creds.token}")
```

### Environment Variable Overrides

Environment variables take priority over stored credentials:

**Core API:**
```bash
export MALEVICH_USER="username"
export MALEVICH_PASSWORD="password"
export MALEVICH_HOST="https://core.mtp.group"
```

**Image Registry:**
```bash
export MALEVICH_IMAGE_USER="username"
export MALEVICH_IMAGE_TOKEN="token"
```

### Managing Credentials

```python
# List all stored credentials (without sensitive data)
all_creds = store.list_all()
for cred in all_creds:
    print(cred)

# Get all image registry credentials
all_images = store.get_all_image_credentials()

# Remove specific credentials
store.remove_core_credentials()
store.remove_image_credentials("ghcr.io/malevichai")

# Clear all credentials
store.clear_all()
```

### Integration with Existing Code

Update your existing credential usage:

```python
# Before
username = 'centre-x1jk'
password = 'kSGnhIfwOkfOwPSfAba8o5aN7x0Xvf4h'

with with_credentials((username, password)), with_connection("https://core.mtp.group"):
    # ... your code

# After
store = UserCredentialsStore()
core_creds = store.get_core_credentials()

if core_creds:
    with with_credentials((core_creds.user, core_creds.password)), \
         with_connection(core_creds.host):
        # ... your code
```

## CLI Commands (Future)

You can add CLI commands to manage credentials:

```bash
# Login
malevich-sdk auth login --type core
malevich-sdk auth login --type image --ref ghcr.io/malevichai

# List credentials
malevich-sdk auth list

# Logout
malevich-sdk auth logout --type core
malevich-sdk auth logout --type image --ref ghcr.io/malevichai

# Show current user
malevich-sdk auth whoami
```

## Security Notes

1. **File Permissions**: Credentials file is automatically set to `0600` (owner read/write only)
2. **No Plaintext in Code**: Never hardcode credentials
3. **Environment Variables**: Use for CI/CD and temporary overrides
4. **Gitignore**: Add `~/.malevich/` to your global gitignore
5. **Rotation**: Regularly rotate tokens and passwords

## API Reference

### UserCredentialsStore

**Methods:**

- `add_core_credentials(user, password, host, replace=True)` - Add/update Core API credentials
- `add_image_credentials(ref, user, token, replace=True)` - Add/update image registry credentials
- `get_core_credentials()` - Get Core API credentials (env vars or stored)
- `get_image_credentials(ref)` - Get credentials for specific registry
- `get_all_image_credentials()` - Get all image registry credentials
- `remove_core_credentials()` - Remove Core API credentials
- `remove_image_credentials(ref)` - Remove specific registry credentials
- `clear_all()` - Remove all credentials
- `list_all()` - List all credentials (without sensitive data)

### Data Classes

**CoreCredentials:**
- `type: "core"`
- `user: str`
- `password: str`
- `host: str`

**ImageCredentials:**
- `type: "image"`
- `ref: str` (registry reference)
- `user: str`
- `token: str`

