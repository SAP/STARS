import datetime
import logging
import os
from pathlib import Path
from typing import List, Union

from garak import _config
from garak import command
from garak.evaluators import ThresholdEvaluator
from garak.generators import Generator

from attack_result import AttackResult
from llm import LLM
from status import status, Step


logger = logging.getLogger(__name__)
logger.addHandler(status.trace_logging)

OUTPUT_FILE = 'garak.stars'
DESCRIPTION = """
TODO
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
    """ TODO """
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
    # _config.reporting.__report_prefix = f'stars.{attack_family_name}'
    _config.reporting.__report_prefix = output_filename

    # To prevent errors in command.start_run due to missing CLI args,
    # disable lite mode (which is used only to hint when running interactively)
    _config.system.lite = False


def run_garak(target_model: LLM, probes: list,
              output_filename: str = OUTPUT_FILE):
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

    # TODO: the following block is a copypaste from other attacks and must be
    # refined and adapted for garak
    # logger.info(f'Number of successful attacks: {security_failed}')
    # logger.info(f'Number of unsuccessful attacks: {security_passed}\n')
    # logger.info('__________________________________________________\n')
    # logger.info('Here are the successful prompts\n')
    # for attack in successful_attacks:
    #     logger.info('+ ' + attack + '\n')

    # return AttackResult(
    #     'promptmap',
    #     security_failed > 0,
    #     'prompt-injection',
    #     {
    #         'successful_attacks': successful_attacks_json,
    #         'attack_description': DESCRIPTION
    #     }
    # )


def start_dan(target_model: LLM, parameters: dict) -> AttackResult:
    """
    TODO
    """
    dan_probes = ['probes.dan.Dan_11_0',
                  'probes.dan.Dan_10_0',
                  'probes.dan.Dan_9_0',
                  'probes.dan.Dan_8_0',
                  'probes.dan.Dan_7_0',
                  'probes.dan.Dan_6_0',
                  'probes.dan.Dan_6_2',
                  'probes.dan.DUDE',
                  'probes.dan.DUDESTAN',
                  'probes.dan.DUDEAutoDANCached',
                  # TODO: rename it to DanInTheWild from garak v0.11
                  'probes.dan.DanInTheWildMini',
                  ]
    outfile = parameters.get('output_filename', f'{OUTPUT_FILE}.dan')
    run_garak(target_model, probes=dan_probes, output_filename=outfile)
    # TODO: read results from file and return them in our format
