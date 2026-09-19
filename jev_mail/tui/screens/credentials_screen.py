from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static

from jev_mail.config import read_env, save_env


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
        with VerticalScroll():
            yield Static("Step 1/3 -- Credentials", classes="title")
            if existing:
                yield Static("Already configured -- shown pre-filled below. Edit only what you want to change.", classes="hint")
            yield Static("Paste ONE Jev key (whichever you have) and your IMAP login.")
            yield Label("TypeSafe API key")
            yield Input(value=existing.get("TYPESAFE_API_KEY", ""), placeholder="TYPESAFE_API_KEY", password=True, id="typesafe_key")
            yield Label("OpenRouter API key")
            yield Input(value=existing.get("OPENROUTER_API_KEY", ""), placeholder="OPENROUTER_API_KEY", password=True, id="openrouter_key")
            yield Label("Vercel AI Gateway key")
            yield Input(value=existing.get("AI_GATEWAY_API_KEY", ""), placeholder="AI_GATEWAY_API_KEY", password=True, id="vercel_key")
            yield Label("IMAP username")
            yield Input(value=existing.get("IMAP_USERNAME", ""), placeholder="you@example.com", id="imap_username")
            yield Label("IMAP password (NOT your regular password if 2FA is on -- see below)")
            yield Input(value=existing.get("IMAP_PASSWORD", ""), placeholder="app password", password=True, id="imap_password")
            yield Static(
                "Need an app password? Gmail: myaccount.google.com/apppasswords "
                "(enable IMAP first in Gmail Settings -> Forwarding and POP/IMAP). "
                "Outlook: account.microsoft.com/security -> App passwords. "
                "Full walkthrough: see the README's 'Getting your IMAP username & password' section.",
                classes="hint",
            )
            yield Button("Continue", id="continue", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
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
