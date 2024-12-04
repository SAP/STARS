from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
import random
import re
import string
import sys


@dataclass
class AttackResult():
    """
    AttackResults are created after running Attacks and store information about
    the attack and the outcome of the attack.

    attack: The name of the attack that was performed.
    success: True means the attack was successful, i.e. the model is vulnerable
    in this regard.
    vulnerability_type: The type of the vulnerability that the model exhibits
    if this attack was successful, e.g. 'jailbreak'. This is stored in the
    AttackResult since some attack frameworks (e.g. PyRIT) can target different
    vulnerabilities.
    details: The details dictionary contains various additional information,
    notably the key attack-specification contains the specification that was
    used to run the attack when running an attack suite.
    """
    attack: str
    success: bool
    vulnerability_type: str
    details: dict

    def __str__(self) -> str:
        result = 'Attack successful' if self.success else \
            'Attack not successful'
        return (f'Result of {self.attack}: {result}. '
                f'Vulnerability: {self.vulnerability_type}. '
                f'Details: {str(self.details)}')


@dataclass
class SuiteResult():
    """
    This class contains the results of an AttackSuite.
    """

    results: list[AttackResult]

    DEFAULT_OUTPUT_PATH = 'reports'
    FILENAME_ALLOWED_CHARS = string.ascii_uppercase + string.digits

    def __str__(self) -> str:
        return '\n'.join([str(r) for r in self.results])

    def sanitize_markdown_content(self, content: str) -> str:
        """
        Escapes Markdown special characters and wraps code content in code
        blocks to prevent malformed Markdown rendering.
        """
        # Escape common Markdown characters
        escape_chars = r'[_*`~>#-]'
        content = re.sub(escape_chars, lambda match: '\\' +
                         match.group(0), content)

        # If content has multiple lines, format it as a code block
        if '\n' in content:
            content = f'\n```\n{content}\n```\n'

        return content

    def get_mime_type(format: str) -> str:
        match format:
            case 'pdf':
                return 'application/pdf'
            case 'json':
                return 'application/json'
            case 'md':
                return 'text/markdown'
        return 'application/octet-stream'

    def to_markdown(self) -> str:
        """
        Format the results of the attack suite into a Markdown string.
        """

        report_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        report = '# Vulnerability Report\n\n'
        report += f'**Date of Report:** {report_date}\n\n'
        report += '## Summary\n\n'
        report += f'Total Attacks: {len(self.results)}\n\n'

        # Add each attack result to the report
        for result in self.results:
            attack_status = '✅ Success' if result.success else '❌ Failure'
            report += f'### {result.attack}\n'
            report += f'- **Status**: {attack_status}\n'
            report += ('- **Vulnerability Type**: '
                       f'{result.vulnerability_type}\n')
            report += '- **Details**:\n'

            # Format the details dictionary
            for key, value in result.details.items():
                if isinstance(value, dict):
                    report += f'  - **{key}**:\n'
                    for sub_key, sub_value in value.items():
                        sub_value_sanitized = self.sanitize_markdown_content(
                            str(sub_value))
                        report += f'    - {sub_key}: {sub_value_sanitized}\n'
                else:
                    value_sanitized = self.sanitize_markdown_content(
                        str(value))
                    report += f'  - **{key}**: {value_sanitized}\n'
            report += '\n'
        return report

    def to_file(
            self,
            output_path: str,
            output_format: str = '') -> str | None:
        """
        Save this SuiteResult into a file

        @args
        output_path: Where to save the file
        output_format: Which format the report should adhere to. Supports JSON
        (json), Markdown (md) and PDF (pdf).
        """
        if output_format == 'json':
            report = json.dumps(
                list(map(lambda ar: asdict(ar), self.results)), indent=2)
        else:
            # Create a generic markdown file, convert it to other formats if
            # requested.
            report = self.to_markdown()
        full_path = output_path
        if not output_path.endswith(output_format):
            full_path = f'{output_path}.{output_format}'

        if output_format == 'pdf':
            # These should be optional dependencies once we have a
            # pyproject.toml to specify them.
            import markdown
            from weasyprint import HTML
            html_content = markdown.markdown(report)
            HTML(string=html_content).write_pdf(full_path)
            print(f'Report written to {full_path}')
            return full_path
        else:
            try:
                with open(full_path, 'w') as f:
                    f.write(report)
                    print(f'Report written to {full_path}')
                    return full_path
            except Exception as e:
                print(e, file=sys.stderr)
                print('Printing report to stdout', file=sys.stderr)
                print(report)

    def automatic_save_to_file(self):
        """
        Save a suite to a file without any arguments.
        This is used by the agent tool, the file name is used to retrieve it
        later.
        """
        name = ''.join(random.choice(self.FILENAME_ALLOWED_CHARS)
                       for _ in range(20))
        path = os.path.join(self.DEFAULT_OUTPUT_PATH, name)
        self.to_file(
            path,
            'json'
        )
        return name

    def load_from_name(name: str) -> 'SuiteResult':
        """
        Load a report from the default directory using the report name / id.
        """
        if not name.endswith('.json'):
            name = name + '.json'
        full_path = os.path.join(SuiteResult.DEFAULT_OUTPUT_PATH, name)
        if not os.path.exists(full_path):
            raise ValueError('Report does not exist')
        with open(full_path, 'r') as f:
            raw_results = json.load(f)
            results = [AttackResult(**r) for r in raw_results]
            return SuiteResult(results)
