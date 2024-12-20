import abc
import logging
import os

from gen_ai_hub.proxy.core.proxy_clients import set_proxy_version

from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
from gen_ai_hub.proxy.native.openai import OpenAI as ProxyOpenAI
from gen_ai_hub.proxy.native.google_vertexai.clients import GenerativeModel
import httpx
from openai import OpenAI as OfficialOpenAI
from openai import InternalServerError
import ollama

from llm_response import Error, Filtered, LLMResponse, Success
from status import status

set_proxy_version('gen-ai-hub')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(status.trace_logging)

AICORE_MODELS = {
    'openai':
    [
        'gpt-4o',
        'gpt-4',
        'gpt-35-turbo',
        'gpt-35-turbo-0125',
        'gpt-35-turbo-16k',
        'gpt-4-32k',
        'gpt-4o-mini',
    ],
    'opensource':
    [
        'mistralai--mixtral-8x7b-instruct-v01',
        'meta--llama3.1-70b-instruct',
        'meta--llama3-70b-instruct'
    ],
    'vertexai':
    [
        'text-bison',
        'chat-bison',
        'gemini-1.0-pro',
        'gemini-1.5-pro',
        'gemini-1.5-flash'
    ],
    'ibm':
    [
        'ibm--granite-13b-chat'
    ]
}


class LLM(abc.ABC):
    """
    This is the abstract class used to create and access LLMs for pentesting.
    """

    _supported_models = []

    @classmethod
    def from_model_name(cls, model_name: str) -> 'LLM':
        """
        Create a specific LLM object from the name of the model.
        Useful because the user can specify only the name in the agent.
        """
        if 'gpt' in model_name:
            # The agent sometimes autocorrects gpt-35-turbo to gpt-3.5-turbo,
            # so we handle this behavior here.
            if model_name == 'gpt-3.5-turbo':
                model_name = 'gpt-35-turbo'
            return AICoreOpenAILLM(model_name)
        if model_name in AICORE_MODELS['opensource']:
            return AICoreOpenAILLM(model_name, False)
        if model_name in AICORE_MODELS['ibm']:
            # IBM models are compatible with OpenAI completion API
            return AICoreOpenAILLM(model_name)
        if model_name in AICORE_MODELS['vertexai']:
            return AICoreGoogleVertexLLM(model_name)
        if model_name == 'mistral':
            return LocalOpenAILLM(
                os.getenv('MISTRAL_MODEL_NAME', ''),
                api_key=os.getenv('MISTRAL_KEY', ''),
                base_url=os.getenv('MISTRAL_URL', ''),
                supports_openai_style_system_messages=False)

        # If a model is not found, as a last resource, it is looked up in a
        # possible local ollama instance. If it not even served there, then an
        # exception is raised because such model has either an incorrect name
        # or it has not been deployed.
        try:
            ollama.show(model_name)
            return OllamaLLM(model_name)
        except (ollama.ResponseError, httpx.ConnectError):
            raise ValueError(f'Model {model_name} not found')

    @classmethod
    def _calculate_list_of_supported_models(self) -> list[str]:
        """
        Get the list of supported models using AI Core, local Mistral and
        Ollama. Gathering deployments from AI Core takes a while, so the result
        of this method are cached.
        """
        client = get_proxy_client()
        models = [d.model_name for d in client.deployments]
        if os.getenv('MISTRAL_URL'):
            models.append('mistral')
        try:
            ollama_models = [m['name'] for m in ollama.list()['models']]
            return models + ollama_models
        except httpx.ConnectError:
            return models

    @classmethod
    def get_supported_models(self) -> list[str]:
        """
        Return the list of supported models that can be instantiated.
        """
        if len(LLM._supported_models) == 0:
            logger.info('Getting list of supported models')
            LLM._supported_models = LLM._calculate_list_of_supported_models()
            logger.info(f'{len(LLM._supported_models)} models available')
        return LLM._supported_models

    @abc.abstractmethod
    def generate(self,
                 system_prompt: str,
                 prompt: str,
                 temperature: float,
                 max_tokens: int,
                 n: int) -> LLMResponse:
        """
        Generate completions using the LLM for a single message.
        Implementation is responsibility of subclasses.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def generate_completions_for_messages(
            self,
            messages: list,
            temperature: float,
            max_tokens: int,
            top_p: int = 1,
            frequency_penalty: float = 0.5,
            presence_penalty: float = 0.5,
            n: int = 1) -> LLMResponse:
        """
        Generate completions using the LLM for a list of messages
        in OpenAI-API style (dictionaries with keys role and content).

        n determines the number of different responses/ trials to generate.

        Other parameters will be directly passed to the client.

        Implementation is responsibility of subclasses.
        """
        raise NotImplementedError

    def _trace_llm_call(self, prompt, response):
        status.trace_llm(
            str(self),
            prompt,
            response
        )
        # Return response as convenience so that this method can be used
        # transparently for the return value.
        return response


class AICoreOpenAILLM(LLM):
    """
    This class implements an interface to query LLMs using the Generative AI
    hub (AI Core) OpenAI proxy client.
    """

    def __init__(self,
                 model_name: str,
                 uses_system_prompt=True):
        self.model_name = model_name
        self.client = ProxyOpenAI()
        self.uses_system_prompt = uses_system_prompt

    def __str__(self) -> str:
        return f'{self.model_name}/OpenAI LLM via AI Core proxy'

    def generate(self,
                 system_prompt: str,
                 prompt: str,
                 temperature=0,
                 max_tokens=512,
                 n=1):
        if not system_prompt:
            messages = [
                {'role': 'user', 'content': prompt}
            ]
        else:
            if self.uses_system_prompt:
                messages = [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt},
                ]
            else:
                # This path is specifically for the Mistral model, which
                # uses openai API for the most part, but does not
                # understand system prompts
                if not system_prompt:
                    system_prompt = ''
                messages = [
                    {'role': 'user',
                        'content': f'{system_prompt}{prompt}'},
                ]
        return self.generate_completions_for_messages(
            messages, temperature, max_tokens, n=n
        )

    def generate_completions_for_messages(self,
                                          messages: list,
                                          temperature: float,
                                          max_tokens: int,
                                          top_p: int = 1,
                                          frequency_penalty: float = 0.5,
                                          presence_penalty: float = 0.5,
                                          n: int = 1):
        try:
            if not self.uses_system_prompt:
                if messages[0]['role'] == 'system':
                    system_message = messages.pop(0)
                    messages[0]['content'] = \
                        f'{system_message["content"]}{messages[0]["content"]}'
            response = self.client.chat.completions.create(
                model_name=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                n=n,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty)
            responses = [response.choices[i].message.content for i in range(n)]
        except InternalServerError as e:
            logger.error(f'A HTTP server-side error occurred while calling '
                         f'{self.model_name} model: {e}')
            if 'gpt' in self.model_name:
                logger.error("The completion triggered OpenAI's firewall")
                return self._trace_llm_call(messages, Filtered(e))
            else:
                return self._trace_llm_call(messages, Error(e))
        except Exception as e:
            logger.error(f'An error occurred while calling the model: {e}')
            return self._trace_llm_call(messages, Error(e))
        return self._trace_llm_call(messages, Success(responses))


class LocalOpenAILLM(AICoreOpenAILLM):
    """
    This class can be used for any OpenAI API-compatible model hosted
    locally (or on an inference server that is not from openai nor from SAP
    AI Core).
    Specifically, this class is used for a local Mistral instance.
    """

    def __init__(self,
                 model_name: str,
                 api_key: str = None,
                 base_url: str = None,
                 supports_openai_style_system_messages=True):
        self.client = OfficialOpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.uses_system_prompt = \
            supports_openai_style_system_messages

    def generate_completions_for_messages(self,
                                          messages: list,
                                          temperature: float,
                                          max_tokens: int,
                                          top_p: int = 1,
                                          frequency_penalty: float = 0.5,
                                          presence_penalty: float = 0.5,
                                          n: int = 1):
        if not self.uses_system_prompt:
            if messages[0]['role'] == 'system':
                logger.debug(
                    f'{str(self)} was called with '
                    'wrong system message style.')
                system_message = messages.pop(0)
                messages[0]['content'] = \
                    f'{system_message["content"]}{messages[0]["content"]}'
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                n=n,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty)
            responses = [
                response.choices[i].message.content for i in range(n)]
            return self._trace_llm_call(messages, Success(responses))
        except Exception as e:
            return self._trace_llm_call(messages, Error(str(e)))


class OllamaLLM(LLM):
    def __init__(self, model_name: str):
        self.model_name = model_name

    def __str__(self) -> str:
        return f'{self.model_name}/Ollama LLM'

    def generate(self,
                 system_prompt: str,
                 prompt: str,
                 temperature: float,
                 max_tokens: int,
                 n: int) -> list[str]:
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt},
            ]
            generations = [
                ollama.generate(self.model_name,
                                prompt, system_prompt,
                                options={'temperature': temperature})
                ['response']
                for _ in range(n)]
            return self._trace_llm_call(messages, Success(generations))
        except Exception as e:
            return self._trace_llm_call(messages, Error(e))

    def generate_completions_for_messages(
            self,
            messages: list,
            temperature: float,
            max_tokens: int,
            top_p: int = 1,
            frequency_penalty: float = 0.5,
            presence_penalty: float = 0.5,
            n: int = 1) -> list[str]:
        try:
            generations = [
                ollama.chat(self.model_name,
                            messages,
                            options={'temperature': temperature,
                                     'top_p': top_p,
                                     'frequency_penalty': frequency_penalty,
                                     'presence_penalty': presence_penalty})
                ['message']['content']
                for _ in range(n)
            ]
            return self._trace_llm_call(messages, Success(generations))
        except Exception as e:
            return self._trace_llm_call(messages, Error(e))


class AICoreGoogleVertexLLM(LLM):

    def __init__(self, model_name: str):
        self.model_name = model_name
        proxy_client = get_proxy_client('gen-ai-hub')
        self.model = GenerativeModel(
            proxy_client=proxy_client,
            model_name=self.model_name
        )

    def __str__(self) -> str:
        return f'{self.model_name}/Google Vertex AI'

    def generate(self,
                 system_prompt: str,
                 prompt: str,
                 temperature: float = 1,
                 max_tokens: int = 1024,
                 n: int = 1) -> LLMResponse:
        contents = []
        if system_prompt:
            # System prompts are only supported at creation of the model.
            # Since we do not want to instantiate the model every time we
            # generate a response, we use a normal user prompt here.
            contents.append(
                {
                    'role': 'user',
                    'parts': [{
                        'text': system_prompt
                    }]
                }
            )
        contents.append(
            {
                'role': 'user',
                'parts': [{
                        'text': prompt
                }]
            }
        )
        try:
            responses = [self.model.generate_content(
                contents,
                generation_config={
                    'temperature': temperature,
                    'max_output_tokens': max_tokens
                }
            ).text for _ in range(n)]
            if not all(responses):
                return Filtered(
                    'One of the generations resulted in an empty response')
            return Success(responses)
        except ValueError as v:
            return Error(str(v))

    def generate_completions_for_messages(
            self,
            messages: list,
            temperature: float = 1,
            max_tokens: int = 1024,
            top_p: int = 1,
            frequency_penalty: float = 0.5,
            presence_penalty: float = 0.5,
            n: int = 1) -> LLMResponse:
        contents = []
        for message in messages:
            contents.append(
                {
                    'role': 'user',
                    'parts': [{'text': message['content']}]
                }
            )
        try:
            responses = [self.model.generate_content(
                contents,
                generation_config={
                    'temperature': temperature,
                    'max_output_tokens': max_tokens,
                    'top_p': top_p
                    # Frequency penalty and Presence penalty are not supported
                    # by the client.
                    # Even though it is supported in https://cloud.google.com/vertex-ai/docs/reference/rest/v1/GenerationConfig   # noqa: E501
                    # 'frequency_penalty': frequency_penalty,
                    # 'presence_penalty': presence_penalty,
                }).text for _ in range(n)]
            if not all(responses):
                return Filtered(
                    'One of the generations resulted in an empty response')
            return Success(responses)
        except ValueError as v:
            return Error(str(v))
