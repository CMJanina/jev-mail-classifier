from __future__ import annotations

import argparse
import imaplib
import sys
import time
from pathlib import Path

from jev_mail.actions import run_action
from jev_mail.classify import classify, matched_categories
from jev_mail.config import AppConfig, ConfigError, load_config
from jev_mail.mailbox import Mailbox
from jev_mail.providers import ProviderError, get_jev_client
from jev_mail.providers.base import JevClient


def _paths(args: argparse.Namespace) -> tuple[Path, Path]:
    base = Path(args.dir)
    return base / "config.yaml", base / ".env"


def _process_unprocessed(mailbox: Mailbox, client: JevClient, config: AppConfig, dry_run: bool) -> None:
    emails = mailbox.fetch_unprocessed(limit=config.mailbox.max_emails_per_run)
    if len(emails) == config.mailbox.max_emails_per_run:
        print(
            f"[jev-mail] hit max_emails_per_run ({config.mailbox.max_emails_per_run}) -- "
            "there may be more unprocessed mail left for next run"
        )
    for mail in emails:
        probabilities = classify(client, config, mail.state)
        matched = matched_categories(config, probabilities)

        if not matched and dry_run:
            print(f"[dry-run] {mail.subject!r}: no category matched")

        for category in matched:
            probability = probabilities[category.name]
            for action in category.actions:
                if dry_run:
                    print(f"[dry-run] {mail.subject!r}: {category.name} ({probability:.2f}) -> {action.type}")
                else:
                    run_action(mailbox, mail, action)

        # Mark processed even when nothing matched -- otherwise a never-matching
        # email gets reclassified (and re-billed) on every future run.
        if not dry_run:
            mailbox.mark_processed(mail.uid)


def _mailbox_error_message(exc: Exception, config: AppConfig) -> str:
    if isinstance(exc, OSError):
        return f"couldn't connect to {config.mailbox.host}:{config.mailbox.port} -- {exc}"
    return f"IMAP error talking to {config.mailbox.host} -- {exc}"


def cmd_configure(args: argparse.Namespace) -> int:
    from jev_mail.tui.app import JevMailConfigApp

    config_path, env_path = _paths(args)
    try:
        config = load_config(config_path, env_path)
    except ConfigError:
        config = None

    JevMailConfigApp(config_path, env_path, config).run()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    return _run(args, watch=False)


def cmd_watch(args: argparse.Namespace) -> int:
    return _run(args, watch=True)


def _run(args: argparse.Namespace, watch: bool) -> int:
    config_path, env_path = _paths(args)
    try:
        config = load_config(config_path, env_path)
        client = get_jev_client(config.jev)
    except (ConfigError, ProviderError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if watch:
        print(f"watching {config.mailbox.folder}@{config.mailbox.host} (ctrl-c to stop)...")
    try:
        with Mailbox(config.mailbox) as mailbox:
            while True:
                _process_unprocessed(mailbox, client, config, args.dry_run)
                if not watch:
                    return 0
                if mailbox.supports_idle():
                    mailbox.idle()
                    mailbox.idle_check(timeout=min(config.mailbox.poll_interval_seconds, 600))
                    mailbox.idle_done()
                else:
                    time.sleep(config.mailbox.poll_interval_seconds)
    except (OSError, imaplib.IMAP4.error) as exc:
        print(f"error: {_mailbox_error_message(exc, config)}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jev-mail", description="Classify your inbox with Jev.")
    parser.set_defaults(dry_run=False)
    parser.add_argument("--dir", default=".", help="directory holding config.yaml / .env (default: cwd)")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("configure", help="open the TUI to build/edit config.yaml")

    run_parser = subparsers.add_parser("run", help="classify unprocessed mail once and exit")
    run_parser.add_argument("--dry-run", action="store_true", help="classify and print, without applying any action")

    watch_parser = subparsers.add_parser("watch", help="keep classifying new mail as it arrives")
    watch_parser.add_argument("--dry-run", action="store_true", help="classify and print, without applying any action")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    config_path, _ = _paths(args)

    if args.command is None:
        args.command = "configure" if not config_path.exists() else "run"

    commands = {"configure": cmd_configure, "run": cmd_run, "watch": cmd_watch}
    sys.exit(commands[args.command](args))


if __name__ == "__main__":
    main()
