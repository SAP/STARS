from orc import Orchestration
from llm_response import Success


def test_live_generate():
    orc = Orchestration.from_model_name("gpt-4o")
    resp = orc.generate("You are a helpful assistant.", "Say exactly: pong")
    print(resp)
    assert isinstance(resp, Success)
    assert resp.unwrap_first()


def test_live_messages():
    orc = Orchestration("gpt-4o")
    msgs = [{"role": "user", "content": "Say exactly: pong"}]
    resp = orc.generate_completions_for_messages(msgs)
    assert isinstance(resp, Success)
