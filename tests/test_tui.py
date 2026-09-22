import pytest

from textual.containers import VerticalScroll
from textual.widgets import Checkbox, Input, Static

from jev_mail.config import AppConfig, JevSettings, MailboxConfig, load_config, save_config
from jev_mail.providers import ProviderError
from jev_mail.tui.app import JevMailConfigApp
from jev_mail.tui.screens import credentials_screen as credentials_screen_module


async def test_every_screen_scroll_area_actually_gets_space(tmp_path):
    """Regression test: a plain Horizontal defaults to height:1fr, which once
    silently broke height:auto on '.actions-dock' and squeezed the sibling
    VerticalScroll down to 1 row -- fields were still settable via `.value =`
    (bypassing layout entirely) so earlier tests didn't catch it. This checks
    real layout, not just that a value round-trips."""
    app = JevMailConfigApp(tmp_path / "config.yaml")
    async with app.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        for screen_name in ["credentials", "mailbox"]:
            scroll = pilot.app.screen.query_one(VerticalScroll)
            assert scroll.region.height > 10, f"{screen_name} screen's scroll area collapsed: {scroll.region}"
            if screen_name == "mailbox":
                pilot.app.screen.query_one("#host", Input).value = "imap.example.com"
            await pilot.click("#continue")
            await pilot.pause()


async def test_full_configure_flow_writes_credentials_in_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    env_path = tmp_path / ".env"
    app = JevMailConfigApp(config_path)

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

    assert not env_path.exists()

    assert config_path.exists()
    reloaded = load_config(config_path)
    assert reloaded.jev.openrouter_api_key == "or-test-key"
    assert reloaded.accounts["default"].username == "me@example.com"
    assert reloaded.accounts["default"].password == "hunter2"
    assert reloaded.accounts["default"].host == "imap.example.com"
    assert reloaded.categories[0].name == "invoice"
    assert reloaded.categories[0].actions[0].type == "tag"
    assert reloaded.categories[0].actions[0].value == "Invoice"


async def test_edit_account_preserves_other_account_and_clears_key(tmp_path):
    config_path = tmp_path / "config.yaml"
    config = AppConfig(
        accounts={
            "personal": MailboxConfig(host="imap.personal.test", username="personal", password="keep"),
            "work": MailboxConfig(host="imap.work.test", username="work", password="old"),
        },
        jev=JevSettings(openrouter_api_key="already-saved"),
        categories=[],
    )
    save_config(config, config_path)
    app = JevMailConfigApp(config_path, load_config(config_path), "work")
    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        assert pilot.app.screen.query_one("#openrouter_key", Input).value == "already-saved"
        assert pilot.app.screen.query_one("#imap_username", Input).value == "work"
        pilot.app.screen.query_one("#openrouter_key", Input).value = ""
        pilot.app.screen.query_one("#imap_password", Input).value = "new"
        await pilot.click("#continue")
        assert load_config(config_path).accounts["work"].password == "old"
        await pilot.click("#continue")
        await pilot.press("s")

    reloaded = load_config(config_path)
    assert reloaded.accounts["personal"] == config.accounts["personal"]
    assert reloaded.accounts["work"].password == "new"
    assert reloaded.jev.openrouter_api_key == ""


async def test_test_key_button_shows_green_tick_on_success(monkeypatch, tmp_path):
    fake_client = type("FakeClient", (), {"decide": lambda self, state, categories: {"ok": 0.99}})()
    monkeypatch.setattr(credentials_screen_module, "get_jev_client", lambda settings: fake_client)

    app = JevMailConfigApp(tmp_path / "config.yaml")
    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        pilot.app.screen.query_one("#openrouter_key", Input).value = "or-test-key"
        await pilot.click("#test_key")
        await pilot.app.screen._test_worker.wait()
        await pilot.pause()

        status = pilot.app.screen.query_one("#key_test_status", Static).content
        assert "Key works" in status


async def test_test_key_button_shows_error_on_failure(monkeypatch, tmp_path):
    def raise_provider_error(settings):
        raise ProviderError("no Jev API key found")

    monkeypatch.setattr(credentials_screen_module, "get_jev_client", raise_provider_error)

    app = JevMailConfigApp(tmp_path / "config.yaml")
    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        await pilot.click("#test_key")
        await pilot.app.screen._test_worker.wait()
        await pilot.pause()

        status = pilot.app.screen.query_one("#key_test_status", Static).content
        assert "no Jev API key found" in status


async def test_delete_category(tmp_path):
    from jev_mail.config import Action, AppConfig, Category, JevSettings, MailboxConfig

    config = AppConfig(
        accounts={"default": MailboxConfig(host="imap.example.com")},
        jev=JevSettings(),
        categories=[Category(name="spam", description="Spam", actions=[Action(type="move", folder="Spam")])],
    )
    app = JevMailConfigApp(tmp_path / "config.yaml", config)

    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        await pilot.click("#continue")  # credentials -> mailbox
        await pilot.click("#continue")  # mailbox -> categories

        list_view = pilot.app.screen.query_one("#category_list")
        list_view.index = 0
        await pilot.press("d")

        assert app.config.categories == []


async def test_cancel_edit_does_not_add_category(tmp_path):
    app = JevMailConfigApp(tmp_path / "config.yaml")

    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        await pilot.click("#continue")
        await pilot.pause()
        pilot.app.screen.query_one("#host", Input).value = "imap.example.com"
        await pilot.click("#continue")

        await pilot.press("a")
        await pilot.click("#cancel")

        assert app.config.categories == []


async def test_mailbox_screen_rejects_empty_host(tmp_path):
    app = JevMailConfigApp(tmp_path / "config.yaml")

    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        await pilot.click("#continue")  # credentials -> mailbox
        await pilot.pause()

        await pilot.click("#continue")  # host still blank

        assert pilot.app.screen.query_one("#host", Input) is not None
        assert "required" in pilot.app.screen.query_one("#mailbox_error", Static).content

        # Button's press-animation guard ignores a second click on the same
        # button within ~0.2s (Textual's `active_effect_duration`) -- wait it out.
        await pilot.pause(0.3)
        pilot.app.screen.query_one("#host", Input).value = "imap.example.com"
        await pilot.click("#continue")
        await pilot.pause()

        assert app.config.accounts["default"].host == "imap.example.com"


@pytest.mark.parametrize("field", ["port", "poll_interval", "max_emails_per_run"])
@pytest.mark.parametrize("value", ["0", "-1", "bad"])
async def test_mailbox_numbers_can_be_corrected_before_saving(tmp_path, field, value):
    path = tmp_path / "config.yaml"
    app = JevMailConfigApp(path)
    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.click("#continue")
        app.screen.query_one("#host", Input).value = "imap.test"
        app.screen.query_one(f"#{field}", Input).value = value
        await pilot.click("#continue")
        assert "positive integer" in app.screen.query_one("#mailbox_error", Static).content
        assert not path.exists()

        await pilot.pause(0.3)
        app.screen.query_one(f"#{field}", Input).value = "10"
        await pilot.click("#continue")
        await pilot.press("s")

    mailbox = load_config(path).accounts["default"]
    key = "poll_interval_seconds" if field == "poll_interval" else field
    assert getattr(mailbox, key) == 10
