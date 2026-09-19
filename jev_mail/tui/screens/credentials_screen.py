from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from jev_mail.config import JevSettings, read_env, save_env
from jev_mail.providers import ProviderError, get_jev_client


class CredentialsScreen(Screen[None]):
    """First screen: paste one Jev key and IMAP login. Writes straight to
    .env -- nothing here ever needs to be typed into config.yaml by hand.
    Pre-fills from any existing .env so re-running `configure` doesn't look
    like it forgot everything -- values are just shown masked, like a saved
    login form, and only overwritten if you actually change them."""

    def __init__(self, env_path: Path):
        super().__init__()
        self._env_path = env_path
        self._existing = read_env(env_path)

    def compose(self) -> ComposeResult:
        existing = self._existing
        yield Header()
        with Container(id="panel"):
            with VerticalScroll():
                yield Static("✉  Credentials", classes="title")
                yield Static("Step 1 of 3 -- paste ONE Jev key (whichever you have) and your IMAP login.", classes="subtitle")
                if existing:
                    yield Static("Already configured -- shown pre-filled below. Edit only what you want to change.", classes="hint")

                yield Label("TypeSafe API key", classes="field-label")
                yield Input(value=existing.get("TYPESAFE_API_KEY", ""), placeholder="TYPESAFE_API_KEY", password=True, id="typesafe_key")
                yield Label("OpenRouter API key", classes="field-label")
                yield Input(value=existing.get("OPENROUTER_API_KEY", ""), placeholder="OPENROUTER_API_KEY", password=True, id="openrouter_key")
                yield Label("Vercel AI Gateway key", classes="field-label")
                yield Input(value=existing.get("AI_GATEWAY_API_KEY", ""), placeholder="AI_GATEWAY_API_KEY", password=True, id="vercel_key")

                with Horizontal(classes="button-row"):
                    yield Static("", id="key_test_status")
                    yield Button("Test key", id="test_key")

                yield Label("IMAP username", classes="field-label")
                yield Input(value=existing.get("IMAP_USERNAME", ""), placeholder="you@example.com", id="imap_username")
                yield Label("IMAP password (NOT your regular password if 2FA is on -- see below)", classes="field-label")
                yield Input(value=existing.get("IMAP_PASSWORD", ""), placeholder="app password", password=True, id="imap_password")
                yield Static(
                    "Need an app password? Gmail: myaccount.google.com/apppasswords "
                    "(enable IMAP first in Gmail Settings -> Forwarding and POP/IMAP). "
                    "Outlook: account.microsoft.com/security -> App passwords. "
                    "Full walkthrough: see the README's 'Getting your IMAP username & password' section.",
                    classes="hint",
                )
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
        save_env(
            {
                "TYPESAFE_API_KEY": self.query_one("#typesafe_key", Input).value,
                "OPENROUTER_API_KEY": self.query_one("#openrouter_key", Input).value,
                "AI_GATEWAY_API_KEY": self.query_one("#vercel_key", Input).value,
                "IMAP_USERNAME": self.query_one("#imap_username", Input).value,
                "IMAP_PASSWORD": self.query_one("#imap_password", Input).value,
            },
            self._env_path,
        )
        self.dismiss(None)

    def _test_key(self) -> None:
        """Runs on a worker thread (network call) -- a cheap, real Jev call
        to confirm whichever key is filled in actually authenticates."""
        status = self.query_one("#key_test_status", Static)
        env = {
            "TYPESAFE_API_KEY": self.query_one("#typesafe_key", Input).value.strip(),
            "OPENROUTER_API_KEY": self.query_one("#openrouter_key", Input).value.strip(),
            "AI_GATEWAY_API_KEY": self.query_one("#vercel_key", Input).value.strip(),
        }
        try:
            client = get_jev_client(JevSettings(provider="auto"), env=env)
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
