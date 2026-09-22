from unittest.mock import MagicMock

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
    ],
)
def test_run_action_dispatches_to_mailbox(action, expected_call):
    mailbox = MagicMock()
    run_action(mailbox, MAIL, action)
    method_name, args = expected_call
    getattr(mailbox, method_name).assert_called_once_with(*args)


def test_run_action_unknown_type_raises():
    with pytest.raises(ValueError):
        run_action(MagicMock(), MAIL, Action(type="bogus"))
