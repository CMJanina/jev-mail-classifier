from __future__ import annotations

import argparse
import imaplib
import sys
import time
from pathlib import Path

from jev_mail.actions import run_action
from jev_mail.classify import classify, matched_categories
from jev_mail.config import AppConfig, ConfigError, JevSettings, MailboxConfig, load_config
from jev_mail.mailbox import Mailbox
from jev_mail.providers import ProviderError, get_jev_client
from jev_mail.providers.base import JevClient


def _config_path(args: argparse.Namespace) -> Path:
    return Path(args.dir) / "config.yaml"


def _process_unprocessed(mailbox: Mailbox, client: JevClient, config: AppConfig, dry_run: bool, limit: int = 25) -> None:
    emails = mailbox.fetch_unprocessed(limit=limit)
    if len(emails) == limit:
        print(
            f"[jev-mail] hit max_emails_per_run ({limit}) -- "
            "there may be more unprocessed mail left for next run"
        )
    for mail in emails:
        probabilities = classify(client, config, mail.state)
        matched = matched_categories(config, probabilities)
        moves = {a.folder for c in matched for a in c.actions if a.type == "move"}
        if len(moves) > 1:
            print(f"[jev-mail] {mail.subject!r}: conflicting move destinations; skipped")
            continue

        if not matched and dry_run:
            print(f"[dry-run] {mail.subject!r}: no category matched")

        for category in matched:
            probability = probabilities[category.name]
            for action in category.actions:
                if dry_run:
                    print(f"[dry-run] {mail.subject!r}: {category.name} ({probability:.2f}) -> {action.type}")
                elif action.type != "move":
                    run_action(mailbox, mail, action)

        # Mark processed even when nothing matched -- otherwise a never-matching
        # email gets reclassified (and re-billed) on every future run.
        if not dry_run:
            if moves:
                mailbox.move(mail.uid, next(iter(moves)))
            else:
                mailbox.mark_processed(mail.uid)


def _mailbox_error_message(exc: Exception, config: MailboxConfig) -> str:
    if isinstance(exc, OSError):
        return f"couldn't connect to {config.host}:{config.port} -- {exc}"
    return f"IMAP error talking to {config.host} -- {exc}"


def cmd_configure(args: argparse.Namespace) -> int:
    from jev_mail.tui.app import JevMailConfigApp

    config_path = _config_path(args)
    try:
        config = load_config(config_path) if config_path.exists() else AppConfig({}, JevSettings(), [])
        if args.account is not None:
            name = args.account
            if not name.strip():
                raise ConfigError("account name must not be empty")
        else:
            name = config.account_name(None) if config.accounts else "default"
        config.accounts.setdefault(name, MailboxConfig(host=""))
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    JevMailConfigApp(config_path, config, name).run()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    return _run(args, watch=False)


def cmd_watch(args: argparse.Namespace) -> int:
    return _run(args, watch=True)


def _run(args: argparse.Namespace, watch: bool) -> int:
    config_path = _config_path(args)
    try:
        config = load_config(config_path)
        account = config.accounts[config.account_name(args.account)]
        if not config.categories:
            raise ConfigError("config has no categories; run `jev-mail configure` to add some")
        client = get_jev_client(config.jev)
    except (ConfigError, ProviderError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if watch:
        print(f"watching {account.folder}@{account.host} (ctrl-c to stop)...")
    try:
        with Mailbox(account, readonly=args.dry_run) as mailbox:
            while True:
                _process_unprocessed(mailbox, client, config, args.dry_run, account.max_emails_per_run)
                if not watch:
                    return 0
                if mailbox.supports_idle():
                    mailbox.idle()
                    mailbox.idle_check(timeout=min(account.poll_interval_seconds, 600))
                    mailbox.idle_done()
                else:
                    time.sleep(account.poll_interval_seconds)
    except (OSError, imaplib.IMAP4.error) as exc:
        print(f"error: {_mailbox_error_message(exc, account)}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jev-mail", description="Classify your inbox with Jev.")
    parser.set_defaults(dry_run=False, account=None)
    parser.add_argument("--dir", default=".", help="directory holding config.yaml (default: cwd)")
    subparsers = parser.add_subparsers(dest="command")

    configure_parser = subparsers.add_parser("configure", help="open the TUI to build/edit config.yaml")

    run_parser = subparsers.add_parser("run", help="classify unprocessed mail once and exit")
    run_parser.add_argument("-n", "--dry-run", action="store_true", help="classify and print, without applying any action")

    watch_parser = subparsers.add_parser("watch", help="keep classifying new mail as it arrives")

    for command_parser in (configure_parser, run_parser, watch_parser):
        command_parser.add_argument("--account", help="account name in config.yaml; configure creates it if missing")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    config_path = _config_path(args)

    if args.command is None:
        args.command = "configure" if not config_path.exists() else "run"

    commands = {"configure": cmd_configure, "run": cmd_run, "watch": cmd_watch}
    sys.exit(commands[args.command](args))


if __name__ == "__main__":
    main()
