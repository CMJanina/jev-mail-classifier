from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static

from jev_mail.config import MailboxConfig


class MailboxScreen(Screen[MailboxConfig]):
    """Second screen: which mailbox/folder to watch. Credentials already live
    in .env from the previous screen -- only non-secret settings live here."""

    def __init__(self, mailbox: MailboxConfig):
        super().__init__()
        self._mailbox = mailbox

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("Step 2/3 -- Mailbox", classes="title")
            yield Label("IMAP host")
            yield Input(value=self._mailbox.host, placeholder="imap.gmail.com", id="host")
            yield Label("Port")
            yield Input(value=str(self._mailbox.port), id="port")
            yield Label("Folder to watch")
            yield Input(value=self._mailbox.folder, id="folder")
            yield Label("Poll interval in seconds (used by `watch` if the server has no IDLE support)")
            yield Input(value=str(self._mailbox.poll_interval_seconds), id="poll_interval")
            yield Label("Max emails to classify per run/poll (caps cost and time on a big backlog)")
            yield Input(value=str(self._mailbox.max_emails_per_run), id="max_emails_per_run")
            yield Button("Continue", id="continue", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "continue":
            return
        self.dismiss(
            MailboxConfig(
                host=self.query_one("#host", Input).value.strip(),
                port=int(self.query_one("#port", Input).value or 993),
                username=self._mailbox.username,
                password=self._mailbox.password,
                folder=self.query_one("#folder", Input).value.strip() or "INBOX",
                poll_interval_seconds=int(self.query_one("#poll_interval", Input).value or 60),
                max_emails_per_run=int(self.query_one("#max_emails_per_run", Input).value or 25),
            )
        )
