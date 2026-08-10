from streamlit.testing.v1 import AppTest


def test_sidebar_navigation_switches_between_modes():
    app = AppTest.from_file("../app.py", default_timeout=60)
    app.run(timeout=60)

    assert app.session_state["current_mode"] == "home"
    assert app.radio[0].value == "home"


def test_home_card_navigation_uses_widget_callbacks():
    app = AppTest.from_file("../app.py", default_timeout=60)
    app.run(timeout=60)

    update_button = next(button for button in app.button if button.label == "进入更新知识库")
    update_button.click().run(timeout=60)

    assert app.session_state["current_mode"] == "update"
    assert app.session_state["navigation_mode"] == "update"
    assert not app.exception

    app.radio[0].set_value("update").run(timeout=60)
    assert app.session_state["current_mode"] == "update"
    assert app.radio[0].value == "update"

    app.radio[0].set_value("generate").run(timeout=60)
    assert app.session_state["current_mode"] == "generate"
    assert app.radio[0].value == "generate"

    app.radio[0].set_value("home").run(timeout=60)
    assert app.session_state["current_mode"] == "home"
    assert app.radio[0].value == "home"


def test_home_page_hides_dev_status_and_raw_card_html():
    app = AppTest.from_file("../app.py", default_timeout=60)
    app.run(timeout=60)

    user_markdown = [
        markdown.value
        for markdown in app.markdown
        if not markdown.value.strip().startswith("<style>")
    ]
    visible_text = "\n".join(
        [
            *user_markdown,
            *[caption.value for caption in app.caption],
            *[subheader.value for subheader in app.subheader],
        ]
    )

    assert "V0.8.0-dev" not in visible_text
    assert "可用" not in visible_text
    assert "建设中" not in visible_text
    assert "autorag-card-body" not in visible_text
    assert "<div class=\"autorag-card\"" not in visible_text
    assert not app.exception
