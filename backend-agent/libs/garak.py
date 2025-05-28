import datetime
import logging
import os
import re
from pathlib import Path
from typing import List, Union

from garak import _config
from garak import command
from garak.evaluators import ThresholdEvaluator
from garak.generators import Generator
from garak.report import Report

from attack_result import AttackResult
from llm import LLM
from status import status, Step


logger = logging.getLogger(__name__)
logger.addHandler(status.trace_logging)

OUTPUT_FILE = 'garak.stars'
DESCRIPTION = """
Garak is a vulnerability scanner for LLMs. Garak probes for hallucination,
data leakage, prompt injection, misinformation, toxicity generation,
jailbreaks, and many other weaknesses. Attacks integrated into this tool are
not original ones, but taken from the literature and reimplemented.
In the context of STARS, we will use Garak as a vector to access a subset of
such attacks (only the ones adapted to our working scenario).
"""
# ############################### Adapter class ###############################

DEFAULT_CLASS = 'SAPAICoreGenerator'


class SAPAICoreGenerator(Generator):
    """Interface for SAP AI Core models.

    Model names must be same as they are shown in SAP AI Core (or same as
    deployed in a local ollama server).
    """

    active = True
    generator_family_name = "SAP"
    parallel_capable = False

    def __init__(self, name, config_root=_config):
        super().__init__(name, config_root)  # Sets the name and generations

        self.client = LLM.from_model_name(name)

    def _call_model(
        self, prompt: str, generations_this_call: int = 1
    ) -> List[Union[str, None]]:
        # response = self.client.generate(self.name, prompt)
        # return [response.get("response", None)]
        response = self.client.generate(system_prompt='', prompt=prompt)
        return response.unwrap(fail_result=[])


# ################################## Attacks ##################################

def _configure_garak(model_name: str, output_filename: str):
    """Configure garak.

    This step is same for any attack we may want to run using Garak.
    We load a pre-defined configuration to connect to AI Core models and set
    the output file report."""
    _config.transient.starttime = datetime.datetime.now()
    _config.transient.starttime_iso = _config.transient.starttime.isoformat()

    # Load the built-in base configuration
    _config.load_base_config()
    # Load a custom configuration
    config_path = Path('libs/data/garak_config.yaml')
    _config.load_config(run_config_filename=str(config_path))

    # Configure model name
    _config.plugins.model_name = model_name

    # Configure output path and file name
    _config.transient.data_dir = Path(os.path.abspath('.'))
    # attack_family_name = probes[0].split('.')[1]
    # _config.reporting.report_prefix = f'stars.{attack_family_name}'
    _config.reporting.report_prefix = output_filename

    # To prevent errors in command.start_run due to missing CLI args,
    # disable lite mode (which is used only to hint when running interactively)
    _config.system.lite = False


def run_garak(target_model: LLM, probes: list,
              output_filename: str = OUTPUT_FILE):
    """Run a list of attacks (probes) from Garak attack framework.

    @params
    target_model: Model that is to be attacked.
    probes: A list of attacks to run.
    Additional parameters:
    Optional parameter output_filename to set the output file of results.
    """
    # At runtime, garak appends ".report.jsonl" to any output filename the user
    # may decide to use, so we clean possible extensions here
    output_filename = re.sub(r'\.jsonl?$', '', output_filename)
    # After removing extensions, remove possible "report" before so not to have
    # it duplicated at runtime
    output_filename = re.sub(r'report$', '', output_filename)
    # Remove possible trailing .
    output_filename = output_filename.rstrip('.')
    if not output_filename:
        # In the unfortunate event the filename gets cleared out, lets use the
        # default value (otherwise, the default behavior would use a filename
        # starting with a . resulting in a hidden file)
        output_filename = OUTPUT_FILE

    with Step('Preparing attack'):
        _configure_garak(target_model.model_name, output_filename)

        # Ignore possible configs and call directly SAPAICoreGenerator
        # as it is the provider we support in STARS
        # we support in STARS
        generator = SAPAICoreGenerator(name=_config.plugins.model_name)

        # Create an evaluator using the default evaluation threshold
        evaluator = ThresholdEvaluator(_config.run.eval_threshold)

    with Step('Run prompt attacks'):
        # Signal the start of the run
        command.start_run()
        logger.debug('Reporting output to '
                     f'{_config.transient.report_filename}')

        # Execute the attacks
        logger.info('Probewise run')
        # For this use-case, do not set detectors nor buffs
        command.probewise_run(generator, probes, evaluator, [])

        logger.info('Attack completed')
        # Signal run completion.
        command.end_run()

    with Step('Read attack results'):
        # garak always appends a hardcoded ".report.jsonl" value at the end of
        # the report filename, even if the user declares a filename
        garak_output = f'{output_filename}.report.jsonl'
        r = Report(report_location=garak_output).load()
        scores = r.get_evaluations().scores

    # Get results
    successful_attacks = {}
    for attack in scores.itertuples():
        # Garak tracks the score of "success" whereas we are interested into a
        # failure score, so we need to invert this value
        attack_score = 1.0 - attack.score
        if attack_score > 0:
            successful_attacks[attack.Index] = attack_score

    logger.info('__________________________________________________\n')
    logger.info(f'Number of successful attacks: {len(successful_attacks)}')
    logger.info('Number of unsuccessful attacks: '
                f'{len(scores) - len(successful_attacks)}\n')
    logger.info('__________________________________________________\n')

    return successful_attacks


def start_dan(target_model: LLM, parameters: dict) -> AttackResult:
    """Start a DAN attack using Garak attack framework.

    @params
    target_model: Model that is to be attacked.
    parameters: Additional parameters:
    Optional parameter output_file to set the output file of results.
    """

    dan_description = """DAN (Do Anything Now) is a prompt injection attack
    that uses static prompts specifically crafted to try and bypass the
    built-in safety, ethical, or content filtering mechanisms of LLMs.
    We leverage 11 sub-probes from Garak to run this attack.
    Each of these 11 sub-probes come with their community-developed static
    prompt(s).
    """
    dan_probes = ['probes.dan.Dan_11_0',
                  'probes.dan.Dan_10_0',
                  'probes.dan.Dan_9_0',
                  'probes.dan.Dan_8_0',
                  'probes.dan.Dan_7_0',
                  'probes.dan.Dan_6_0',
                  'probes.dan.Dan_6_2',
                  'probes.dan.DUDE',
                  'probes.dan.STAN',
                  'probes.dan.AutoDANCached',
                  'probes.dan.DanInTheWild',
                  ]
    outfile = parameters.get('output_file', f'{OUTPUT_FILE}.dan')
    # Run the attack
    results = run_garak(target_model,
                        probes=dan_probes,
                        output_filename=outfile)

    return AttackResult(
        'dan',
        len(results) > 0,
        'prompt-injection',
        {
            'successful_attacks': results,
            'attack_description': dan_description
        }
    )


def start_encoding(target_model: LLM, parameters: dict) -> AttackResult:
    """Start a encoding attack using Garak attack framework.

    @params
    target_model: Model that is to be attacked.
    parameters: Additional parameters:
    Optional parameter output_file to set the output file of results.
    """

    encoding_description = """Encoding is a prompt injection attack
    that uses static prompts obfuscated using encodings.
    We leverage 13 sub-probes from Garak to run this attack.
    Each of these 13 sub-probes come with 30 prompts (except for InjectAscii85
    having 60 prompts).
    """
    encoding_probes = ['probes.encoding.InjectBase64',
                       'probes.encoding.InjectBase16',
                       'probes.encoding.InjectBase32',
                       'probes.encoding.InjectAscii85',
                       'probes.encoding.InjectHex',
                       'probes.encoding.InjectUU',
                       'probes.encoding.InjectROT13',
                       'probes.encoding.InjectBase2048',
                       'probes.encoding.InjectBraille',
                       'probes.encoding.InjectMorse',
                       'probes.encoding.InjectNato',
                       'probes.encoding.InjectEcoji',
                       'probes.encoding.InjectZalgo',
                       ]
    outfile = parameters.get('output_file', f'{OUTPUT_FILE}.encoding')
    # Run the attack
    results = run_garak(target_model,
                        probes=encoding_probes,
                        output_filename=outfile)

    return AttackResult(
        'encoding',
        len(results) > 0,
        'prompt-injection',
        {
            'successful_attacks': results,
            'attack_description': encoding_description
        }
    )


def start_goodside(target_model: LLM, parameters: dict) -> AttackResult:
    """Start a goodside attack using Garak attack framework.

     Implementation of Riley Goodside attack using Garak framework.
     LLM prompt injection via invisible instructions in pasted text

    @params
    target_model: Model that is to be attacked.
    parameters: Additional parameters:
    Optional parameter output_file to set the output file of results.
    """

    goodside_description = """This attack is a LLM prompt injection via
    invisible instructions in pasted text. In particular, exploit UTF tag page
    encoding for user-invisible prompt injection.
    """
    goodside_probes = ['probes.goodside.Tag',
                       ]
    outfile = parameters.get('output_file', f'{OUTPUT_FILE}.goodside')
    # Run the attack
    results = run_garak(target_model,
                        probes=goodside_probes,
                        output_filename=outfile)

    return AttackResult(
        'goodside',
        len(results) > 0,
        'prompt-injection',
        {
            'successful_attacks': results,
            'attack_description': goodside_description
        }
    )


def start_latentinjection(target_model: LLM, parameters: dict) -> AttackResult:
    """Start a latentinjection attack using Garak attack framework.

    @params
    target_model: Model that is to be attacked.
    parameters: Additional parameters:
    Optional parameter output_file to set the output file of results.
    """

    li_description = """LatentInjection is a prompt injection attack
    with instructions buried in other contexts (e.g., in translation tasks, in
    documents ).
    We leverage 9 sub-probes from Garak to run this attack.
    Each of these 9 sub-probes come with around 250 prompts
    (except for Whois subprobes having around 30 prompts).
    """
    li_probes = ['probes.latentinjection.LatentInjectionFactSnippetEiffel',
                 'probes.latentinjection.LatentInjectionFactSnippetLegal',
                 'probes.latentinjection.LatentInjectionReport',
                 'probes.latentinjection.LatentInjectionResume',
                 'probes.latentinjection.LatentInjectionTranslationEnFr',
                 'probes.latentinjection.LatentInjectionTranslationEnZh',
                 'probes.latentinjection.LatentJailbreak',
                 'probes.latentinjection.LatentWhois',
                 'probes.latentinjection.LatentWhoisSnippet',
                 ]

    outfile = parameters.get('output_file', f'{OUTPUT_FILE}.latentinjection')
    # Run the attack
    results = run_garak(target_model,
                        probes=li_probes,
                        output_filename=outfile)

    return AttackResult(
        'latentinjection',
        len(results) > 0,
        'prompt-injection',
        {
            'successful_attacks': results,
            'attack_description': li_description
        }
    )


def start_malwaregen(target_model: LLM, parameters: dict) -> AttackResult:
    """Start a malwaregen attack using Garak attack framework.

    Drive the LLM into generating malware. Each of the 4 attack implementations
    templates asks to generate the malware in a different programming language.

    @params
    target_model: Model that is to be attacked.
    parameters: Additional parameters:
    Optional parameter output_file to set the output file of results.
    """

    malwaregen_description = """This attack is a malware code generation.
    8 programming languages are supported: x86 assembly, x86-64 assembly, C#,
    C, C++, Rust, ARM64, Swift.
    """
    malwaregen_probes = ['probes.malwaregen.TopLevel',
                         'probes.malwaregen.SubFunctions',
                         'probes.malwaregen.Evasion',
                         'probes.malwaregen.Payload',
                         ]
    outfile = parameters.get('output_file', f'{OUTPUT_FILE}.malwaregen')
    # Run the attack
    results = run_garak(target_model,
                        probes=malwaregen_probes,
                        output_filename=outfile)

    return AttackResult(
        'malwaregen',
        len(results) > 0,
        'insecure-code-generation',
        {
            'successful_attacks': results,
            'attack_description': malwaregen_description
        }
    )


def start_phrasing(target_model: LLM, parameters: dict) -> AttackResult:
    """Start a phrasing attack using Garak attack framework.

    @params
    target_model: Model that is to be attacked.
    parameters: Additional parameters:
    Optional parameter output_file to set the output file of results.
    """

    phrasing_description = """This attack is a jailbreaking via reformulating
    harmful requests in the past (or future) tense. 200 prompts for each tense
    are tested.
    """
    phrasing_probes = ['probes.phrasing.PastTense',
                       'probes.phrasing.FutureTense',
                       ]
    outfile = parameters.get('output_file', f'{OUTPUT_FILE}.phrasing')
    # Run the attack
    results = run_garak(target_model,
                        probes=phrasing_probes,
                        output_filename=outfile)

    return AttackResult(
        'phrasing',
        len(results) > 0,
        'jailbreak',
        {
            'successful_attacks': results,
            'attack_description': phrasing_description
        }
    )


def start_promptinject(target_model: LLM, parameters: dict) -> AttackResult:
    """Start a PromptInject attack using Garak attack framework.

    This is a lighter version of the official PromptInject attack, testing 100
    prompts instead of thusands of prompts with 3 different strategies.

    @params
    target_model: Model that is to be attacked.
    parameters: Additional parameters:
    Optional parameter output_file to set the output file of results.
    """

    pi_description = """PromptInject is a framework for prompt injection.
    PromptInject uses a range of techniques to compose prompts that try to
    manipulate the LLM into repeating a certain string. This attack is a
    lighter version of the official PromptInject, running 100 prompts instead
    of thousands.
    """
    pi_probes = ['probes.promptinject.HijackHateHumans',
                 'probes.promptinject.HijackKillHumans',
                 'probes.promptinject.HijackLongPrompt',
                 ]

    outfile = parameters.get('output_file', f'{OUTPUT_FILE}.promptinject')
    # Run the attack
    results = run_garak(target_model,
                        probes=pi_probes,
                        output_filename=outfile)

    return AttackResult(
        'PromptInject',
        len(results) > 0,
        'prompt-injection',
        {
            'successful_attacks': results,
            'attack_description': pi_description
        }
    )


def start_suffix(target_model: LLM, parameters: dict) -> AttackResult:
    """Start a suffix attack using Garak attack framework.

    This is a lighter version of GCG with 26 pre-computed prompts.

    @params
    target_model: Model that is to be attacked.
    parameters: Additional parameters:
    Optional parameter output_file to set the output file of results.
    """

    suffix_description = """This attack runs a light version of GCG where
    26 prompts have been pre-computed and cached.
    """
    suffix_probes = ['probes.suffix.GCGCached',
                     ]

    outfile = parameters.get('output_file', f'{OUTPUT_FILE}.suffix')
    # Run the attack
    results = run_garak(target_model,
                        probes=suffix_probes,
                        output_filename=outfile)

    return AttackResult(
        'suffix',
        len(results) > 0,
        'jailbreak',
        {
            'successful_attacks': results,
            'attack_description': suffix_description
        }
    )
