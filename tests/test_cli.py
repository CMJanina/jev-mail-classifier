from unittest.mock import MagicMock

import pytest

import jev_mail.cli as cli
from jev_mail.config import Action, AppConfig, Category, JevSettings, MailboxConfig
from jev_mail.mailbox import Email


def _config() -> AppConfig:
    return AppConfig(
        mailbox=MailboxConfig(host="imap.example.com"),
        jev=JevSettings(default_threshold=0.6),
        categories=[Category(name="invoice", description="Invoice", actions=[Action(type="tag", value="Invoice")])],
    )


def test_build_parser_defaults_and_dry_run_flag():
    parser = cli.build_parser()
    assert parser.parse_args([]).dry_run is False

    args = parser.parse_args(["run", "--dry-run"])
    assert args.command == "run"
    assert args.dry_run is True

    args = parser.parse_args(["watch"])
    assert args.command == "watch"
    assert args.dry_run is False

    args = parser.parse_args(["configure"])
    assert args.command == "configure"


def test_process_unprocessed_passes_limit_to_fetch():
    mailbox = MagicMock()
    mailbox.fetch_unprocessed.return_value = []
    client = MagicMock()

    config = _config()
    config.mailbox.max_emails_per_run = 7
    cli._process_unprocessed(mailbox, client, config, dry_run=False)

    mailbox.fetch_unprocessed.assert_called_once_with(limit=7)


def test_process_unprocessed_warns_when_limit_is_hit(capsys):
    mailbox = MagicMock()
    mailbox.fetch_unprocessed.return_value = [Email(uid=1, subject="One", body="body")]
    client = MagicMock()
    client.decide.return_value = {"invoice": 0.9}

    config = _config()
    config.mailbox.max_emails_per_run = 1
    cli._process_unprocessed(mailbox, client, config, dry_run=False)

    assert "max_emails_per_run" in capsys.readouterr().out


def test_process_unprocessed_dry_run_does_not_mutate_mailbox(capsys):
    mailbox = MagicMock()
    mailbox.fetch_unprocessed.return_value = [Email(uid=1, subject="Invoice #1", body="Please pay")]
    client = MagicMock()
    client.decide.return_value = {"invoice": 0.9}

    cli._process_unprocessed(mailbox, client, _config(), dry_run=True)

    mailbox.add_tag.assert_not_called()
    mailbox.mark_processed.assert_not_called()
    assert "dry-run" in capsys.readouterr().out


def test_process_unprocessed_applies_actions_and_marks_processed():
    mailbox = MagicMock()
    mailbox.fetch_unprocessed.return_value = [Email(uid=1, subject="Invoice #1", body="Please pay")]
    client = MagicMock()
    client.decide.return_value = {"invoice": 0.9}

    cli._process_unprocessed(mailbox, client, _config(), dry_run=False)

    mailbox.add_tag.assert_called_once_with(1, "Invoice")
    mailbox.mark_processed.assert_called_once_with(1)


def test_process_unprocessed_below_threshold_no_actions():
    mailbox = MagicMock()
    mailbox.fetch_unprocessed.return_value = [Email(uid=1, subject="Newsletter", body="...")]
    client = MagicMock()
    client.decide.return_value = {"invoice": 0.1}

    cli._process_unprocessed(mailbox, client, _config(), dry_run=False)

    mailbox.add_tag.assert_not_called()
    mailbox.mark_processed.assert_called_once_with(1)


@pytest.mark.parametrize("command", ["run", "watch"])
def test_command_reports_config_error(monkeypatch, capsys, command):
    from jev_mail.config import ConfigError

    def raise_config_error(*a, **k):
        raise ConfigError("no config file")

    monkeypatch.setattr(cli, "load_config", raise_config_error)
    args = cli.build_parser().parse_args([command])
    args.dir = "."

    exit_code = getattr(cli, f"cmd_{command}")(args)

    assert exit_code == 1
    assert "no config file" in capsys.readouterr().err


@pytest.mark.parametrize("command", ["run", "watch"])
def test_command_reports_connection_error_not_a_traceback(monkeypatch, capsys, command):
    monkeypatch.setattr(cli, "load_config", lambda *a, **k: _config())
    monkeypatch.setattr(cli, "get_jev_client", lambda *a, **k: MagicMock())

    class FakeMailbox:
        def __init__(self, mailbox_config):
            pass

        def __enter__(self):
            raise ConnectionRefusedError("[Errno 61] Connection refused")

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(cli, "Mailbox", FakeMailbox)
    args = cli.build_parser().parse_args([command])
    args.dir = "."

    exit_code = getattr(cli, f"cmd_{command}")(args)

    err = capsys.readouterr().err
    assert exit_code == 1
    assert "Traceback" not in err
    assert "imap.example.com" in err


def test_main_auto_launches_configure_when_no_config(monkeypatch, tmp_path):
    called = {}
    monkeypatch.setattr(cli, "cmd_configure", lambda args: called.setdefault("cmd", "configure") or 0)
    monkeypatch.setattr(cli.sys, "argv", ["jev-mail", "--dir", str(tmp_path)])
    monkeypatch.setattr(cli.sys, "exit", lambda code: called.setdefault("exit", code))

    cli.main()

    assert called["cmd"] == "configure"


def test_main_auto_runs_when_config_exists(monkeypatch, tmp_path):
    (tmp_path / "config.yaml").write_text("mailbox:\n  host: x\ncategories: {}\n")
    called = {}
    monkeypatch.setattr(cli, "cmd_run", lambda args: called.setdefault("cmd", "run") or 0)
    monkeypatch.setattr(cli.sys, "argv", ["jev-mail", "--dir", str(tmp_path)])
    monkeypatch.setattr(cli.sys, "exit", lambda code: called.setdefault("exit", code))

    cli.main()

    assert called["cmd"] == "run"
