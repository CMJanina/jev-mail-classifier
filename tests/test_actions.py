from unittest.mock import MagicMock

import httpx
import pytest

from jev_mail.actions import run_action
from jev_mail.config import Action
from jev_mail.mailbox import Email

MAIL = Email(uid=1, subject="Hello", body="World")


@pytest.mark.parametrize(
    "action,expected_call",
    [
        (Action(type="tag", value="Invoice"), ("add_tag", (1, "Invoice"))),
        (Action(type="move", folder="Invoices"), ("move", (1, "Invoices"))),
        (Action(type="flag"), ("set_flag", (1, True))),
        (Action(type="unflag"), ("set_flag", (1, False))),
        (Action(type="mark_read"), ("set_seen", (1, True))),
        (Action(type="mark_unread"), ("set_seen", (1, False))),
    ],
)
def test_run_action_dispatches_to_mailbox(action, expected_call):
    mailbox = MagicMock()
    run_action(mailbox, MAIL, action, category_name="invoice", probability=0.9)
    method_name, args = expected_call
    getattr(mailbox, method_name).assert_called_once_with(*args)


def test_run_action_webhook_posts_json(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json

    monkeypatch.setattr(httpx, "post", fake_post)
    mailbox = MagicMock()

    run_action(mailbox, MAIL, Action(type="webhook", url="https://hooks.example.com/x"), "urgent", 0.87)

    assert captured["url"] == "https://hooks.example.com/x"
    assert captured["json"] == {"category": "urgent", "probability": 0.87, "subject": "Hello"}


def test_run_action_unknown_type_raises():
    with pytest.raises(ValueError):
        run_action(MagicMock(), MAIL, Action(type="bogus"), "invoice", 0.9)
