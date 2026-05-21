from typing import Any, Dict, List, Optional
import logging

from gen_ai_hub.orchestration_v2.service import OrchestrationService
from gen_ai_hub.orchestration_v2.models.config import OrchestrationConfig, ModuleConfig
from gen_ai_hub.orchestration_v2.models.llm_model_details import LLMModelDetails
from gen_ai_hub.orchestration_v2.models.template import Template, PromptTemplatingModuleConfig
from gen_ai_hub.orchestration_v2.models.message import (
    AssistantMessage,
    ChatMessage,
    SystemMessage,
    UserMessage,
)
from gen_ai_hub.orchestration_v2.models.azure_content_filter import AzureContentFilter, AzureThreshold
from gen_ai_hub.orchestration_v2.models.content_filter import ContentFilter, ContentFilterProvider
from gen_ai_hub.orchestration_v2.models.content_filtering import (
    FilteringModuleConfig,
    InputFiltering,
    OutputFiltering,
)
from gen_ai_hub.orchestration_v2.models.document_grounding import (
    GroundingModuleConfig,
    DocumentGroundingConfig,
    DocumentGroundingFilter,
    DocumentGroundingPlaceholders,
)

from llm_response import Error, Filtered, LLMResponse, Success
from status import status

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(status.trace_logging)

# Models supported by AI Core Orchestration Service.
# These are the same model deployment names as used in the LLM module,
# but accessed through the Orchestration Service pipeline instead of
# directly through the model endpoints.
ORCHESTRATION_MODELS = [
    # Azure OpenAI
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
    # MistralAI
    'mistralai--mistral-large-instruct',
    'mistralai--mistral-medium-instruct',
    'mistralai--mistral-small-instruct',
    # Amazon Bedrock (via Orchestration)
    'amazon--nova-lite',
    'amazon--nova-micro',
    'amazon--nova-pro',
    'anthropic--claude-3-haiku',
    'anthropic--claude-3-opus',
    'anthropic--claude-3.5-sonnet',
    'anthropic--claude-3.7-sonnet',
    # Google Vertex AI (via Orchestration)
    'gemini-2.5-flash',
    'gemini-2.5-pro',
]


class Orchestration:
    """
    Interface to SAP AI Core Orchestration Service.

    Unlike the direct model access in llm.py, this class routes requests
    through the AI Core Orchestration pipeline, which supports:
      - Declarative prompt templating with named variables
      - Input / output content filtering (Azure Content Safety)
      - Grounding (Retrieval-Augmented Generation) via a document store
      - A unified interface regardless of the underlying model provider

    The same LLMResponse types (Success, Error, Filtered) are returned
    as in llm.py so callers can treat both interchangeably.

    Example — simple usage::

        orc = Orchestration.from_model_name('gpt-4o')
        result = orc.generate('You are a security expert.', 'Explain XSS.')
        print(result.unwrap_first())

    Example — with content filtering::

        from gen_ai_hub.orchestration_v2.models.azure_content_filter import (
            AzureContentFilter, AzureThreshold
        )
        cf = AzureContentFilter(hate=AzureThreshold.ALLOW_SAFE,
                                violence=AzureThreshold.ALLOW_SAFE)
        orc = Orchestration('gpt-4o', input_filter=cf, output_filter=cf)
        result = orc.generate('...', '...')

    Example — with grounding (RAG)::

        from gen_ai_hub.orchestration_v2.models.document_grounding import (
            GroundingModuleConfig, DocumentGroundingConfig,
            DocumentGroundingFilter, DocumentGroundingPlaceholders
        )
        grounding = GroundingModuleConfig(
            config=DocumentGroundingConfig(
                filters=[DocumentGroundingFilter(
                    data_repository_type='vector',
                    data_repositories=['my-collection'],
                )],
                placeholders=DocumentGroundingPlaceholders(
                    input=['user_prompt'],
                    output='grounding_context',
                ),
            )
        )
        orc = Orchestration('gpt-4o', grounding=grounding)
        result = orc.generate_with_grounding('What is our refund policy?')
    """

    def __init__(
        self,
        model_name: str,
        input_filter: Optional[AzureContentFilter] = None,
        output_filter: Optional[AzureContentFilter] = None,
        grounding: Optional[GroundingModuleConfig] = None,
        model_params: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialise the Orchestration client.

        Parameters
        ----------
        model_name:
            The model deployment name (e.g. ``'gpt-4o'``).
        input_filter:
            Optional Azure Content Safety filter applied to the *prompt*
            before it reaches the model.
        output_filter:
            Optional Azure Content Safety filter applied to the model
            *response* before it is returned to the caller.
        grounding:
            Optional grounding (RAG) configuration.  When set,
            ``generate_with_grounding()`` will inject retrieved context
            into the prompt automatically.
        model_params:
            Default generation parameters forwarded to the LLM module
            (e.g. ``{'temperature': 0.7, 'max_tokens': 512}``).
            These can be overridden per call via ``**kwargs``.
        """
        self.model_name = model_name
        self.input_filter = input_filter
        self.output_filter = output_filter
        self.grounding = grounding
        self.model_params: Dict[str, Any] = model_params or {}
        self.client = OrchestrationService()

    def __str__(self) -> str:
        return f'{self.model_name}/AI Core Orchestration'

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def get_supported_models(cls) -> List[str]:
        """Return the list of models supported by the Orchestration Service."""
        return list(ORCHESTRATION_MODELS)

    @classmethod
    def from_model_name(cls, model_name: str) -> 'Orchestration':
        """
        Create an :class:`Orchestration` instance from a model name alone.

        Raises :class:`ValueError` if the model is not in the list of
        models supported by the Orchestration Service.
        """
        if model_name not in ORCHESTRATION_MODELS:
            raise ValueError(
                f"Model '{model_name}' is not supported by the AI Core "
                f'Orchestration Service. Supported models: '
                f'{ORCHESTRATION_MODELS}'
            )
        logger.info(f'Creating Orchestration client for model: {model_name}')
        return cls(model_name)

    # ------------------------------------------------------------------
    # Public generation API  (mirrors llm.py interface)
    # ------------------------------------------------------------------

    def generate(
        self,
        system_prompt: str,
        prompt: str,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Single-turn generation via the Orchestration pipeline.

        Builds a two-message template (``system`` + ``user``) with named
        template variables, submits it to the Orchestration Service and
        returns an :class:`LLMResponse`.

        Parameters
        ----------
        system_prompt:
            Instruction / persona for the model.  May be empty.
        prompt:
            The user's message / question.
        **kwargs:
            Extra generation parameters (``temperature``, ``max_tokens``,
            ``n``, …) that override the instance-level ``model_params``.
        """
        messages: List[ChatMessage] = []

        if system_prompt:
            messages.append(SystemMessage(content='{{?system_prompt}}'))
        messages.append(UserMessage(content='{{?user_prompt}}'))

        placeholder_values: Dict[str, str] = {'user_prompt': prompt}
        if system_prompt:
            placeholder_values['system_prompt'] = system_prompt

        return self._run(messages, placeholder_values, **kwargs)

    def generate_completions_for_messages(
        self,
        messages: list,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Multi-turn generation using an OpenAI-style message list.

        Each element of *messages* must be a dict with ``'role'`` and
        ``'content'`` keys (the same format used throughout llm.py).

        Parameters
        ----------
        messages:
            A list of ``{'role': ..., 'content': ...}`` dicts.
        **kwargs:
            Extra generation parameters forwarded to the LLM module.
        """
        orc_messages: List[ChatMessage] = []
        placeholder_values: Dict[str, str] = {}

        for i, msg in enumerate(messages):
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            var_name = f'msg_{i}'
            var_ref = f'{{{{?{var_name}}}}}'

            if role == 'system':
                orc_messages.append(SystemMessage(content=var_ref))
            elif role == 'assistant':
                orc_messages.append(AssistantMessage(content=var_ref))
            else:
                orc_messages.append(UserMessage(content=var_ref))

            placeholder_values[var_name] = content

        return self._run(orc_messages, placeholder_values, **kwargs)

    def generate_with_grounding(
        self,
        prompt: str,
        system_prompt: str = '',
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generation with grounding (RAG) enabled.

        The Orchestration Service will retrieve relevant documents from
        the configured document store and inject them into the prompt
        automatically before calling the model.

        Requires *grounding* to be configured when constructing this
        instance (via ``__init__`` or by setting ``self.grounding``).

        Parameters
        ----------
        prompt:
            The user question / task.
        system_prompt:
            Optional system instruction.
        **kwargs:
            Extra generation parameters.

        Raises
        ------
        ValueError
            If no grounding configuration is set on this instance.
        """
        if self.grounding is None:
            raise ValueError(
                'Grounding is not configured for this Orchestration instance. '
                'Pass a GroundingModuleConfig to the constructor.'
            )

        messages: List[ChatMessage] = []
        placeholder_values: Dict[str, str] = {'user_prompt': prompt}

        if system_prompt:
            messages.append(SystemMessage(content='{{?system_prompt}}'))
            placeholder_values['system_prompt'] = system_prompt

        # The grounding context injected by the Orchestration Service is
        # referenced via the $grounding_context variable in the template.
        messages.append(
            UserMessage(
                content='Context:\n$grounding_context\n\nQuestion: {{?user_prompt}}',
            )
        )

        return self._run(messages, placeholder_values, **kwargs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_llm_details(self, **kwargs: Any) -> LLMModelDetails:
        """
        Merge instance-level ``model_params`` with per-call ``kwargs``
        and return an :class:`LLMModelDetails` for the Orchestration
        pipeline.

        Per-call ``kwargs`` take precedence over instance defaults.
        """
        params = {**self.model_params, **kwargs}
        # 'n' is not a standard Orchestration LLM param; strip it so
        # that it does not cause an API error.
        params.pop('n', None)
        return LLMModelDetails(
            name=self.model_name,
            params=params if params else None,
        )

    def _build_config(
        self,
        messages: List[ChatMessage],
        **kwargs: Any,
    ) -> OrchestrationConfig:
        """
        Assemble a complete :class:`OrchestrationConfig` from the
        supplied parts and the instance-level optional modules
        (filtering, grounding).
        """
        llm = self._build_llm_details(**kwargs)
        template = Template(template=messages)
        pt_config = PromptTemplatingModuleConfig(prompt=template, model=llm)

        input_filtering: Optional[InputFiltering] = None
        output_filtering: Optional[OutputFiltering] = None

        if self.input_filter is not None:
            input_filtering = InputFiltering(
                filters=[ContentFilter(type_=ContentFilterProvider.AZURE, config=self.input_filter)]
            )
        if self.output_filter is not None:
            output_filtering = OutputFiltering(
                filters=[ContentFilter(type_=ContentFilterProvider.AZURE, config=self.output_filter)]
            )

        filtering: Optional[FilteringModuleConfig] = None
        if input_filtering is not None or output_filtering is not None:
            filtering = FilteringModuleConfig(input=input_filtering, output=output_filtering)

        module_config = ModuleConfig(
            prompt_templating=pt_config,
            filtering=filtering,
            grounding=self.grounding,
        )
        return OrchestrationConfig(modules=module_config)

    def _run(
        self,
        messages: List[ChatMessage],
        placeholder_values: Dict[str, str],
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Build the config, call the Orchestration Service and return an
        :class:`LLMResponse`.

        Handles:
        - ``n`` repetitions (calls the service *n* times sequentially).
        - Content-filter rejections (returned as ``Filtered``).
        - All other exceptions (returned as ``Error``).
        """
        n: int = kwargs.pop('n', 1)

        try:
            config = self._build_config(messages, **kwargs)
            responses: List[str] = []

            for _ in range(n):
                result = self.client.run(
                    config=config,
                    placeholder_values=placeholder_values,
                )
                text = result.final_result.choices[0].message.content
                responses.append(text)

            if not all(responses):
                return self._trace_orc_call(
                    messages,
                    Filtered('One or more generations produced an empty response'),
                )

            return self._trace_orc_call(messages, Success(responses))

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f'Orchestration call to {self.model_name} failed: {error_msg}'
            )
            # The Orchestration Service raises an exception whose message
            # contains "filtered" when a content filter blocks the request.
            if 'filtered' in error_msg.lower() or 'content_filter' in error_msg.lower():
                return self._trace_orc_call(messages, Filtered(e))
            return self._trace_orc_call(messages, Error(e))

    def _trace_orc_call(
        self,
        prompt: Any,
        response: LLMResponse,
    ) -> LLMResponse:
        """
        Log the orchestration call (prompt + response) to the status
        tracer and return *response* unchanged.

        This mirrors :meth:`LLM._trace_llm_call` in ``llm.py`` so that
        all AI interactions — whether direct model calls or orchestration
        pipeline calls — appear in the trace log.
        """
        if isinstance(prompt, list):
            serializable_prompt = [
                m.model_dump() if hasattr(m, 'model_dump') else m
                for m in prompt
            ]
        else:
            serializable_prompt = prompt
        status.trace_llm(
            str(self),
            serializable_prompt,
            response,
        )
        return response
