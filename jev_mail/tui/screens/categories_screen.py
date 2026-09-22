from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from jev_mail.config import AppConfig, Category
from jev_mail.tui.screens.category_edit_screen import CategoryEditScreen


class CategoriesScreen(Screen[None]):
    """Hub screen: the category list, with add/edit/delete and a save-and-exit
    binding. Dismissing here (via `s`) tells the app to write config.yaml."""

    BINDINGS = [
        Binding("a", "add_category", "Add"),
        Binding("e", "edit_category", "Edit"),
        Binding("d", "delete_category", "Delete"),
        Binding("s", "save", "Save & exit"),
    ]

    def __init__(self, config: AppConfig):
        super().__init__()
        self._config = config

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="panel"):
            yield Static("\U0001f5c2️  Categories", classes="title")
            yield Static("Step 3 of 3 -- a add · e edit · d delete · s save & exit", classes="subtitle")
            yield ListView(id="category_list")
        yield Footer()

    def on_mount(self) -> None:
        self.app.sub_title = "Step 3 of 3 · Categories"
        self._refresh_list()

    def _refresh_list(self) -> None:
        list_view = self.query_one("#category_list", ListView)
        list_view.clear()
        if not self._config.categories:
            list_view.append(ListItem(Label("No categories yet -- press [b]a[/b] to add one.", id="empty_categories")))
            return
        for category in self._config.categories:
            n_actions = len(category.actions)
            plural = "action" if n_actions == 1 else "actions"
            list_view.append(
                ListItem(
                    Label(
                        f"[b]{category.name}[/b] [dim]-- {category.description}[/dim]  "
                        f"[$accent]({n_actions} {plural})[/]"
                    )
                )
            )

    def _selected_index(self) -> int | None:
        if not self._config.categories:
            return None
        return self.query_one("#category_list", ListView).index

    def action_add_category(self) -> None:
        self.app.push_screen(CategoryEditScreen(None), self._on_add_done)

    def action_edit_category(self) -> None:
        index = self._selected_index()
        if index is None:
            return

        def _on_edit_done(result: Category | None) -> None:
            if result is not None:
                self._config.categories[index] = result
                self._refresh_list()

        self.app.push_screen(CategoryEditScreen(self._config.categories[index]), _on_edit_done)

    def action_delete_category(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        del self._config.categories[index]
        self._refresh_list()

    def action_save(self) -> None:
        self.dismiss(None)

    def _on_add_done(self, result: Category | None) -> None:
        if result is not None:
            self._config.categories.append(result)
            self._refresh_list()
