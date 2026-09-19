from __future__ import annotations

from pathlib import Path

from textual.app import App

from jev_mail.config import AppConfig, JevSettings, MailboxConfig, save_config
from jev_mail.tui.screens.categories_screen import CategoriesScreen
from jev_mail.tui.screens.credentials_screen import CredentialsScreen
from jev_mail.tui.screens.mailbox_screen import MailboxScreen

CSS = """
.title {
    text-style: bold;
    padding: 1 0;
}
.hint {
    color: $text-muted;
    padding: 1 0;
}
.error {
    color: red;
    padding: 1 0;
}
"""


class JevMailConfigApp(App):
    """Credentials -> Mailbox -> Categories, then writes config.yaml (and,
    via the credentials screen, .env). Each step's Continue/Save dismisses
    with the collected data; the app wires results into `self.config`."""

    TITLE = "jev-mail configure"
    CSS = CSS

    def __init__(self, config_path: Path, env_path: Path, config: AppConfig | None = None):
        super().__init__()
        self.config_path = config_path
        self.env_path = env_path
        self.config = config or AppConfig(mailbox=MailboxConfig(host=""), jev=JevSettings(), categories=[])

    def on_mount(self) -> None:
        self.push_screen(CredentialsScreen(self.env_path), self._after_credentials)

    def _after_credentials(self, _: None) -> None:
        self.push_screen(MailboxScreen(self.config.mailbox), self._after_mailbox)

    def _after_mailbox(self, mailbox: MailboxConfig) -> None:
        self.config.mailbox = mailbox
        self.push_screen(CategoriesScreen(self.config), self._after_categories)

    def _after_categories(self, _: None) -> None:
        save_config(self.config, self.config_path)
        self.exit(message=f"Saved {self.config_path}")
