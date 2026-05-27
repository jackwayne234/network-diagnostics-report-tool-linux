from PySide6.QtWidgets import QApplication, QPushButton

from net_troubleshooter.core.models import CommandResult, ResultStatus
from net_troubleshooter.gui.widgets import ResultCard


def get_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_failed_result_card_shows_retry_button_and_calls_callback():
    get_app()
    calls = []
    result = CommandResult(
        name="Ping example.com",
        command="ping",
        args=["example.com"],
        status=ResultStatus.FAIL,
        summary="Ping failed.",
    )

    card = ResultCard(result, retry_callback=lambda: calls.append("retried"))

    retry_buttons = [button for button in card.findChildren(QPushButton) if button.text() == "Retry this check"]
    assert len(retry_buttons) == 1
    retry_buttons[0].click()
    assert calls == ["retried"]


def test_passed_result_card_hides_retry_button_even_with_callback():
    get_app()
    result = CommandResult(
        name="Ping example.com",
        command="ping",
        args=["example.com"],
        status=ResultStatus.PASS,
        summary="Ping passed.",
    )

    card = ResultCard(result, retry_callback=lambda: None)

    retry_buttons = [button for button in card.findChildren(QPushButton) if button.text() == "Retry this check"]
    assert retry_buttons == []


def test_timed_out_result_card_shows_retry_button():
    get_app()
    result = CommandResult(
        name="Trace route example.com",
        command="tracepath",
        args=["example.com"],
        status=ResultStatus.WARNING,
        summary="Timed out.",
        timed_out=True,
    )

    card = ResultCard(result, retry_callback=lambda: None)

    retry_buttons = [button for button in card.findChildren(QPushButton) if button.text() == "Retry this check"]
    assert len(retry_buttons) == 1
