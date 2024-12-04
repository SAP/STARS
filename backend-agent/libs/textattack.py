import random
import subprocess

from attack_result import AttackResult
from status import status

# Results
FILE_SUCCESS = 'result_success.txt'
FILE_FAIL = 'result_fail.txt'
FILE_ERROR = 'error.txt'
FILE_SUMMARY = 'summary.txt'

# This array contains a list of attacks from the TextAttack library.
# When we ask the agent to pentest a model, these are the attacks that will
# be run.
# See available attacks here:
# https://github.com/QData/TextAttack?\tab=readme-ov-file#attacks-and-\
# papers-implemented-attack-recipes-textattack-attack---recipe-recipe_name
attacks = [
    'a2t', 'clare', 'checklist', 'pso', 'pruthi', 'iga', 'pwws', 'textfooler',
    'textbugger', 'seq2sick', 'morpheus', 'input-reduction', 'hotflip',
    'deepwordbug', 'faster-alzantot', 'bert-attack', 'bae', 'alzantot',
    'kuleshov'
]

# TODO: load attacks from data files
# TODO: agent should load attacks at runtime


def parse_textattack_result(cli_result: bytes) -> tuple[float, str]:
    """This is an example of a report generated after running an attack using
    TextAttack library. This textual report needs to be parsed and only
    relevant information extracted.
    The relevant information is the body of the table drawn at the bottom.
    ------- Example:

        Attack(
      (search_method): ...
      (goal_function): ...
      (transformation): ...
      (constraints): ...
      (is_black_box): ...
    )

    DATE TIME METHOD predicts: ...
    --------------------------------------------- Result X ---------------------------------------------  # noqa: E501
    [[Positive/Negative (Percentage%)]] --> [[[FAILED]]]

    DESCRIPTION


    +-------------------------------+--------+
    | Attack Results                |        |
    +-------------------------------+--------+
    | Number of successful attacks: | N      |
    | Number of failed attacks:     | N      |
    | Number of skipped attacks:    | N      |
    | Original accuracy:            | X%     |
    | Accuracy under attack:        | X%     |
    | Attack success rate:          | X%     |
    | Average perturbed word %:     | X%     |
    | Average num. words per input: | N      |
    | Avg num queries:              | N      |
    +-------------------------------+--------+
    """
    # TODO: parse with regular expressions
    # CLI result is bytes format but a str is needed
    output = cli_result.decode('utf-8')
    # Split at the beginning of the table drawing
    output_for_parser = output.split('+')
    # The body of the folder is in position 6
    table_body = output_for_parser[6]
    # Get the attack success rate
    new_output = table_body.split('|')
    success_rate = float(new_output[17].replace('%', ''))
    return success_rate, table_body


# TODO
def clean_old_results():
    """Remove files from previous executions of attacks."""
    command = f'rm {FILE_SUCCESS} {FILE_FAIL} {FILE_ERROR} {FILE_SUMMARY}'
    try:
        output = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError as err:
        output = err.output
    # TODO: log if it was ok or not
    print(output)


def run_textattack_recipe(attack: str, model_name: str, dataset: str) -> bool:
    """Run a textattack recipe and log results."""
    # Build TextAttack CLI command
    if dataset:
        # The model is from HuggingFace
        command = f'textattack attack \
            --model-from-huggingface {model_name} \
            --dataset-from-huggingface {dataset} \
            --recipe {attack} \
            --num-examples 3'
    else:
        # The model is local
        command = f"textattack attack \
            --model {model_name} \
            --recipe {attack} \
            --num-examples 3"
    try:
        output = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError as err:
        # Log the attack error and return
        output = err.output  # TODO: log it or remove it
        log_error(attack)
        return False
    success_rate, results = parse_textattack_result(output)
    if success_rate > 50:
        log_summary(attack)
        log_success(attack, results)
        return True
    else:
        log_fail(attack)
        return False


def log_error(attack: str) -> None:
    """Log the name of the attack that raised an error."""
    with open(FILE_ERROR, 'a') as f_error:
        f_error.write(f'{attack}\n')


def log_fail(attack: str) -> None:
    """Log the name of the attack that failed."""
    with open(FILE_FAIL, 'a') as f_fail:
        f_fail.write(f'{attack}\n')


def log_success(attack: str, results: str) -> None:
    """Log the name of the attack and its results.
    The summary should contain a list of attacks with success rate higher than
    a threshold.
    """
    with open(FILE_SUCCESS, 'a') as f_success:
        f_success.write(f'result {attack}\n')
        f_success.write(f'{results}\n')


def log_summary(attack: str) -> None:
    """Log the name of the attack in the summary."""
    with open(FILE_SUMMARY, 'a') as f_summary:
        f_summary.write(f'{attack}\n')


def test():
    # Clean old results
    clean_old_results()
    # Call TextAttack runner using the test model and dataset
    model_name = 'distilbert-base-uncased-finetuned-sst-2-english'
    dataset = 'sst2'
    successes = 0
    # As this is a test, run only 8 random attacks instead of the full list
    quick_attacks = random.sample(attacks, k=8)
    for i, attack in enumerate(quick_attacks):
        print(f'Attack {i + 1} of {len(quick_attacks)}: {attack}')
        status.report_progress(i, len(quick_attacks))
        successes += run_textattack_recipe(attack, model_name, dataset)
    status.report_success()
    return AttackResult(
        'textattack',
        successes > 0,
        'nlp'
    )


def own_model_attack(model_name: str):
    """
    Run textattack on a local model.
    """
    clean_old_results()
    successes = 0
    for i, attack in enumerate(attacks):
        print(f'Attack {i + 1} of {len(attacks)}: {attack}')
        status.report_progress(i, len(attacks))
        successes += run_textattack_recipe(attack, model_name)
    status.report_success()
    return AttackResult(
        'textattack',
        successes > 0,
        'nlp'
    )


def hf_model_attack(model_name: str, dataset: str):
    """
    Run textattack on a hugging face model and dataset.
    """
    # Remove old files
    clean_old_results()
    successes = 0
    # Run attacks
    for i, attack in enumerate(attacks):
        print(f'Attack {i + 1} of {len(attacks)}: {attack}')
        status.report_progress(i, len(attacks))
        successes += run_textattack_recipe(attack, model_name, dataset)
    status.report_success()
    return AttackResult(
        'textattack',
        successes > 0,
        'nlp'
    )
