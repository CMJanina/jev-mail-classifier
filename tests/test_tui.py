from textual.widgets import Checkbox, Input

from jev_mail.config import load_config
from jev_mail.tui.app import JevMailConfigApp


async def test_full_configure_flow_writes_env_and_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    env_path = tmp_path / ".env"
    app = JevMailConfigApp(config_path, env_path)

    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        # Screen 1: credentials
        pilot.app.screen.query_one("#openrouter_key", Input).value = "or-test-key"
        pilot.app.screen.query_one("#imap_username", Input).value = "me@example.com"
        pilot.app.screen.query_one("#imap_password", Input).value = "hunter2"
        await pilot.click("#continue")
        await pilot.pause()

        # Screen 2: mailbox
        pilot.app.screen.query_one("#host", Input).value = "imap.example.com"
        pilot.app.screen.query_one("#folder", Input).value = "INBOX"
        await pilot.click("#continue")
        await pilot.pause()

        # Screen 3: categories -- add one
        await pilot.press("a")
        await pilot.pause()
        pilot.app.screen.query_one("#name", Input).value = "invoice"
        pilot.app.screen.query_one("#description", Input).value = "Invoice or billing"
        pilot.app.screen.query_one("#cb_tag", Checkbox).value = True
        pilot.app.screen.query_one("#tag_value", Input).value = "Invoice"
        await pilot.click("#save")

        assert len(app.config.categories) == 1
        assert app.config.categories[0].name == "invoice"

        await pilot.press("s")

    assert env_path.exists()
    assert "OPENROUTER_API_KEY=or-test-key" in env_path.read_text()
    assert "IMAP_USERNAME=me@example.com" in env_path.read_text()

    assert config_path.exists()
    reloaded = load_config(config_path, env_path)
    assert reloaded.mailbox.host == "imap.example.com"
    assert reloaded.categories[0].name == "invoice"
    assert reloaded.categories[0].actions[0].type == "tag"
    assert reloaded.categories[0].actions[0].value == "Invoice"


async def test_delete_category(tmp_path):
    from jev_mail.config import Action, AppConfig, Category, JevSettings, MailboxConfig

    config = AppConfig(
        mailbox=MailboxConfig(host="imap.example.com"),
        jev=JevSettings(),
        categories=[Category(name="spam", description="Spam", actions=[Action(type="move", folder="Spam")])],
    )
    app = JevMailConfigApp(tmp_path / "config.yaml", tmp_path / ".env", config)

    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        await pilot.click("#continue")  # credentials -> mailbox
        await pilot.click("#continue")  # mailbox -> categories

        list_view = pilot.app.screen.query_one("#category_list")
        list_view.index = 0
        await pilot.press("d")

        assert app.config.categories == []


async def test_cancel_edit_does_not_add_category(tmp_path):
    app = JevMailConfigApp(tmp_path / "config.yaml", tmp_path / ".env")

    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        await pilot.click("#continue")
        await pilot.click("#continue")

        await pilot.press("a")
        await pilot.click("#cancel")

        assert app.config.categories == []
