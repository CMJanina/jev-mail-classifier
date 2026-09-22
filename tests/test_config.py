import stat

import pytest

from jev_mail.config import Action, AppConfig, Category, ConfigError, JevSettings, MailboxConfig, load_config, save_config


def test_config_round_trip_accounts_and_literal_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("IMAP_PASSWORD", "wrong")
    monkeypatch.setenv("OPENROUTER_API_KEY", "wrong")
    (tmp_path / ".env").write_text("IMAP_PASSWORD=wrong\nOPENROUTER_API_KEY=wrong\n")
    config = AppConfig(
        accounts={
            "personal": MailboxConfig(host="imap.personal.test", username="me", password="it's a # secret\n${IMAP_PASSWORD}"),
            "work": MailboxConfig(host="imap.work.test", username="work", password="other", max_emails_per_run=5),
        },
        jev=JevSettings(openrouter_api_key="configured-key", default_threshold=0.5),
        categories=[Category("invoice", "Invoice", 0.8, [Action("move", folder="Invoices")])],
    )
    path = tmp_path / "config.yaml"
    path.touch(mode=0o644)
    save_config(config, path)
    assert load_config(path) == config
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert load_config(path).accounts["personal"].max_emails_per_run == 25


def test_account_selection():
    config = AppConfig({"personal": MailboxConfig("imap.test")}, JevSettings(), [])
    assert config.account_name(None) == "personal"
    config.accounts["work"] = MailboxConfig("imap.work.test")
    assert config.account_name("work") == "work"
    with pytest.raises(ConfigError, match="choose an account.*personal, work"):
        config.account_name(None)
    with pytest.raises(ConfigError, match="unknown account.*personal, work"):
        config.account_name("typo")


@pytest.mark.parametrize("content", [
    "[]", "[broken", "accounts: {}", "accounts: []",
    "accounts:\n  work:\n    host: ''",
    "accounts:\n  work:\n    host: imap.test\n    password: 123",
    "accounts:\n  work:\n    host: imap.test\n    max_emails_per_run: 0",
    "accounts:\n  work:\n    host: imap.test\n    unknown: value",
])
def test_invalid_config_raises_config_error(tmp_path, content):
    path = tmp_path / "config.yaml"
    path.write_text(content)
    with pytest.raises(ConfigError):
        load_config(path)


def test_legacy_config_requires_migration(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("mailbox:\n  host: imap.test\n")
    with pytest.raises(ConfigError, match="old config format"):
        load_config(path)


def test_missing_config_raises(tmp_path):
    with pytest.raises(ConfigError, match="no config file"):
        load_config(tmp_path / "missing.yaml")


def test_quoted_default_threshold_matches_categories(tmp_path):
    from jev_mail.classify import matched_categories

    path = tmp_path / "config.yaml"
    path.write_text('accounts:\n  work:\n    host: imap.test\njev:\n  default_threshold: "0.7"\ncategories:\n  invoice:\n    description: Invoice\n')
    config = load_config(path)
    assert config.jev.default_threshold == 0.7
    assert matched_categories(config, {"invoice": 0.8}) == config.categories
    assert matched_categories(config, {"invoice": 0.6}) == []


@pytest.mark.parametrize("key", ["port", "poll_interval_seconds", "max_emails_per_run"])
@pytest.mark.parametrize("value", [0, -1, "bad"])
def test_save_rejects_invalid_mailbox_numbers_without_changing_file(tmp_path, key, value):
    path = tmp_path / "config.yaml"
    config = AppConfig({"work": MailboxConfig("imap.test")}, JevSettings(), [])
    save_config(config, path)
    original = path.read_bytes()
    setattr(config.accounts["work"], key, value)
    with pytest.raises(ConfigError, match=f"{key} must be a positive integer"):
        save_config(config, path)
    assert path.read_bytes() == original
