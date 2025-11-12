"""User credentials storage for different authentication types."""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal, Union


@dataclass
class CoreCredentials:
    """Credentials for Malevich Core API."""
    type: Literal["core"] = "core"
    user: str = ""
    password: str = ""
    host: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ImageCredentials:
    """Credentials for container image registries."""
    type: Literal["image"] = "image"
    ref: str = ""  # Registry reference (e.g., "ghcr.io/malevichai")
    user: str = ""
    token: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


Credentials = Union[CoreCredentials, ImageCredentials]


class UserCredentialsStore:
    """Store and manage user credentials for different services.
    
    Supports:
    - Core API credentials (username/password)
    - Image registry credentials (username/token)
    - Environment variable overrides
    - Multiple credential profiles
    """
    
    def __init__(self, config_dir: Path | None = None):
        """Initialize the credentials store.
        
        Args:
            config_dir: Directory for storing config. Defaults to ~/.malevich
        """
        self.config_dir = config_dir or Path.home() / ".malevich"
        self.config_file = self.config_dir / "credentials.json"
        self._credentials: list[dict] = []
        self._load_credentials()
    
    def _load_credentials(self) -> None:
        """Load credentials from config file."""
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text())
                self._credentials = data.get("credentials", [])
            except (json.JSONDecodeError, KeyError):
                self._credentials = []
        else:
            self._credentials = []
    
    def _save_credentials(self) -> None:
        """Save credentials to config file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        data = {"credentials": self._credentials}
        self.config_file.write_text(json.dumps(data, indent=2))
        
        # Set restrictive permissions (Unix-like systems)
        try:
            self.config_file.chmod(0o600)
        except Exception:
            # Windows or permission issues
            pass
    
    def add_core_credentials(
        self,
        user: str,
        password: str,
        host: str = "https://core.mtp.group",
        replace: bool = True
    ) -> CoreCredentials:
        """Add or update Core API credentials.
        
        Args:
            user: Username for Core API
            password: Password for Core API
            host: Host URL for Core API
            replace: If True, replace existing core credentials. If False, add new entry.
        
        Returns:
            The created CoreCredentials object
        """
        creds = CoreCredentials(user=user, password=password, host=host)
        
        if replace:
            # Remove existing core credentials
            self._credentials = [
                c for c in self._credentials if c.get("type") != "core"
            ]
        
        self._credentials.append(creds.to_dict())
        self._save_credentials()
        return creds
    
    def add_image_credentials(
        self,
        ref: str,
        user: str,
        token: str,
        replace: bool = True
    ) -> ImageCredentials:
        """Add or update image registry credentials.
        
        Args:
            ref: Registry reference (e.g., "ghcr.io/malevichai")
            user: Username for registry
            token: Access token for registry
            replace: If True, replace existing credentials for this ref
        
        Returns:
            The created ImageCredentials object
        """
        creds = ImageCredentials(ref=ref, user=user, token=token)
        
        if replace:
            # Remove existing credentials for this ref
            self._credentials = [
                c for c in self._credentials 
                if not (c.get("type") == "image" and c.get("ref") == ref)
            ]
        
        self._credentials.append(creds.to_dict())
        self._save_credentials()
        return creds
    
    def get_core_credentials(self, username: str) -> CoreCredentials | None:
        """Get Core API credentials.
        
        Priority:
        1. Environment variables (MALEVICH_USER, MALEVICH_PASSWORD, MALEVICH_HOST)
        2. Stored credentials
        
        Returns:
            CoreCredentials if found, None otherwise
        """
        # Check environment variables first
        env_user = os.getenv("MALEVICH_USER")
        env_password = os.getenv("MALEVICH_PASSWORD")
        env_host = os.getenv("MALEVICH_HOST")
        
        if env_user and env_password:
            return CoreCredentials(
                user=env_user,
                password=env_password,
                host=env_host or "https://core.mtp.group"
            )
        
        # Check stored credentials
        for cred in self._credentials:
            if cred.get("type") == "core" and cred.get("user") == username:
                return CoreCredentials(
                    user=cred.get("user", ""),
                    password=cred.get("password", ""),
                    host=cred.get("host", "https://core.mtp.group")
                )
        
        return None
    
    def get_image_credentials(self, ref: str) -> ImageCredentials | None:
        """Get image registry credentials for a specific registry.
        
        Priority:
        1. Environment variables (MALEVICH_IMAGE_USER, MALEVICH_IMAGE_TOKEN)
        2. Stored credentials matching the ref
        
        Args:
            ref: Registry reference (e.g., "ghcr.io/malevichai")
        
        Returns:
            ImageCredentials if found, None otherwise
        """
        # Check environment variables first
        env_user = os.getenv("MALEVICH_IMAGE_USER")
        env_token = os.getenv("MALEVICH_IMAGE_TOKEN")
        
        if env_user and env_token:
            return ImageCredentials(
                ref=ref,
                user=env_user,
                token=env_token
            )
        
        # Check stored credentials
        for cred in self._credentials:
            if cred.get("type") == "image" and cred.get("ref") == ref:
                return ImageCredentials(
                    ref=cred.get("ref", ""),
                    user=cred.get("user", ""),
                    token=cred.get("token", "")
                )
        
        return None
    
    def get_all_image_credentials(self) -> list[ImageCredentials]:
        """Get all stored image registry credentials.
        
        Returns:
            List of ImageCredentials
        """
        result = []
        for cred in self._credentials:
            if cred.get("type") == "image":
                result.append(ImageCredentials(
                    ref=cred.get("ref", ""),
                    user=cred.get("user", ""),
                    token=cred.get("token", "")
                ))
        return result
    
    def remove_core_credentials(self) -> bool:
        """Remove Core API credentials.
        
        Returns:
            True if credentials were removed, False if none existed
        """
        original_len = len(self._credentials)
        self._credentials = [
            c for c in self._credentials if c.get("type") != "core"
        ]
        
        if len(self._credentials) < original_len:
            self._save_credentials()
            return True
        return False
    
    def remove_image_credentials(self, ref: str) -> bool:
        """Remove image registry credentials for a specific registry.
        
        Args:
            ref: Registry reference (e.g., "ghcr.io/malevichai")
        
        Returns:
            True if credentials were removed, False if none existed
        """
        original_len = len(self._credentials)
        self._credentials = [
            c for c in self._credentials 
            if not (c.get("type") == "image" and c.get("ref") == ref)
        ]
        
        if len(self._credentials) < original_len:
            self._save_credentials()
            return True
        return False
    
    def clear_all(self) -> None:
        """Remove all stored credentials."""
        self._credentials = []
        self._save_credentials()
    
    def list_all(self) -> list[dict]:
        """List all stored credentials (without sensitive data).
        
        Returns:
            List of credential metadata (type, user, ref, host)
        """
        result = []
        for cred in self._credentials:
            cred_type = cred.get("type")
            if cred_type == "core":
                result.append({
                    "type": "core",
                    "user": cred.get("user"),
                    "host": cred.get("host"),
                })
            elif cred_type == "image":
                result.append({
                    "type": "image",
                    "ref": cred.get("ref"),
                    "user": cred.get("user"),
                })
        return result

