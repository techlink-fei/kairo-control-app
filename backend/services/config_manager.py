"""Configuration management service for persistent config storage."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from backend.models.config import Config


class ConfigManager:
    """Manages loading and saving configuration to/from JSON file."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize ConfigManager.

        Args:
            config_path: Path to config file. Defaults to webui_config.json in repo root.
        """
        if config_path is None:
            # Default to repo root
            repo_root = Path(__file__).parent.parent.parent
            config_path = repo_root / "webui_config.json"

        self.config_path = config_path

    def load_config(self) -> Config:
        """Load configuration from JSON file.

        Returns:
            Config object. Returns default empty config if file doesn't exist.
        """
        try:
            with self.config_path.open(encoding="utf-8") as f:
                data = json.load(f)
            return Config.model_validate(data)
        except FileNotFoundError:
            return Config()
        except ValueError as e:
            print(f"Warning: Failed to load config from {self.config_path}: {e}")
            return Config()

    def save_config(self, config: Config) -> None:
        """Save configuration to JSON file.

        Args:
            config: Config object to save.
        """
        temporary = NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.config_path.parent,
            prefix=f".{self.config_path.name}.",
            suffix=".tmp",
            delete=False,
        )
        path = Path(temporary.name)
        try:
            with temporary as f:
                json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            path.replace(self.config_path)
        finally:
            path.unlink(missing_ok=True)

    def reset_config(self) -> Config:
        """Reset configuration to defaults.

        Returns:
            Fresh default Config object.
        """
        self.config_path.unlink(missing_ok=True)

        return Config()

    def config_exists(self) -> bool:
        """Check if config file exists.

        Returns:
            True if config file exists, False otherwise.
        """
        return self.config_path.exists()
