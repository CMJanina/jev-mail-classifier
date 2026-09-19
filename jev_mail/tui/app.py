from __future__ import annotations

from pathlib import Path

from textual.app import App

from jev_mail.config import AppConfig, JevSettings, MailboxConfig, save_config
from jev_mail.tui.screens.categories_screen import CategoriesScreen
from jev_mail.tui.screens.credentials_screen import CredentialsScreen
from jev_mail.tui.screens.mailbox_screen import MailboxScreen

CSS = """
Screen {
    align: center middle;
    background: $surface;
}

#panel {
    width: 96;
    max-width: 96%;
    height: 90%;
    border: round $accent;
    background: $panel;
    padding: 1 3;
}

#panel > VerticalScroll {
    height: 1fr;
}

/* scrollbar-* properties don't inherit from an ancestor -- they have to be
   set on the actual scrollable widget, hence the type selectors here rather
   than on Screen/#panel. */
VerticalScroll, ListView {
    scrollbar-size-vertical: 1;
    scrollbar-size-horizontal: 1;
    scrollbar-color: $accent 60%;
    scrollbar-color-hover: $accent;
    scrollbar-color-active: $accent;
    scrollbar-background: $panel;
    scrollbar-background-hover: $panel;
    scrollbar-background-active: $panel;
}

/* A plain Horizontal defaults to height:1fr, which breaks height:auto
   measurement on its parent (e.g. the docked action bar) -- pin it down. */
.actions-dock Horizontal {
    height: auto;
}

.title {
    text-style: bold;
    color: $accent;
    padding: 0 0 1 0;
}

.subtitle {
    color: $text-muted;
    padding: 0 0 1 0;
}

.hint {
    color: $text-muted;
    padding: 1 0;
}

.error {
    color: $error;
    text-style: bold;
    padding: 1 0;
}

.success {
    color: $success;
    text-style: bold;
    padding: 1 0;
}

.field-label {
    color: $text-muted;
    padding: 1 0 0 0;
}

#test_key {
    margin-top: 1;
}

#key_test_status {
    width: 1fr;
    padding: 1 0;
}

.actions-dock {
    dock: bottom;
    height: auto;
    padding-top: 1;
    border-top: solid $accent 30%;
}

.actions-dock Button {
    margin-right: 1;
}

#category_list {
    border: round $accent 50%;
    background: $surface;
    height: auto;
    max-height: 16;
    margin: 1 0;
}

#category_list > ListItem {
    padding: 0 1;
}

#category_list > ListItem.--highlight {
    background: $accent 25%;
}

#empty_categories {
    color: $text-muted;
    text-style: italic;
    padding: 1;
}
"""


class JevMailConfigApp(App):
    """Credentials -> Mailbox -> Categories, then writes config.yaml (and,
    via the credentials screen, .env). Each step's Continue/Save dismisses
    with the collected data; the app wires results into `self.config`."""

    TITLE = "jev-mail"
    CSS = CSS

    def __init__(self, config_path: Path, env_path: Path, config: AppConfig | None = None):
        super().__init__()
        self.theme = "gruvbox"
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
