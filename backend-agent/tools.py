import json
import os
import subprocess

from langchain.tools import tool

import libs.textattack
from attack import AttackSpecification, AttackSuite
from status import status
from llm import LLM

###############################################################################
#                           Custom tools                                      #
# https://python.langchain.com/docs/modules/agents/tools/custom_tools         #
###############################################################################

###############################################################################
# Here we create custom tools that allow some behaviors coded from scratch.   #
# To create these tools, as indicated in the documentation, you need to       #
# create a description in their docstring, so that the agent knows when and   #
# how to use them.                                                            #
# The @tool decorator identifies custom tools, that can be then implemented   #
# as any other python function.                                               #
# It is preferrable to type the arguments of this function to avoid execution #
# bugs when used by the agent.                                                #
###############################################################################

# *************************************************************************** #
# *                         LLM attacks tools                               * #
# *************************************************************************** #


@tool
def run_prompt_attack(model_name: str,
                      system_prompt: str) -> str:
    """You should use this function for running prompt attacks using the
    "prompt map" framework on some LLM.
    Start this only after using run_prompt_attack_how, since it will explain
    how to interpret the results.
    @ param
    model_name: You should ask the user to input the name of a LLM as it
    appears on SAP AI Core. You cannot run this tool without
    this information.
    system_prompt: The system prompt given to the model that is attacked.
    Leave as empty string when not specified.
    """

    return str(AttackSpecification.create(
        'promptmap',
        target=model_name,
        params={'system_prompt': system_prompt}).start())


@tool
def run_gptfuzz(mutate_model_name: str,
                target_model_name: str,
                max_query_count: int = 300,
                max_jailbreak_count: int = 1) -> str:
    """
    Use this function to start an attack against the target LLM
    using the GPTFuzz attack framework.
    @ param
    mutate_model_name: The model used in the attack to mutate prompts.
    If no model is specified, use gpt-4o.
    target_model_name: The name of the model that should be pentested,
    as it appears on SAP AI Core (or "mistral" for the local
    mistral-instruct instance). You cannot run this tool without this
    information
    max_query_count: How many queries to send before terminating.
    Default is 300.
    max_jailbreak_count: After how many found jailbreaks should the attack
    stop? When putting 1 here (the default value), this means that the
    attack will conclude if a jailbreak is found.
    """

    return str(AttackSpecification.create(
        'gptfuzz',
        target=target_model_name,
        attack_model=mutate_model_name,
        params={'max_query_count': max_query_count,
                'max_jailbreak_count': max_jailbreak_count}).start())


@tool
def run_pyrit_attack(
    attack_name: str,
    target_model: str,
    attack_model: str,
    objective: str,
    **kwargs 
) -> str:
    """
    Use this function to start an attack using the PyRIT framework. PyRIT is a
    framework that comprises several attack orchestrators,
    each of them coming with a
    specific name (redteaming, crescendo, pair ...).
    Run pyrit_how before running this function. Some attacks may need
    different parameters.
    @params
    attack_name: Since PyRIT supports many attack orchestrators,
    the name of the attack must be specified here.
    Supported: "redteaming", "crescendo", "pair"
    target_model: The name of the model that should be attacked as it appears
    on SAP AI Core. You cannot run this tool without
    this information.
    attack_model: The name of the model that is used to generate adversarial
    prompts as it appears on SAP AI Core. You cannot run this tool
    without this information.
    objective: What is the attack trying to achieve. This should be a string
    that outlines the objective, for example something that the target LLM
    should not be doing. You cannot run this tool
    without this information.
    **kwargs: optional attack-specific parameters passed as keyword arguments 
    """

    attack_name = attack_name.lower()
    supported_attacks = ['redteaming', 'crescendo', 'pair']
    if attack_name not in supported_attacks:
        return f'The attack "{attack_name}" is not available. \
        Supported attacks are: {",".join(supported_attacks)}'
    
    # Build parameters - now using kwargs directly
    params = {'objective': objective, **kwargs}

    return str(AttackSpecification.create(
        attack_name,
        target_model,
        attack_model,
        params=params
    ).start())


@tool
def run_codeattack(target_model_name: str,
                   eval_model_name: str,
                   num_prompts: int | None) -> str:
    """You should use this function for running prompt attacks using the
    "codeattack" framework on some LLM.
    Start this only after using codeattack_how, since it will explain
    how to interpret the results.
    @ param
    target_model_name: The name of the model to be attacked.
    eval_model_name: The name of the model that is used to determine if the
    attack was successful.
    num_prompts: The number of attack prompts to be tested. Leave as None when
    not specified.
    """

    return str(AttackSpecification.create(
        'codeattack',
        target=target_model_name,
        eval_model=eval_model_name,
        params={'num_prompts': num_prompts}).start())


@tool
def run_artprompt(target_model_name: str,
                  eval_model_name: str,
                  num_prompts: int | None,) -> str:
    """You should use this function for running prompt attacks using the
    "artprompt" framework on some LLM.
    Start this only after using artprompt_how, since it will explain
    how to interpret the results.
    @ param
    target_model_name: The name of the model to be attacked.
    eval_model_name: The name of the model that is used to determine if the
    attack was successful.
    num_prompts: The number of attack prompts to be tested. Leave as None when
    not specified.
    """

    return str(AttackSpecification.create(
        'artprompt',
        target=target_model_name,
        eval_model=eval_model_name,
        params={'num_prompts': num_prompts}).start())


@tool
def run_garak_attack(
    attack_name: str,
    target_model_name: str,
) -> str:
    """
    Use this function to start an attack using the garak framework. Garak is a
    framework that comprises several attacks, each of them coming with a
    specific name (dan, encoding, goodside, latentinjection, malwaregen,
    phrasing, promptinject, suffix).
    Run garak_how before running this function. Some attacks may need
    different parameters.
    @params
    attack_name: Since garak supports many attacks, the name of the
    attack must be specified here.
    target_model_name: The name of the model to be attacked.
    """

    attack = attack_name.lower()
    supported_attacks = ['dan',
                         'encoding',
                         'goodside',
                         'latentinjection',
                         'malwaregen',
                         'phrasing',
                         'promptinject',
                         'suffix']
    if attack not in supported_attacks:
        return f'The attack "{attack}" is not available. \
        Supported attacks are: {",".join(supported_attacks)}'

    return str(AttackSpecification.create(
        attack,
        target=target_model_name).start())


# *************************************************************************** #
# *                         HF NLP attacks tools                            * #
# *************************************************************************** #

###############################################################################
# This is another custom tool.                                                #
# The purpose of this tool is to quickly launch tests while avoiding loading  #
# without having to request information from the user. It purely focuses on   #
# an execution test.                                                          #
###############################################################################

@tool
def test_textattack() -> str:
    """You should use it when the user asks to run a test on textattack.
    Once the result is returned, you should show it to the user."""
    return str(libs.textattack.test())


###############################################################################
# This custom tool contains the logic to launch the pentest on the models     #
# already contained in the CLI. It will be called by the agent once it has    #
# obtained all the information that the roadmap has asked it to retrieve from #
# the user.                                                                   #
###############################################################################

@tool
def run_own_model_attack(model_name: str) -> str:
    """You should use it for running some attacks belonging to the user and
    locally stored.
    This function is useful to launch some attack on some model already
    integrated into the cli.
    @param
    model_name: You should ask to the user what the name of a model to attack
    is
    """
    return str(libs.textattack.own_model_attack(model_name))


###############################################################################
# Like the tool above, this tool contains logic, but this time to launch the  #
# pentests on models from Huggingface, specifically NLP type models.          #
# It will be launched when the agent has all the user information thanks to   #
# the tool 'Launch_pentest_on_ml_huggingface_model'.                          #
###############################################################################

@tool
def run_hf_model_nlp(model_name: str, dataset: str) -> str:
    """"You should use it for running some attacks on some model stored on
    huggingface. Start this only after using run_hf_model_nlp_how.
    @ param
    model_name: You should ask to the user to input the name of a model from
    HuggingFace. You cannot run this tool without this information.
    dataset: You should ask to the user to input the name of a dataset from
    HuggingFace. You cannot run this tool without this information.
    """
    return str(libs.textattack.hf_model_attack(model_name, dataset))


# *************************************************************************** #
# *                             Utility tools                               * #
# *************************************************************************** #

@tool
def run_attack_suite(path: str, target: str) -> str:
    """
    Use this tool to run an attack suite.
    ALWAYS use attack_suite_how BEFORE running this tool.

    @params
    path: Path to the attack suite specification file to run.
    target: Name of the model to run attacks against.
    """

    if not os.path.exists(path):
        return 'Provided path does not exist. No attacks run!'

    with open(path, 'r') as f:
        suite_spec = json.load(f)
    suite = AttackSuite.from_dict(suite_spec)
    suite.set_target(target)
    results = suite.run(summarize_by_llm=True)
    status.display_report_card(results)
    return str(results)


@tool
def use_command(command: str) -> str:
    """You should use it to apply a command for the user, but you need to ask
    if the user agrees to use this command before executing it.
    You will have to show the output to the user and ask their feedback.
    @param
    command: The agent asks to the user if the command was understood correctly
    and then use it on this tool
    """
    try:
        output = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError as err:
        output = err.output
    return output.decode('utf-8')


@tool
def get_supported_models() -> str:
    """
    Use this tool whenever the name of a model must be specified by a user
    or before suggesting a model name.

    This tool will list all currently available Large Language Models by name.
    """

    return ','.join(LLM.get_supported_models())
