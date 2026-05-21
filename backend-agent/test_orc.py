from unittest.mock import MagicMock, patch
from orc import Orchestration
from llm_response import Success, Error, Filtered


def _fake_result(text="hello"):
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    result = MagicMock()
    result.final_result.choices = [choice]
    return result


@patch("orc.OrchestrationService")
def test_generate_returns_success(MockService):
    MockService.return_value.run.return_value = _fake_result("ok")
    orc = Orchestration("gpt-4o")
    resp = orc.generate("You are helpful.", "What is 2+2?")
    assert isinstance(resp, Success)
    assert resp.unwrap_first() == "ok"


@patch("orc.OrchestrationService")
def test_generate_completions_for_messages(MockService):
    MockService.return_value.run.return_value = _fake_result("answer")
    orc = Orchestration("gpt-4o")
    msgs = [{"role": "system", "content": "Be helpful."},
            {"role": "user",   "content": "Hello"}]
    resp = orc.generate_completions_for_messages(msgs)
    assert isinstance(resp, Success)


@patch("orc.OrchestrationService")
def test_exception_becomes_error(MockService):
    MockService.return_value.run.side_effect = RuntimeError("boom")
    orc = Orchestration("gpt-4o")
    resp = orc.generate("", "test")
    assert isinstance(resp, Error)


@patch("orc.OrchestrationService")
def test_filtered_keyword_in_exception(MockService):
    MockService.return_value.run.side_effect = RuntimeError("content_filter triggered")
    orc = Orchestration("gpt-4o")
    resp = orc.generate("", "test")
    assert isinstance(resp, Filtered)


def test_from_model_name_unsupported_raises():
    try:
        Orchestration.from_model_name("not-a-real-model")
        assert False, "should have raised"
    except ValueError:
        pass


def test_get_supported_models():
    models = Orchestration.get_supported_models()
    assert "gpt-4o" in models
