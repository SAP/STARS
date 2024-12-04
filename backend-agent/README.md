# STARS (Threat AI Reporting Scanner) #

This project aims to create an "agent" capable of performing pentests.
To achieve this, we are using several features of Langchain.
Among them, we are using the "Question over a Document," "Conversational_agent," and some "custom tools".

For a list of supported custom tools (i.e., the attacks), refer to the project's README.

## Components
- The *Question over a Document* module is primarily used to inject methodologies into the agent for performing actions (i.e., specific tasks)
- The *Conversational Agent* allows us to create an agent that can communicate with users and perform the tasks they request
- The *custom tools* are a mandatory part of this project, as they enable the agent to perform certain tasks (such as executing commands or communicating with a CLI) that do not originate by pre-defined libraries or already existing modules

## SAP AI Core Requirements

Before running the tool, make sure to have an account configured and fully
working on SAP AI Core (requires a SAP BTP subaccount with a running AI Core service instance).

Please note that the agent requires `gpt-4` LLM and `text-embedding-ada-002`
embedding function. For the default attack suite, additional the model
`mistralai--mixtral-8x7b-instruct-v01` is used.
They must be already **deployed and running in SAP AI Core** before running this
tool.
Refer [to the official documentation](https://help.sap.com/docs/sap-ai-core/sap-ai-core-service-guide/models-and-scenarios-in-generative-ai-hub) for what other models it is possible to deploy.

### Support for non-SAP AI Core models
In general, the pentest tools integrated in the agent can be run on LLMs deployed in SAP AI Core, but also custom inference servers (e.g., vllm or a local ollama) are supported.


## Installation
- Use Python 3.10 or 3.11
- Install dependencies with `pip install -r requirements.txt`
- MacOS only: install libmagic `brew install libmagic`

> Tested on a M3 MacOS and on Ubuntu 22.04


## Run

The agent is run in a backend (Flask webserver).

`python main.py`

Refer to `frontend` folder for the frontend.

For some features, additional configuration options are required.
For that, create a `.env` file. You can find an example in `.env.example`.

### Tracing with Langfuse

[Langfuse](https://github.com/langfuse/langfuse) is a tool that can be used for understanding what the agent does, helping in debugging it. To use it, [set up a Langfuse server](https://github.com/langfuse/langfuse?tab=readme-ov-file#get-started). Open the web interface and create a project. Set up a new API key and copy secret and public key into your .env file (LANGFUSE_SK and LANGFUSE_PK), set the LANGFUSE_HOST variable and enable Langfuse by setting the ENABLE_LANGFUSE variable.

Install the langfuse handler with `pip install langfuse`.

When the agent now queries the underlying LLM, these queries will be logged in Langfuse, where you can analyze the traces.
