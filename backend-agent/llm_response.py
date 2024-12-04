
from dataclasses import dataclass, asdict
from typing import Any


class LLMResponse():
    def unwrap(self, fail_result: Any = None) -> list[str] | Any:
        """
        Return the response if it is successful, otherwise return None.
        """
        if (isinstance(self, Success)):
            return self.text
        else:
            return fail_result

    def unwrap_first(self) -> str | None:
        unwrapped = self.unwrap()
        if unwrapped:
            return unwrapped[0]
        return unwrapped

    def to_str_list(self):
        match self:
            case Success(t):
                return t
            case Error(e):
                return f'Error when querying llm: {e}'
            case Filtered(f):
                return f'Filtered by an LLM defense: {f}'

    def to_dict(self):
        return asdict(self)


@dataclass
class Success(LLMResponse):
    """
    The LLM responded successfully.
    """
    text: list[str]

    def to_dict(self):
        return {
            'type': 'Success',
            'text': self.text
        }


@dataclass
class Error(LLMResponse):
    """
    The LLM did not respond successfully.
    """
    reason: Any

    def to_dict(self):
        return {
            'type': 'Error',
            'reason': str(self.reason)
        }


@dataclass
class Filtered(LLMResponse):
    """
    The prompt or the response was filtered by an LLM defense mechanism.
    """
    reason: Any

    def to_dict(self):
        return {
            'type': 'Filtered',
            'reason': str(self.reason)
        }
