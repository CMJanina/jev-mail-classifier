from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

import yaml

ACTION_TYPES = ("tag", "move")


class ConfigError(Exception):
    """Raised for a malformed or incomplete config.yaml."""


@dataclass(frozen=True)
class Action:
    type: Literal["tag", "move"]
    value: str | None = None
    folder: str | None = None

    def __post_init__(self) -> None:
        if self.type not in ACTION_TYPES:
            raise ConfigError(f"unknown action type: {self.type!r}")
        payload = self.value if self.type == "tag" else self.folder
        if not isinstance(payload, str) or not payload.strip():
            raise ConfigError(f"{self.type} action requires a non-empty {'value' if self.type == 'tag' else 'folder'}")
        if self.type == "tag":
            # IMAP keywords are atoms, not quoted strings.
            if any(ord(c) < 33 or ord(c) > 126 or c in '(){%*"\\]' for c in payload):
                raise ConfigError("tag value must be an IMAP keyword without spaces or special characters")
        elif any(ord(c) < 32 or ord(c) == 127 for c in payload):
            raise ConfigError("move folder must not contain control characters")

    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        return cls(type=data.get("type"), value=data.get("value"), folder=data.get("folder"))

    def to_dict(self) -> dict:
        out: dict = {"type": self.type}
        if self.value is not None:
            out["value"] = self.value
        if self.folder is not None:
            out["folder"] = self.folder
        return out


@dataclass
class Category:
    name: str
    description: str
    threshold: float | None = None
    actions: list[Action] = field(default_factory=list)


@dataclass
class MailboxConfig:
    host: str
    port: int = 993
    username: str = ""
    password: str = ""
    folder: str = "INBOX"
    poll_interval_seconds: int = 60
    max_emails_per_run: int = 25

    def validate_numbers(self) -> None:
        for key in ("port", "poll_interval_seconds", "max_emails_per_run"):
            value = getattr(self, key)
            if type(value) is not int or value <= 0:
                raise ConfigError(f"{key} must be a positive integer")


@dataclass
class JevSettings:
    provider: str = "auto"
    default_threshold: float = 0.6
    typesafe_api_key: str = ""
    openrouter_api_key: str = ""


@dataclass
class AppConfig:
    accounts: dict[str, MailboxConfig]
    jev: JevSettings
    categories: list[Category]

    def category_threshold(self, category: Category) -> float:
        return category.threshold if category.threshold is not None else self.jev.default_threshold

    def account_name(self, name: str | None) -> str:
        if name is not None and name in self.accounts:
            return name
        if name is None and len(self.accounts) == 1:
            return next(iter(self.accounts))
        available = ", ".join(self.accounts) or "none"
        if name is not None:
            raise ConfigError(f"unknown account {name!r}; available accounts: {available}")
        raise ConfigError(f"choose an account with --account NAME; available accounts: {available}")


def load_config(config_path: str | Path) -> AppConfig:
    config_path = Path(config_path)
    if not config_path.exists():
        raise ConfigError(f"no config file at {config_path}; run `jev-mail configure` first")
    try:
        raw = yaml.safe_load(config_path.read_text())
        if not isinstance(raw, dict):
            raise ConfigError("config.yaml must contain a mapping")
        if "mailbox" in raw:
            raise ConfigError(
                "old config format: move mailbox to accounts.NAME and copy credentials "
                "from .env into config.yaml; see README migration instructions"
            )
        accounts_raw = raw.get("accounts", {})
        if not isinstance(accounts_raw, dict) or not accounts_raw:
            raise ConfigError("config has no accounts; add an entry under accounts")
        accounts = {}
        for name, data in accounts_raw.items():
            if not isinstance(name, str) or not name.strip():
                raise ConfigError("account names must be non-empty strings")
            mailbox = MailboxConfig(**data)
            for key in ("host", "username", "password", "folder"):
                if not isinstance(getattr(mailbox, key), str):
                    raise ConfigError(f"accounts.{name}.{key} must be a string")
            if not mailbox.host.strip():
                raise ConfigError(f"accounts.{name}.host is empty")
            mailbox.validate_numbers()
            accounts[name] = mailbox

        jev = JevSettings(**raw.get("jev", {}))
        jev.default_threshold = float(jev.default_threshold)
        for key in ("provider", "typesafe_api_key", "openrouter_api_key"):
            if not isinstance(getattr(jev, key), str):
                raise ConfigError(f"jev.{key} must be a string")
        categories = [
            Category(
                name=name,
                description=data.get("description", ""),
                threshold=data.get("threshold"),
                actions=[Action.from_dict(a) for a in data.get("actions", [])],
            )
            for name, data in (raw.get("categories") or {}).items()
        ]
        return AppConfig(accounts=accounts, jev=jev, categories=categories)
    except (OSError, yaml.YAMLError, TypeError, ValueError, AttributeError) as exc:
        raise ConfigError("invalid config.yaml; check its syntax and setting types") from exc


def save_config(config: AppConfig, config_path: str | Path) -> None:
    for mailbox in config.accounts.values():
        mailbox.validate_numbers()
    raw = {
        "jev": asdict(config.jev),
        "accounts": {name: asdict(mailbox) for name, mailbox in config.accounts.items()},
        "categories": {
            cat.name: {
                "description": cat.description,
                **({"threshold": cat.threshold} if cat.threshold is not None else {}),
                "actions": [a.to_dict() for a in cat.actions],
            }
            for cat in config.categories
        },
    }
    content = yaml.safe_dump(raw, sort_keys=False, default_flow_style=False)
    # Restrict access before writing credentials, including on an existing file.
    fd = os.open(config_path, os.O_WRONLY | os.O_CREAT, 0o600)
    with os.fdopen(fd, "w") as output:
        os.fchmod(output.fileno(), 0o600)
        output.truncate(0)
        output.write(content)
