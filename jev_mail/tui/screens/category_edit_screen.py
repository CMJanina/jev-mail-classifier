from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, Static

from jev_mail.config import Action, Category


class CategoryEditScreen(Screen[Category | None]):
    """Add or edit one category: what Jev looks for, and up to one of each
    action type to take when it matches. `None` category means "new"."""

    def __init__(self, category: Category | None):
        super().__init__()
        self._category = category

    def compose(self) -> ComposeResult:
        c = self._category
        actions_by_type = {a.type: a for a in (c.actions if c else [])}

        yield Header()
        with Container(id="panel"):
            with VerticalScroll():
                yield Static("Add category" if c is None else f"Edit: {c.name}", classes="title")
                yield Label("Name (short, no spaces -- also used as the tag keyword)", classes="field-label")
                yield Input(value=c.name if c else "", id="name")
                yield Label("Description (what Jev should look for)", classes="field-label")
                yield Input(value=c.description if c else "", placeholder="Invoice, billing statement, or payment request", id="description")
                yield Label("Threshold override 0-1 (blank = use the default)", classes="field-label")
                yield Input(value=str(c.threshold) if c and c.threshold is not None else "", id="threshold")

                yield Static("Actions when matched", classes="subtitle")
                yield Checkbox("Tag", value="tag" in actions_by_type, id="cb_tag")
                yield Input(value=actions_by_type["tag"].value if "tag" in actions_by_type else "", placeholder="tag value", id="tag_value")

                yield Checkbox("Move to folder", value="move" in actions_by_type, id="cb_move")
                yield Input(value=actions_by_type["move"].folder if "move" in actions_by_type else "", placeholder="folder name", id="move_folder")
            with Horizontal(classes="actions-dock"):
                yield Button("Save", id="save", variant="primary")
                yield Button("Cancel", id="cancel")
        yield Footer()

    def on_mount(self) -> None:
        self.app.sub_title = "Add category" if self._category is None else f"Edit {self._category.name}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        if event.button.id != "save":
            return

        actions = []
        if self.query_one("#cb_tag", Checkbox).value:
            value = self.query_one("#tag_value", Input).value.strip() or self.query_one("#name", Input).value.strip()
            actions.append(Action(type="tag", value=value))
        if self.query_one("#cb_move", Checkbox).value:
            actions.append(Action(type="move", folder=self.query_one("#move_folder", Input).value.strip()))

        threshold_raw = self.query_one("#threshold", Input).value.strip()
        self.dismiss(
            Category(
                name=self.query_one("#name", Input).value.strip(),
                description=self.query_one("#description", Input).value.strip(),
                threshold=float(threshold_raw) if threshold_raw else None,
                actions=actions,
            )
        )
