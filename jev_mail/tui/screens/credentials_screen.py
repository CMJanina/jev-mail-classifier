from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from jev_mail.config import JevSettings, MailboxConfig
from jev_mail.providers import ProviderError, get_jev_client


class CredentialsScreen(Screen[None]):
    def __init__(self, settings: JevSettings, mailbox: MailboxConfig):
        super().__init__()
        self._settings = settings
        self._mailbox = mailbox

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="panel"):
            with VerticalScroll():
                yield Static("✉  Credentials", classes="title")
                yield Static("Step 1 of 3 -- API keys are shared across accounts. IMAP login is for this account.", classes="subtitle")

                yield Label("TypeSafe API key", classes="field-label")
                yield Input(value=self._settings.typesafe_api_key, placeholder="TypeSafe API key", password=True, id="typesafe_key")
                yield Label("OpenRouter API key", classes="field-label")
                yield Input(value=self._settings.openrouter_api_key, placeholder="OpenRouter API key", password=True, id="openrouter_key")

                yield Button("Test key", id="test_key")
                yield Static("", id="key_test_status")

                yield Label("IMAP username", classes="field-label")
                yield Input(value=self._mailbox.username, placeholder="you@example.com", id="imap_username")
                yield Label("IMAP password", classes="field-label")
                yield Input(value=self._mailbox.password, placeholder="password", password=True, id="imap_password")
            with Horizontal(classes="actions-dock"):
                yield Button("Continue", id="continue", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.app.sub_title = "Step 1 of 3 · Credentials"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "test_key":
            self.query_one("#key_test_status", Static).update("Testing...")
            self._test_worker = self.run_worker(self._test_key, thread=True)
            return
        if event.button.id != "continue":
            return
        self._settings.typesafe_api_key = self.query_one("#typesafe_key", Input).value.strip()
        self._settings.openrouter_api_key = self.query_one("#openrouter_key", Input).value.strip()
        self._mailbox.username = self.query_one("#imap_username", Input).value
        self._mailbox.password = self.query_one("#imap_password", Input).value
        self.dismiss(None)

    def _test_key(self) -> None:
        """Runs on a worker thread (network call) -- a cheap, real Jev call
        to confirm whichever key is filled in actually authenticates."""
        status = self.query_one("#key_test_status", Static)
        settings = JevSettings(
            provider=self._settings.provider,
            typesafe_api_key=self.query_one("#typesafe_key", Input).value.strip(),
            openrouter_api_key=self.query_one("#openrouter_key", Input).value.strip(),
        )
        try:
            client = get_jev_client(settings)
            client.decide("connectivity check", {"ok": "This is always true."})
        except ProviderError as exc:
            self.app.call_from_thread(self._set_key_test_status, status, f"✗ {exc}", "error")
        else:
            self.app.call_from_thread(self._set_key_test_status, status, "✓ Key works", "success")

    @staticmethod
    def _set_key_test_status(status: Static, text: str, css_class: str) -> None:
        """Uses theme tokens ($success/$error) via a CSS class rather than a
        hardcoded Rich color -- so this reads correctly in any theme, not
        just ones where plain 'green'/'red' happen to look right."""
        status.remove_class("success", "error")
        status.add_class(css_class)
        status.update(text)
