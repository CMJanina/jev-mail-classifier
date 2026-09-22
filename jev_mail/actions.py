from __future__ import annotations

from jev_mail.config import Action
from jev_mail.mailbox import Email, Mailbox


def run_action(mailbox: Mailbox, mail: Email, action: Action) -> None:
    if action.type == "tag":
        mailbox.add_tag(mail.uid, action.value)
    elif action.type == "move":
        mailbox.move(mail.uid, action.folder)
    else:
        raise ValueError(f"unknown action type: {action.type}")
