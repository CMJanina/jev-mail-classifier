from unittest.mock import MagicMock

import pytest

import jev_mail.cli as cli
from jev_mail.config import Action, AppConfig, Category, JevSettings, MailboxConfig
from jev_mail.mailbox import Email


def _config() -> AppConfig:
    return AppConfig(
        accounts={"default": MailboxConfig(host="imap.example.com")},
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
    config.accounts["default"].max_emails_per_run = 7
    cli._process_unprocessed(mailbox, client, config, dry_run=False, limit=config.accounts["default"].max_emails_per_run)

    mailbox.fetch_unprocessed.assert_called_once_with(limit=7)


def test_process_unprocessed_warns_when_limit_is_hit(capsys):
    mailbox = MagicMock()
    mailbox.fetch_unprocessed.return_value = [Email(uid=1, subject="One", body="body")]
    client = MagicMock()
    client.decide.return_value = {"invoice": 0.9}

    config = _config()
    config.accounts["default"].max_emails_per_run = 1
    cli._process_unprocessed(mailbox, client, config, dry_run=False, limit=config.accounts["default"].max_emails_per_run)

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
        def __init__(self, mailbox_config, *, readonly=False):
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


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("destination", ["Invoices", "Other"])
def test_move_preserves_all_tags_and_processed_flag(destination, dry_run, capsys):
    from jev_mail.mailbox import Mailbox, PROCESSED_KEYWORD

    inbox = {1: set()}
    moved = {}
    server = MagicMock()
    server.add_flags.side_effect = lambda uids, flags: inbox[uids[0]].update(flags)
    server.move.side_effect = lambda uids, folder: moved.update({folder: inbox.pop(uids[0])})
    mailbox = Mailbox(MailboxConfig(host="example.com"), server=server)
    mailbox.fetch_unprocessed = lambda limit: [Email(1, "Invoice", "Urgent")]
    config = _config()
    config.categories[0].actions.insert(0, Action("move", folder="Invoices"))
    config.categories.append(Category("urgent", "Urgent", actions=[
        Action("tag", value="Urgent"), Action("move", folder=destination),
    ]))
    client = MagicMock()
    client.decide.return_value = {"invoice": .9, "urgent": .9}

    cli._process_unprocessed(mailbox, client, config, dry_run)

    if dry_run or destination != "Invoices":
        assert inbox == {1: set()}
        assert moved == {}
        server.add_flags.assert_not_called()
        server.move.assert_not_called()
    else:
        assert inbox == {}
        assert moved == {"Invoices": {"Invoice", "Urgent", PROCESSED_KEYWORD}}
        server.move.assert_called_once_with([1], "Invoices")
    if destination != "Invoices":
        assert "conflicting move destinations" in capsys.readouterr().out


@pytest.mark.parametrize("command", ["run", "watch"])
@pytest.mark.parametrize("selection", [[], ["--account", "typo"]])
def test_multiple_accounts_require_valid_selection(tmp_path, monkeypatch, capsys, command, selection):
    from jev_mail.config import save_config

    config = _config()
    config.accounts["work"] = MailboxConfig("imap.work.test")
    save_config(config, tmp_path / "config.yaml")
    mailbox = MagicMock()
    monkeypatch.setattr(cli, "Mailbox", mailbox)
    args = cli.build_parser().parse_args(["--dir", str(tmp_path), command, *selection])
    assert getattr(cli, f"cmd_{command}")(args) == 1
    assert "available accounts: default, work" in capsys.readouterr().err
    mailbox.assert_not_called()


def test_run_selected_account_uses_its_credentials_and_limit(tmp_path, monkeypatch):
    from jev_mail.config import save_config

    config = _config()
    config.accounts["work"] = MailboxConfig("imap.work.test", username="work", password="secret", max_emails_per_run=3)
    config.jev.openrouter_api_key = "config-key"
    save_config(config, tmp_path / "config.yaml")
    mailbox = MagicMock()
    mailbox.return_value.__enter__.return_value.fetch_unprocessed.return_value = []
    monkeypatch.setattr(cli, "Mailbox", mailbox)
    args = cli.build_parser().parse_args(["--dir", str(tmp_path), "run", "--account", "work", "--dry-run"])
    assert cli.cmd_run(args) == 0
    mailbox.assert_called_once_with(config.accounts["work"], readonly=True)
    mailbox.return_value.__enter__.return_value.fetch_unprocessed.assert_called_once_with(limit=3)


def test_configure_adds_account_without_losing_existing_config(tmp_path, monkeypatch):
    from jev_mail.config import save_config, load_config
    from jev_mail.tui import app

    config = _config()
    save_config(config, tmp_path / "config.yaml")
    wizard = MagicMock()
    monkeypatch.setattr(app, "JevMailConfigApp", wizard)
    args = cli.build_parser().parse_args(["--dir", str(tmp_path), "configure", "--account", "work"])
    assert cli.cmd_configure(args) == 0
    path, edited, name = wizard.call_args.args
    assert name == "work"
    assert edited.accounts["default"] == config.accounts["default"]
    assert edited.categories == config.categories
    assert "work" in edited.accounts
    assert load_config(path) == config  # Nothing is written until the wizard saves.


def test_configure_does_not_overwrite_legacy_config(tmp_path, capsys):
    path = tmp_path / "config.yaml"
    original = "mailbox:\n  host: imap.test\n"
    path.write_text(original)
    args = cli.build_parser().parse_args(["--dir", str(tmp_path), "configure"])
    assert cli.cmd_configure(args) == 1
    assert "old config format" in capsys.readouterr().err
    assert path.read_text() == original
