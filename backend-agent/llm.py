from typing import Any, Dict, List
import abc
import logging
import os

from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
from gen_ai_hub.proxy.core.proxy_clients import set_proxy_version
from gen_ai_hub.proxy.native.openai import OpenAI as ProxyOpenAI
from gen_ai_hub.proxy.native.google_vertexai.clients import GenerativeModel
from gen_ai_hub.proxy.native.amazon.clients import Session
from openai import OpenAI as OfficialOpenAI
from openai import InternalServerError
import httpx
import ollama

from llm_response import Error, Filtered, LLMResponse, Success
from status import status

set_proxy_version('gen-ai-hub')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(status.trace_logging)

AICORE_MODELS = {
    'aicore-ibm':
    [
        'ibm--granite-13b-chat'
    ],
    'aicore-mistralai':
    [
        'mistralai--mistral-large-instruct',
        'mistralai--mistral-small-instruct',
    ],
    'aicore-opensource':
    [
        'meta--llama3.1-70b-instruct',
    ],
    'aws-bedrock':
    [
        'amazon--nova-lite',
        'amazon--nova-micro',
        'amazon--nova-pro',
        'amazon--nova-premier',
        'amazon--titan-text-lite',  # deprecated
        'amazon--titan-text-express',  # deprecated
        'anthropic--claude-3-haiku',
        'anthropic--claude-3-sonnet',
        'anthropic--claude-3-opus',
        'anthropic--claude-3.5-sonnet',
        'anthropic--claude-3.7-sonnet',
        'anthropic--claude-4-sonnet',
        'anthropic--claude-4-opus',
    ],
    'azure-openai':
    [
        'gpt-4',  # deprecated
        'gpt-4o',
        'gpt-4o-mini',
        'gpt-4.1',
        'gpt-4.1-mini',
        'gpt-4.1-nano',
        'gpt-5',
        'gpt-5-mini',
        'gpt-5-nano',
        'o1',
        'o3',
        'o3-mini',
        'o4-mini',
    ],
    'gcp-vertexai':
    [
        'gemini-1.5-pro',  # deprecated
        'gemini-1.5-flash'  # deprecated,
        'gemini-2.0-flash',
        'gemini-2.0-flash-lite',
        'gemini-2.5-flash',
        'gemini-2.5-pro',
    ],
}


class LLM(abc.ABC):
    """
    This is the abstract class used to create and access LLMs for pentesting.
    """

    _supported_models: list[str] = []

    @classmethod
    def from_model_name(cls, model_name: str) -> 'LLM':
        """
        Create a specific LLM object from the name of the model.
        Useful because the user can specify only the name in the agent.
        """
        # Foundation-models scenarios in AI Core
        if model_name in AICORE_MODELS['azure-openai']:
            return AICoreOpenAILLM(model_name)
        if model_name in AICORE_MODELS['aicore-ibm']:
            # IBM models are compatible with OpenAI completion API
            return AICoreOpenAILLM(model_name)
        if model_name in AICORE_MODELS['aicore-opensource']:
            return AICoreOpenAILLM(model_name, False)
        if model_name in AICORE_MODELS['aicore-mistralai']:
            return AICoreOpenAILLM(model_name, False)
        if model_name in AICORE_MODELS['aws-bedrock']:
            if 'titan' in model_name:
                # Titan models don't support system prompts
                return AICoreAmazonBedrockLLM(model_name, False)
            else:
                return AICoreAmazonBedrockLLM(model_name)
        if model_name in AICORE_MODELS['gcp-vertexai']:
            return AICoreGoogleVertexLLM(model_name)

        # Custom models
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
        ollama_host = os.getenv('OLLAMA_HOST')
        ollama_port = os.getenv('OLLAMA_PORT', 11434)
        try:
            if ollama_host:
                # The model is served in a remote ollama instance
                remote_ollama_host = f'{ollama_host}:{ollama_port}'
                return OllamaLLM(model_name, remote_ollama_host)
            else:
                # The model is served in a local ollama instance
                ollama.show(model_name)
                return OllamaLLM(model_name)
        except (ConnectionError, ollama.ResponseError, httpx.ConnectError):
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
            ollama_models = []
            ollama_host = os.getenv('OLLAMA_HOST')
            ollama_port = os.getenv('OLLAMA_PORT', 11434)
            if ollama_host:
                # The model is served in a remote ollama instance
                remote_ollama_host = f'{ollama_host}:{ollama_port}'
                ollama_models = [m['model'] for m in
                                 ollama.Client(remote_ollama_host).list()
                                 ['models']]
            else:
                ollama_models = [m['name'] for m in ollama.list()['models']]
            return models + ollama_models
        except (ConnectionError, ollama.ResponseError, httpx.ConnectError):
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
                 **kwargs: dict) -> LLMResponse:
        """
        Generate completions using the LLM for a single message.
        Implementation is responsibility of subclasses.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def generate_completions_for_messages(self,
                                          messages: list,
                                          **kwargs: dict) -> LLMResponse:
        """
        Generate completions using the LLM for a list of messages
        in OpenAI-API style (dictionaries with keys role and content).

        Other parameters will be directly passed to the client and are
        consistent to OpenAI's style.

        Implementation is responsibility of subclasses, as well as the handling
        of possible parameters not supported in non-OpenAI models.
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
    """This class implements an interface to query LLMs using the Generative AI
    Hub (AI Core) OpenAI proxy client.

    All models in AI Core that are compatible with the OpenAI API can be
    queries using this class.
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
                 **kwargs) -> LLMResponse:
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
                        'content': f'{system_prompt}\n{prompt}'},
                ]
        return self.generate_completions_for_messages(
            messages, **kwargs
        )

    def generate_completions_for_messages(self,
                                          messages: list,
                                          **kwargs) -> LLMResponse:
        try:
            if not self.uses_system_prompt:
                if messages[0]['role'] == 'system':
                    system_message = messages.pop(0)
                    messages[0]['content'] = (
                        f'{system_message["content"]}\n'
                        f'{messages[0]["content"]}')
            response = self.client.chat.completions.create(
                model_name=self.model_name,
                messages=messages,
                **kwargs)
            responses = [response.choices[i].message.content for i in
                         range(kwargs.get('n', 1))]
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
                 api_key: str = '',
                 base_url: str = '',
                 supports_openai_style_system_messages=True):
        self.client = OfficialOpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.uses_system_prompt = \
            supports_openai_style_system_messages

    def generate_completions_for_messages(self,
                                          messages: list,
                                          **kwargs) -> LLMResponse:
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
                **kwargs)
            responses = [
                response.choices[i].message.content for i in
                range(kwargs.get('n', 1))]
            return self._trace_llm_call(messages, Success(responses))
        except Exception as e:
            return self._trace_llm_call(messages, Error(str(e)))


class OllamaLLM(LLM):
    def __init__(self, model_name: str, host=None):
        self.model_name = model_name
        self.client = ollama.Client(host=host)

    def __str__(self) -> str:
        return f'{self.model_name}/Ollama LLM'

    def generate(self,
                 system_prompt: str,
                 prompt: str,
                 **kwargs) -> list[str]:  # TODO:check
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt},
            ]
            generations = [
                self.client.generate(model=self.model_name,
                                     prompt=prompt,
                                     system=system_prompt,
                                     options={'temperature':
                                              kwargs.get('temperature')}
                                     )['response']
                for _ in range(kwargs.get('n', 1))]
            return self._trace_llm_call(messages, Success(generations))
        except Exception as e:
            return self._trace_llm_call(messages, Error(e))

    def generate_completions_for_messages(
            self,
            messages: list,
            **kwargs) -> list[str]:  # TODO:check
        try:
            generations = [
                self.client.chat(
                    self.model_name,
                    messages,
                    options=kwargs
                )['message']['content']
                for _ in range(kwargs.get('n', 1))
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

    def _send_request(self, messages: list, **kwargs) -> LLMResponse:
        # Convert the max_tokens or max_completion_tokens parameter
        if 'max_tokens' in kwargs:
            kwargs['max_output_tokens'] = kwargs.pop('max_tokens')
        if 'max_completion_tokens' in kwargs:
            kwargs['max_output_tokens'] = kwargs.pop('max_completion_tokens')
        # Frequency penalty and Presence penalty are not supported
        # by the client.
        # Even though they are supported in https://cloud.google.com/vertex-ai/docs/reference/rest/v1/GenerationConfig   # noqa: E501
        kwargs.pop('frequency_penalty', None)
        kwargs.pop('presence_penalty', None)

        n = kwargs.pop('n', 1)
        # Send request
        try:
            responses = [self.model.generate_content(
                messages,
                generation_config=kwargs
            ).text for _ in range(n)]
            if not all(responses):
                return Filtered(
                    'One of the generations resulted in an empty response')
            return Success(responses)
        except ValueError as v:
            return Error(str(v))

    def generate(self,
                 system_prompt: str,
                 prompt: str,
                 **kwargs) -> LLMResponse:
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
        return self._send_request(contents, **kwargs)

    def generate_completions_for_messages(
            self,
            messages: list,
            **kwargs: dict) -> LLMResponse:
        contents = []
        for message in messages:
            contents.append(
                {
                    'role': 'user',
                    'parts': [{'text': message['content']}]
                }
            )
        return self._send_request(contents, **kwargs)


class AICoreAmazonBedrockLLM(LLM):

    def __init__(self, model_name: str, uses_system_prompt: bool = True):
        self.model_name = model_name
        proxy_client = get_proxy_client('gen-ai-hub')
        self.model = Session().client(
            proxy_client=proxy_client,
            model_name=self.model_name
        )
        self.uses_system_prompt = uses_system_prompt

    def __str__(self) -> str:
        return f'{self.model_name}/Amazon Bedrock'

    def _send_request(self, messages: list, **kwargs) -> LLMResponse:
        # Build inference configuration from kwargs
        # Supported parameters are: maxTokens, temperature, topP, stopSequences
        temperature = kwargs.get('temperature')
        max_tokens = kwargs.get('max_tokens') or \
            kwargs.get('max_completion_tokens')
        top_p = kwargs.get('top_p')
        inference_configs = {}
        if temperature:
            inference_configs['temperature'] = temperature
        if max_tokens:
            inference_configs['maxTokens'] = max_tokens
        if top_p:
            inference_configs['topP'] = top_p
        # TODO: We ignore stopSequences for now

        # Manage possible system prompt
        system_configs = []
        if kwargs.get('system_prompt'):
            system_configs = [{'text': kwargs.get('system_prompt')}]

        # Send request
        try:
            responses = [self.model.converse(
                messages=messages,
                inferenceConfig=inference_configs,
                system=system_configs
            )['output']['message']['content'][0]['text'] for _ in
                range(kwargs.get('n', 1))]
            if not all(responses):
                return Filtered(
                    'One of the generations resulted in an empty response')
            return Success(responses)
        except ValueError as v:
            return Error(str(v))

    def generate(self,
                 system_prompt: str,
                 prompt: str,
                 **kwargs: dict) -> LLMResponse:

        # Declare types for messages and kwargs to avoid mypy errors
        messages: List[Dict[str, Any]] = []

        # Build messages
        if not system_prompt:
            messages.append(
                {'role': 'user', 'content': [{'text': prompt}]}
            )
        else:
            # System prompt handling (the role "system" is not supported in
            # bedrock messages)
            if self.uses_system_prompt:
                # Pass the system prompt in kwargs and delegate its
                # handling to _send_request
                kwargs['system_prompt'] = system_prompt
                messages.append(
                    {'role': 'user', 'content': [{'text': prompt}]}
                )
            else:
                # Similarly to some Mistral models, also among Bedrock models
                # there are some that do not support system prompt (e.g., titan
                # models).
                messages.append(
                    {'role': 'user',
                     'content': [{'text': f'{system_prompt}\n{prompt}'}]},
                )
        return self._send_request(messages, **kwargs)

    def generate_completions_for_messages(
            self,
            messages: list,
            **kwargs: dict) -> LLMResponse:
        contents = []
        # Translate openai-style messages to bedrock-style messages
        for message in messages:
            if message.get('role') == 'system' and \
                    self.uses_system_prompt:
                # This message will be passed in kwargs and handled in
                # _send_request as system prompt
                kwargs['system_prompt'] = message['content']
                continue
            contents.append(
                {
                    'role': 'user',
                    'content': [{'text': message['content']}]
                }
            )
        return self._send_request(contents, **kwargs)
