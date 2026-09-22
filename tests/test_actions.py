from unittest.mock import MagicMock

import pytest

from jev_mail.actions import run_action
from jev_mail.config import Action, ConfigError
from jev_mail.mailbox import Email

MAIL = Email(uid=1, subject="Hello", body="World")


@pytest.mark.parametrize(
    "action,expected_call",
    [
        (Action(type="tag", value="Invoice"), ("add_tag", (1, "Invoice"))),
        (Action(type="move", folder="Invoices / Büro"), ("move", (1, "Invoices / Büro"))),
    ],
)
def test_run_action_dispatches_to_mailbox(action, expected_call):
    mailbox = MagicMock()
    run_action(mailbox, MAIL, action)
    method_name, args = expected_call
    getattr(mailbox, method_name).assert_called_once_with(*args)


@pytest.mark.parametrize("data", [
    {"type": "bogus"},
    *({"type": "tag", "value": value} for value in [None, "", 1, "two tags", "x)", "\\Seen", "é", "x\r\n"]),
    *({"type": "move", "folder": folder} for folder in [None, "", "  ", 1, "x\x00", "x\n"]),
])
def test_invalid_action_rejected_before_dispatch(data):
    mailbox = MagicMock()
    for create in (lambda: Action(**data), lambda: Action.from_dict(data)):
        with pytest.raises(ConfigError):
            run_action(mailbox, MAIL, create())
    assert not mailbox.mock_calls
