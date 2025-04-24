from argparse import Namespace
from dataclasses import asdict
import json
import os
import logging

from attack_result import AttackResult, SuiteResult
from libs.artprompt import start_artprompt, \
    OUTPUT_FILE as artprompt_out_file
from libs.codeattack import start_codeattack, \
    OUTPUT_FILE as codeattack_out_file
from libs.garak import start_dan, \
    start_encoding, start_goodside, \
    start_latentinjection, start_malwaregen, \
    start_phrasing, start_promptinject, \
    start_suffix, \
    OUTPUT_FILE as garak_output_file
from libs.gptfuzz import perform_gptfuzz_attack, \
    OUTPUT_FILE as gptfuzz_out_file
from libs.promptmap import start_prompt_map, \
    OUTPUT_FILE as prompt_map_out_file
from libs.pyrit import start_pyrit_attack
from llm import LLM
from status import Trace

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AttackSpecification:

    """
    Specification for attacks on LLMs. This looks like this:

    {
        'attack' : 'pyrit',
        'parameters' : {
            # Parameters to give to the attack
        },
        'target-model' : 'mistral'
        'attack-model' : 'gpt-4',
        'eval-model' : 'gpt-35-turbo' # Maybe empty
    }

    A specification can be instantiated with the 'create' class method
    and run with 'start'
    """

    # Cli provides some arguments we do not need/want for attacks
    IGNORED_ARGS = ['subcommand', 'dry_run', 'func']

    def __init__(self, spec: dict):
        self.spec = spec

    def load(path: str) -> 'AttackSpecification':
        """
        Load an attack specification from a JSON file.
        """
        with open(path, 'r') as f:
            spec = AttackSpecification(json.load(f))
        return spec

    def serialize(self) -> str:
        """
        Serialize an attack specification to JSON.
        """
        return json.dumps(self.spec, indent=2)

    def create(
            attack: str,
            target: str,
            attack_model: str | None = None,
            eval_model: str | None = None,
            args: Namespace | None = None,
            params: dict | None = None,
    ) -> 'AttackSpecification':
        """
        Instantiate an AttackSpecification with the given parameters and
        return it.

        @args
        attack: The name of the attack to perform
        target: Target model to run the attack against
        attack_model: Model that is used to attack the target. Optional.
        eval_model: Model to evaluate if the attack was successful. Optional.
        params: Specify attack parameters using a dictionary.
        """

        spec = {
            'attack': attack,
            'target-model': target,

        }
        if attack_model:
            spec['attack-model'] = attack_model
        if eval_model:
            spec['eval-model'] = eval_model
        if params:
            spec['parameters'] = {}
            for key, value in params.items():
                if value and key not in AttackSpecification.IGNORED_ARGS:
                    spec['parameters'][key] = value

        return AttackSpecification(spec)

    @property
    def attack(self):
        assert isinstance(self.spec, dict)
        return self.spec['attack']

    @property
    def target_model(self):
        target_model_name = self.spec['target-model']
        return LLM.from_model_name(target_model_name)

    @target_model.setter
    def target_model(self, model_name: str):
        self.spec['target-model'] = model_name

    @property
    def parameters(self):
        if 'parameters' in self.spec:
            return self.spec['parameters']
        return {}

    @property
    def attack_model(self):
        if 'attack-model' not in self.spec:
            raise MisconfigurationException(
                'This attack specification requires an attack model, which was not configured.')  # noqa: E501
        return LLM.from_model_name(self.spec['attack-model'])

    @property
    def eval_model(self):
        if 'eval-model' not in self.spec:
            raise MisconfigurationException(
                'This attack specification requires an eval model, which was not configured.')  # noqa: E501
        return LLM.from_model_name(self.spec['eval-model'])

    def start(self) -> AttackResult:
        """
        Start the attack as specified with this specification.
        """
        with Trace(self.attack, self.spec) as t:
            match self.attack.lower():
                case 'promptmap':
                    return t.trace(start_prompt_map(
                        self.target_model,
                        self.parameters
                    ))
                case 'pyrit':
                    return t.trace(start_pyrit_attack(
                        self.attack_model,
                        self.target_model,
                        self.parameters
                    ), print_output=False)
                case 'gptfuzz':
                    return t.trace(perform_gptfuzz_attack(
                        self.attack_model,
                        self.target_model,
                        self.parameters
                    ))
                case 'codeattack':
                    return t.trace(start_codeattack(
                        self.target_model,
                        self.eval_model,
                        self.parameters
                    ))
                case 'artprompt':
                    return t.trace(start_artprompt(
                        self.target_model,
                        self.eval_model,
                        self.parameters
                    ))
                case 'dan':
                    return t.trace(start_dan(
                        self.target_model,
                        self.parameters
                    ))
                case 'encoding':
                    return t.trace(start_encoding(
                        self.target_model,
                        self.parameters
                    ))
                case 'goodside':
                    return t.trace(start_goodside(
                        self.target_model,
                        self.parameters
                    ))
                case 'latentinjection':
                    return t.trace(start_latentinjection(
                        self.target_model,
                        self.parameters
                    ))
                case 'malwaregen':
                    return t.trace(start_malwaregen(
                        self.target_model,
                        self.parameters
                    ))
                case 'phrasing':
                    return t.trace(start_phrasing(
                        self.target_model,
                        self.parameters
                    ))
                case 'promptinject':
                    return t.trace(start_promptinject(
                        self.target_model,
                        self.parameters
                    ))
                case 'suffix':
                    return t.trace(start_suffix(
                        self.target_model,
                        self.parameters
                    ))
                case _:
                    raise ValueError(f'Attack {self.attack} is not known.')

    @property
    def output_file(self):
        if 'output_file' in self.parameters:
            # TODO when running attacks from garak, the output_file parameter
            # appends .report.jsonl at runtime
            return self.parameters
        match self.attack:
            case 'promptmap':
                return prompt_map_out_file
            case 'gptfuzz':
                return gptfuzz_out_file
            case 'codeattack':
                return codeattack_out_file
            case 'artprompt':
                return artprompt_out_file
            case ('dan' | 'encoding' | 'goodside' | 'latentinjection' |
                  'malwaregen' | 'phrasing' | 'promptinject' | 'suffix'):
                return garak_output_file if \
                    garak_output_file.endswith('.report.jsonl') else \
                    f'{garak_output_file}.report.jsonl'


class AttackSuite():
    """
    AttackSuites combine multiple attacks into one suite, where attacks are
    run sequentially.
    This allows running comprehensive vulnerability scans.
    """

    name: str
    attacks: list[AttackSpecification]
    llm: LLM | None = None

    def from_dict(suite_specification: dict) -> 'AttackSuite':
        """
        Create an AttackSuite from a given attack suite JSON spec dictionary.
        """
        attacks = [AttackSpecification(a)
                   for a in suite_specification['attacks']]
        suite = AttackSuite()
        suite.attacks = attacks
        suite.name = suite_specification['meta']['name']
        return suite

    def set_target(self, target_model: str):
        """
        Set the target model for all attacks in the suite.
        """
        for a in self.attacks:
            a.target_model = target_model

    def run(self, summarize_by_llm: bool = False) -> SuiteResult:
        """
        Run an attack suite, sequentially run all attacks.
        Returns the list of results from the included attacks.

        @args
        summarize_by_llm: Set to true to query an LLM to add a summary to every
        result. Can be useful for displaying results. The LLM is given all the
        information that is included in the AttackResult.
        """
        print(f'Running suite {self.name}')
        full_result = []  # Concatenating results for the agent
        for a in self.attacks:
            try:
                result = a.start()
            except KeyboardInterrupt:
                logger.warning('Attack suite stopped, reporting intermediate '
                               'results. Press Ctrl+C again to cancel.')
                return SuiteResult(full_result)
            except Exception as e:
                logger.error(f'Exception in {a.attack}: {e}')
                full_result.append(
                    AttackResult(a.attack, False, 'unknown',
                                 {
                                     'exception': str(e),
                                     'attack-specification': a.serialize()
                                 })
                )
                continue
            result.details['attack-specification'] = a.serialize()
            if summarize_by_llm:
                summary = self.summarize_attack_result(result)
                result.details['summary'] = summary
            full_result.append(result)
        return SuiteResult(full_result)

    def summarize_attack_result(self, attack_result: AttackResult) -> str:
        system_prompt = """
        You are an assistant in testing Large Language Models for
        vulnerabilities.

        A tool has run a vulnerability scan against an LLM. It is your task to
        summarize the results into a few sentences.
        Explain how the scan/attack was set up and what the result was.
        Assume that the user knows about the general vulnerability type but
        not about this specific scan.

        To create the summary you will get the result of the scan as a JSON.
        The first level keys are the name of the attack/scan, its success (so
        True means the attack was successful, thus a vulnerability was
        discovered) and the vulnerability type.
        On the details key you can find some other information that may be
        relevant, especially the attack-specification, which are the
        parameters that were used to run this scan.

        Remember to only return the summary and nothing else.
    """
        if not self.llm:
            self.llm = LLM.from_model_name(
                os.getenv('RESULT_SUMMARIZE_MODEL', 'gpt-4'))
        result = json.dumps(asdict(attack_result))
        return self.llm.generate(system_prompt=system_prompt, prompt=result)\
            .unwrap_first()


class MisconfigurationException(Exception):
    pass
