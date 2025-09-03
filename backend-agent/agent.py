import os

from dotenv import load_dotenv
from gen_ai_hub.proxy.core.proxy_clients import set_proxy_version
from gen_ai_hub.proxy.langchain.init_models import (
    init_llm, init_embedding_model)
from langchain.agents.agent_toolkits import \
    create_conversational_retrieval_agent
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.vectorstores import FAISS
from langchain_core.messages import SystemMessage
from langchain_core.tools.retriever import create_retriever_tool
from langchain_text_splitters import RecursiveCharacterTextSplitter


# load env variables
load_dotenv()
AGENT_MODEL = os.environ.get('AGENT_MODEL', 'gpt-4o')
EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'text-embedding-ada-002')
# Use models deployed in SAP AI Core
set_proxy_version('gen-ai-hub')

###############################################################################
# This file creates the agent and adds tools to it.                           #
###############################################################################


# Embedding function
print('Load embedding function')
###############################################################################
# Embeddings create a vector representation of a piece of text.               #
# We customize the embedding function to load all files in a cache, so to     #
# improve performance.                                                        #
# https://python.langchain.com/docs/modules/data_connection/text_embedding/\  #
#                                                      caching_embeddings     #
###############################################################################
# SAP-compliant embedding models
# https://github.tools.sap/AI-Playground-Projects/llm-commons#embedding-models
underlying_embeddings = init_embedding_model(EMBEDDING_MODEL)
# Initialize local cache for faster loading of subsequent executions
fs = LocalFileStore('./cache')
# Link the embedding and the local cache system, and define a namespace
# to differentiate the caches (here not needed, but best practice)
cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    underlying_embeddings, fs, namespace=underlying_embeddings.model)


def get_retriever(document_path: str,
                  name: str,
                  description: str,
                  document_glob='**/*'):
    # Document loader
    # https://python.langchain.com/docs/modules/data_connection/document_loaders/
    # https://python.langchain.com/docs/integrations/document_loaders/
    ###########################################################################
    # Load the files contained in a folder.                                   #
    # The DirectoryLoader function takes as parameters the path of the folder #
    # to load, and the extensions of the files to load.                       #
    # We use a wildcard to take all the files in the folder.                  #
    #                                                                         #
    # Directory loader:                                                       #
    # https://python.langchain.com/docs/modules/data_connection/document_loaders/\#
    #                                                          file_directory #
    # Directory loader loads all files in a folder, given their extension.    #
    # It relies on a underlying UnstructuredLoader class of loaders.          #
    ###########################################################################
    loader = DirectoryLoader(document_path, document_glob)
    raw_docs = loader.load()

    # Splitting such short documents may not be strongly needed, but it is a
    # best practice
    # Recursively split by character (default: returns and spaces)
    # This text splitter class is the recommended one for generic text
    # https://python.langchain.com/docs/modules/data_connection/document_transformers/

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100)
    docs = text_splitter.split_documents(raw_docs)

    # Vector store
    # https://python.langchain.com/docs/modules/data_connection/vectorstores
    ###########################################################################
    # Vector stores are used to store embeddings vectors and load the         #
    # information into a format that the model will be able to understand.    #
    # There are several vector stores that can be adopted:                    #
    # https://python.langchain.com/docs/integrations/vectorstores             #
    # Our requirements are simple: being free, open source, and run locally in#
    # multiple platform environments.                                         #
    # So, we chose FAISS (knowing also ChromaDB could have been a good choice)#
    # In general, and for future development of this project, we may want to  #
    # keep an eye on a popularity ranking of vector dbms                      #
    # https://db-engines.com/en/ranking/vector+dbms                           #
    # Another possible choice is Hana Vector DB                               #
    ###########################################################################
    # We could also save and load a FAISS index. This is useful so we don’t
    # have to recreate it everytime we run the agent.
    # In this case the process is simple, but as the agent grows it could
    # become a need-to-do.
    database = FAISS.from_documents(docs, cached_embedder)

    # Retriever
    # https://python.langchain.com/docs/modules/data_connection/retrievers/
    ###########################################################################
    # A retriever is the component in charge of retrieving the relevant       #
    # information to answer to an unstructured query.                         #
    # Depending on the use case (i.e., how information have been stored),     #
    # several retrieval components can be used:                               #
    # https://python.langchain.com/docs/integrations/retrievers               #
    # In our case, the simplest method is sufficient. It involves creating    #
    # embeddings for each piece of text, that we did at the previous step when#
    # storing document embeddings in the vector store.                        #
    ###########################################################################
    retriever = database.as_retriever()

    return create_retriever_tool(retriever, name, description)


# LLM
# https://python.langchain.com/docs/modules/model_io/llms/

print('Load LLM')

###############################################################################
# The LLM is the core component of a langchain. The langchain does not serve  #
# its own LLM, but rather provides a standard interface for interacting with  #
# many different LLMs. Indeed, a lot of LLMs are natively supported:          #
# https://python.langchain.com/docs/integrations/llms/                        #
#                                                                             #
# At SAP we are not allowed to query LLMs as they are. Indeed, we need to use #
# a proxy application (SAP AI Core). Several LLMs are already available via   #
# this application. They are defined foundational models. Besides, it is      #
# possible to deploy and host additional LLMs and models by deploying custom  #
# inference servers via AI Core.                                              #
# Current available foundational models in SAP AI Core                        #
# https://help.sap.com/docs/sap-ai-core/sap-ai-core-service-guide/            #
#   models-and-scenarios-in-generative-ai-hub                                 #
###############################################################################

# Initialize the LLM model to use, among the ones provided by SAP
# The max token count needs to be increased so that responses are not cut off.
llm = init_llm(model_name=AGENT_MODEL, max_tokens=4096)

# Chain
# https://python.langchain.com/docs/modules/chains
# Not needed here, as we are building an agent (see more below)


# ################################# Agent #####################################

###############################################################################
#                                                                             #
# The core idea of agents is to use a language model to choose a sequence of  #
# actions to take. In chains, a sequence of actions is hardcoded (in code).   #
# In agents, a language model is used as a reasoning engine to determine      #
# which actions to take and in which order.                                   #
# https://python.langchain.com/docs/modules/agents/how_to/custom_agent        #
#                                                                             #
###############################################################################

system_message = SystemMessage(
    content=(
        'You are a powerful assistant whose main goal is to help the user'
        'perform vulnerability scans and security scans against machine '
        'learning models, primarily against Large Language Models (LLMs). '
        'Do your best to answer the questions but do not make up '
        'information you do not know. Use any tools available to look up '
        'relevant information, if necessary. Always look up how attacks work '
        'before using them. If a user asks "Start the vulnerability scan", '
        'run attack_suite_how to find out how you can run a scan against an '
        'LLM'))


# Define tools
# https://python.langchain.com/docs/modules/agents/tools/
print('Define tools')

###############################################################################
# Define tools to be used by the agent.                                       #
# A wide list of built in tools already exists:                               #
# https://python.langchain.com/docs/integrations/tools                        #
# Otherwise, we can create custom tools. There are multiple way to define a   #
# tool. Here we use retrievers and we write custom tools from scratch.        #
#                                                                             #
# Retrievers previously can be transformed into tools.                        #
# https://python.langchain.com/docs/use_cases/question_answering/\            #
# conversational_retrieval_agents#retriever-tool                              #
# This allows the agent to access them and load their information.            #
###############################################################################

# Custom tools
from tools import run_prompt_attack, \
    run_gptfuzz, \
    run_pyrit, \
    run_pyrit_red_teaming, \
    run_pyrit_crescendo, \
    run_pyrit_pair, \
    run_codeattack, \
    run_artprompt, \
    run_garak_attack, \
    run_attack_suite, \
    get_supported_models, \
    use_command, \
    test_textattack, \
    run_own_model_attack as textattack_run_own_model, \
    run_hf_model_nlp as textattack_run_hf  # noqa: E402

# Retriever tools
print('Load pentesting notes and create retrievers')

# Retriever that contains the roadmap of pentesting on internal models
# using textattack
textattack_notes_own_model = get_retriever(
    document_path='./data/textattack/launch_own_model',
    name='textattack_own_model_how',  # Name of tool (unique and descriptive)
    description='Steps to take to run a textattack pentest on a local \
    pre-registered ML model; dont ask any information before launching \
    this tool. Use this before using the run_own_model_attack tool'
)
# Retriever that contains the roadmap for pentesting Huggingface models
# using textattack
textattack_notes_huggingface_model = get_retriever(
    './data/textattack/launch_hf_model',
    'textattack_hf_model_how',
    'Steps to take to run a textattack pentest on an ML model on huggingface; \
    dont ask any information before launching this tool. \
    Use this before using the run_hf_model_nlp tool'
)
# Retriever that contains the roadmap of LLM prompt attacks
prompt_attack_notes = get_retriever(
    './data/prompt_map',
    'prompt_attack_how',
    'Steps to take to run a pentest on a LLM using the \
    "prompt map" framework. Use this before using the \
    run_prompt_attack tool'
)
# Retriever that contains notes on how the agent should use GPTFuzz
gprfuzz_notes = get_retriever(
    './data/gptfuzz',
    'gptfuzz_pentest_notes',
    'Steps to take to run a pentest on a LLM using the \
    "gptfuzz" framework. ALWAYS use this before using the \
    run_gptfuzz tool'
)
# Retriever that contains notes on how the agent should use PyRIT
pyrit_notes = get_retriever(
    './data/pyrit',
    'pyrit_how',
    'Steps to take to run a pentest on a LLM using the \
    "PyRIT" framework. ALWAYS run this before using the \
    run_pyrit tool, because it will explain how to use the tool'
)
# Retriever that contains notes on how to use CodeAttack
codeattack_notes = get_retriever(
    './data/codeattack',
    'codeattack_how',
    'Steps to take to run a pentest on a LLM using the \
    "codeattack" framework. Use this before using the \
    run_codeattack tool'
)
# Retriever that contains notes on how to use ArtPrompt
artprompt_notes = get_retriever(
    './data/artprompt',
    'artprompt_how',
    'Steps to take to run a pentest on a LLM using the \
    "artprompt" framework. Use this before using the \
    run_artprompt tool'
)
# Retriever that contains notes on how to use Garak
garak_notes = get_retriever(
    './data/garak',
    'garak_how',
    'Steps to take to run a pentest on a LLM using the \
    "garak" framework. ALWAYS run this before using the \
    run_garak_attack tool, because it will explain how to use the tool'
)
# Retriever that contains notes on how to run attack suites
llm_attack_suite_notes = get_retriever(
    './data/suite',
    'attack_suite_how',
    ('Explains how to run test suites. These are useful for'
     'launching multiple attacks on LLMs. Running a test suite is a good'
     'first step for users to take to get a general understanding of the'
     'vulnerabilities of a model.'),
    document_glob='**/*.txt'
)

# Create the agent
# https://python.langchain.com/docs/modules/agents/tools/toolkits
###############################################################################
# Build a conversational agent                                                #
# https://python.langchain.com/docs/use_cases/question_answering/\            #
# conversational_retrieval_agents                                             #
###############################################################################
print('Create agent')

# Create an array of tools the agent can interact with.
tools = [
    use_command,
    test_textattack,
    textattack_notes_own_model,
    textattack_run_own_model,
    textattack_notes_huggingface_model,
    textattack_run_hf,
    prompt_attack_notes,
    run_prompt_attack,
    gprfuzz_notes,
    run_gptfuzz,
    pyrit_notes,
    run_pyrit,
    run_pyrit_red_teaming,
    run_pyrit_crescendo,
    run_pyrit_pair,
    codeattack_notes,
    run_codeattack,
    artprompt_notes,
    run_artprompt,
    garak_notes,
    run_garak_attack,
    llm_attack_suite_notes,
    run_attack_suite,
    get_supported_models
]

# Instantiate agent using `create_conversational_retrieval_agent`.
# Using this convenience function, memory is automatically created.
agent = create_conversational_retrieval_agent(llm,
                                              tools,
                                              memory_key='chat_history',
                                              system_message=system_message,
                                              verbose=True)
print('Agent is ready')
