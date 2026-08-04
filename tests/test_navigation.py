from streamlit.testing.v1 import AppTest


def test_sidebar_navigation_switches_between_modes():
    app = AppTest.from_file("app.py", default_timeout=60)
    app.run(timeout=60)

    assert app.session_state["current_mode"] == "home"
    assert app.radio[0].value == "home"

    app.radio[0].set_value("update").run(timeout=60)
    assert app.session_state["current_mode"] == "update"
    assert app.radio[0].value == "update"

    app.radio[0].set_value("generate").run(timeout=60)
    assert app.session_state["current_mode"] == "generate"
    assert app.radio[0].value == "generate"

    app.radio[0].set_value("home").run(timeout=60)
    assert app.session_state["current_mode"] == "home"
    assert app.radio[0].value == "home"
