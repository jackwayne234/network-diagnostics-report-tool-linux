from net_troubleshooter.core.runner import CommandRunner
from net_troubleshooter.core.models import ResultStatus


def test_missing_tool_returns_skipped_result():
    result = CommandRunner().run("Missing", "definitely-not-a-real-network-tool-xyz", [])
    assert result.status == ResultStatus.SKIPPED
    assert result.missing_tool is True
    assert "not installed" in result.summary


def test_runner_executes_non_shell_command():
    result = CommandRunner().run("Python version", "python3", ["--version"], timeout=5)
    assert result.status == ResultStatus.PASS
    assert result.exit_code == 0
    assert result.command == "python3"
