from argparse import ArgumentParser, Namespace
import json
import logging
import os
import sys
from typing import Callable

from llm import LLM
from libs.textattack import test as test_textattack, \
    hf_model_attack, \
    own_model_attack, \
    FILE_ERROR as textattack_out_error, \
    FILE_FAIL as textattack_out_fail, \
    FILE_SUCCESS as textattack_out_success, \
    FILE_SUMMARY as textattack_out_summary
from attack import AttackSpecification, AttackSuite
from status import Trace

# Library-free Subcommand utilities from
# https://gist.github.com/mivade/384c2c41c3a29c637cb6c603d4197f9f
cli = ArgumentParser(
    usage='Use the subcommands to perform attacks using integrated libraries.'
)
subparsers = cli.add_subparsers(
    dest='subcommand', help='Tool or library to run')

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S'
)


# Part of the `arg` and `subcommand` functions has been taken from
# ttconv Library v1.0.0
#
# License: BSD-3-Clause New or Revised License
# Release Date: Jan 28, 2021
# Matched File Path: /ttconv/tt.py
def arg(*name_or_flags: str, **kwargs) -> tuple[list[str], dict]:
    """Convenience function to properly format arguments to pass to the
    subcommand decorator.
    """
    return (list(name_or_flags), kwargs)


def subcommand(args=[], parent=subparsers) -> Callable:
    """Decorator to define a new subcommand in a sanity-preserving way.
    The function will be stored in the ``func`` variable when the parser
    parses arguments so that it can be called directly like so::
        args = cli.parse_args()
        args.func(args)
    Usage example::
        @subcommand([argument('-d', help='Enable debug mode', action='store_true')])
        def subcommand(args):
            print(args)
    Then on the command line::
        $ python cli.py subcommand -d
    """  # noqa: E501
    def decorator(func):
        parser = parent.add_parser(func.__name__, description=func.__doc__)
        for arg in args:
            parser.add_argument(*arg[0], **arg[1])
        parser.set_defaults(func=func)
    return decorator


def start_spec(spec: AttackSpecification, args: Namespace):
    if args.dry_run:
        print('Dry run: not running attacks, only outputting specification.'
              'Run the specification with the "run" subcommand.',
              file=sys.stderr)
        print(spec.serialize())
    else:
        result = spec.start()
        if spec.output_file:
            print(f'Full result written to {spec.output_file}')
        return result


@subcommand([arg('target_model', help='Name of the target model to attack'),
             arg('-s', '--system-prompt', type=str,
                 help='The system prompt given to the model that is attacked.'),  # noqa: E501
             arg('--output_file', '-o', help='Output file with results',
                 default=None)])
def promptmap(args):
    spec = AttackSpecification.create(
        'promptmap',
        args.target_model,
        params=vars(args))
    start_spec(spec, args)


@subcommand([arg('target_model', help='Name of the target model to attack'),
             arg('attack_model',
                 help='Name of the model that is used to attack/ mutate prompts'),  # noqa: E501
             arg('-q', '--max-query-count', default=300, type=int,
                 help='Maximum number of queries to send before terminating the attack'),  # noqa: E501
             arg('-j', '--max-jailbreak-count', default=1, type=int,
                 help='Maximum number of jailbreaks needed to achieve before terminating the attack'),  # noqa: E501
             arg('--output_file', '-o', help='Output file with results',
                 default=None)])
def gptfuzz(args):
    spec = AttackSpecification.create(
        'gptfuzz',
        args.target_model,
        attack_model=args.attack_model,
        params=vars(args))
    start_spec(spec, args)


@subcommand([arg('-t', '--test', action='store_true', help='Run a test of random textattack attacks.'),  # noqa: E501
             arg('--local-model', help='The name of a locally stored model.'),
             arg('--hf-model', help='The name of model on HuggingFace.'),
             arg('--hf-dataset', help='The name of a dataset on HuggingFace.')])  # noqa: E501
def textattack(args):
    if args.dry_run:
        print('Attack specifications are only supported for LLM attacks. '
              '--dry-run is not supported.')
        return
    if args.test:
        print(test_textattack())
        return
    if args.local_model:
        with Trace('textattack_local', {'model': args.local_model}) as t:
            t.trace(own_model_attack(args.local_model))
    elif args.hf_model and args.hf_dataset:
        with Trace('textattack_hf', {'model_name': args.hf_model,
                                     'dataset': args.hf_dataset}) as t:
            t.trace(hf_model_attack(args.hf_model, args.hf_dataset))
    else:
        print("""No attack started: Use EITHER
            1. -t for running a test command.
            2. --local_model for running an attack on a local model.
            3. Both --hf_model and --hf_dataset to run an attack on a HuggingFace model.
              """)  # noqa: E501
        return
    print(f'Attacks with errors written to written to {textattack_out_error}')
    print(f'Failed attacks written to written to {textattack_out_fail}')
    print(f'Successful attacks written to written to {textattack_out_success}')
    print(f'Summary of attacks writte to {textattack_out_summary}')


@subcommand([arg('target_model', help='Name of the target model to attack'),
             arg('attack_model',
                 help='Name of the model that is used to attack/ mutate prompts'),  # noqa: E501
             arg('objective', help='What is the attack trying to achieve. This\
                   should be a string that outlines the objective, for example\
                   something that the target LLM should not be doing.'),
             arg('--max-turns', '-t',
                 type=int,
                 help='Number of turns (=prompts to the target) to take before quitting.',  # noqa: E501
                 default=3)])
def pyrit(args):
    spec = AttackSpecification.create(
        'pyrit',
        args.target_model,
        attack_model=args.attack_model,
        params=vars(args))
    result = start_spec(spec, args)
    if not result:
        print('Something went wrong. No result returned from the attack.')
        return
    print(
        'The attack was successful.' if result.success
        else 'The attack was not successful.')
    print('Overall response:')
    print(result.details['response'])


@subcommand([arg('target_model', help='Name of the target model to attack'),
             arg('eval_model',
                 help='Name of the model that is used to determine if the attack was successful',  # noqa: E501
                 ),
             arg('--num_prompts', '-n', help='Number of prompts to test',
                 default=None),
             arg('--output_file', '-o', help='Output file with results',
                 default=None)])
def codeattack(args):
    spec = AttackSpecification.create(
        'codeattack',
        args.target_model,
        eval_model=args.eval_model,
        params=vars(args))
    start_spec(spec, args)


@subcommand([arg('target_model', help='Name of the target model to attack'),
             arg('eval_model',
                 help='Name of the model that is used to determine if the attack was successful',  # noqa: E501
                 ),
             arg('--num_prompts', '-n',
                 help='Number of prompts to test',
                 default=None),
             arg('--output_file', '-o', help='Output file with results',
                 default=None)])
def artprompt(args):
    spec = AttackSpecification.create(
        'artprompt',
        args.target_model,
        eval_model=args.eval_model,
        params=vars(args))
    start_spec(spec, args)


@subcommand([arg('target_model', help='Name of the target model to attack'),
             arg('--output_file', '-o', help='Output file with results',
                 default=None)])
def dan(args):
    spec = AttackSpecification.create(
        'dan',
        args.target_model,
        params=vars(args))
    start_spec(spec, args)


@subcommand([arg('target_model', help='Name of the target model to attack'),
             arg('--output_file', '-o', help='Output file with results',
                 default=None)])
def encoding(args):
    spec = AttackSpecification.create(
        'encoding',
        args.target_model,
        params=vars(args))
    start_spec(spec, args)


@subcommand([arg('target_model', help='Name of the target model to attack'),
             arg('--output_file', '-o', help='Output file with results',
                 default=None)])
def goodside(args):
    spec = AttackSpecification.create(
        'goodside',
        args.target_model,
        params=vars(args))
    start_spec(spec, args)


@subcommand([arg('target_model', help='Name of the target model to attack'),
             arg('--output_file', '-o', help='Output file with results',
                 default=None)])
def latentinjection(args):
    spec = AttackSpecification.create(
        'latentinjection',
        args.target_model,
        params=vars(args))
    start_spec(spec, args)


@subcommand([arg('target_model', help='Name of the target model to attack'),
             arg('--output_file', '-o', help='Output file with results',
                 default=None)])
def malwaregen(args):
    spec = AttackSpecification.create(
        'malwaregen',
        args.target_model,
        params=vars(args))
    start_spec(spec, args)


@subcommand([arg('target_model', help='Name of the target model to attack'),
             arg('--output_file', '-o', help='Output file with results',
                 default=None)])
def phrasing(args):
    spec = AttackSpecification.create(
        'phrasing',
        args.target_model,
        params=vars(args))
    start_spec(spec, args)


@subcommand([arg('target_model', help='Name of the target model to attack'),
             arg('--output_file', '-o', help='Output file with results',
                 default=None)])
def promptinject(args):
    spec = AttackSpecification.create(
        'promptinject',
        args.target_model,
        params=vars(args))
    start_spec(spec, args)


@subcommand([arg('target_model', help='Name of the target model to attack'),
             arg('--output_file', '-o', help='Output file with results',
                 default=None)])
def suffix(args):
    spec = AttackSpecification.create(
        'suffix',
        args.target_model,
        params=vars(args))
    start_spec(spec, args)


@subcommand([arg('file',
                 help='Path to the JSON file containing the attack specification.',  # noqa: E501
                 nargs='?'),
            arg('--target',
                help='Specify a target model if not specified in the spec.',
                type=str),
            arg('--output', '-o',
                help='Path where the output should be stored.',
                default=''),
            arg('--format', '-f',
                help='Specifies the output format. Supported: md, pdf',
                default='md'),
            arg('--summary',
                action='store_true',
                help='Use an LLM to summarize attacks.')])
def run(args):
    """ Run an LLM attack from a specification JSON. """
    if not args.file:
        print(
            'No file given as argument. Enter specification using stdin.',
            file=sys.stderr)
        input = ''
        for line in sys.stdin:
            input += line
            if line == '\n':
                break
        if not input:
            print(
                'Specify the path to an attack specification or give a specification in stdin.', file=sys.stderr)  # noqa: E501
        spec = json.loads(input)
    else:
        with open(args.file, 'r') as f:
            spec = json.load(f)
    if 'attack' in spec:
        # spec specifies an attack
        attack_spec = AttackSpecification(spec)
        attack_spec.start()
    elif 'attacks' in spec:
        # spec specifies an attack suite
        suite = AttackSuite.from_dict(spec)
        suite.set_target(args.target)
        results = suite.run(summarize_by_llm=args.summary)
        if not args.output:
            print(str(results))
        else:
            results.to_file(
                args.output,
                args.format
            )
    else:
        print('JSON is invalid. No attacks run.',
              file=sys.stderr)


@subcommand()
def info(_):
    """
    Get some additional information on the state of the tool, useful for
    future usage.
    """
    available_models = LLM.get_supported_models()
    print('### Available LLMs ###')
    print('These can be used as targets and eval/attack models for attacks.')
    print('-' * 30)
    print('\n'.join(available_models))
    print('### Configuration ###')
    print(f'ENABLE_LANGFUSE={os.getenv("ENABLE_LANGFUSE", False)}')


cli.add_argument('-v', '--verbose',
                 help='Increase verbosity of tools by setting the log level \
                    to INFO.',
                 action='store_true')
cli.add_argument('-d', '--dry-run',
                 help='Don\'t run the attack, only generate an attack specification.',  # noqa: E501
                 action='store_true')

if __name__ == '__main__':
    # Use the app factory to create the Flask app and initialize db
    from app import create_app
    app = create_app()
    args = cli.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    if not args.subcommand:
        cli.print_help()
    else:
        # Flask-SQLAlchemy relies on the application context to manage
        # database connections and configuration
        with app.app_context():
            args.func(args)
