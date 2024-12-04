from dataclasses import asdict
import datetime
import json
import logging
import os
from typing import Union

from langchain.callbacks.base import BaseCallbackHandler

from attack_result import SuiteResult
from llm_response import LLMResponse

TRACES_DIRECTORY = 'traces'


class StatusReporter(object):
    """
    This class provides a Singleton that is available all over the backend to
    give status reports to the frontend.

    This is used to display steps, progress bars and reports in the frontend.
    Basically everything that is not a chat message.

    Use the functions by importing the status object created below.
    """

    def __new__(cls):
        """
        Make sure that there is only one instance.
        """
        if not hasattr(cls, 'instance'):
            cls.instance = super(StatusReporter, cls).__new__(cls)
            cls.instance.sock = None
            cls.instance.warned = False
        return cls.instance

    # States reports can be in
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    SKIPPED = 'SKIPPED'
    PENDING = 'PENDING'

    def assert_sock(self):
        if not self.sock:
            if not self.warned:
                logging.warning(
                    'Reporting status failed, because no websocket was \
provided. Skipping further status reports.')
                self.warned = True
            return False
        return True

    def report(self, title: str, status: str):
        """
        Update a report for an action (e.g. substep of an action).

        title: The title of the action (needs to be identifiable)
        status: The status of that action. For the frontend to show an icon, it
        needs to be one of the states defined above (e.g. RUNNING).
        """
        if not self.assert_sock():
            return
        self.sock.send(json.dumps({
            'type': 'report',
            'data': [{
                'title': title,
                'status': status
            }]
        }))

    def clear_report(self):
        """
        Remove all reports in the frontend.
        """
        if not self.assert_sock():
            return
        self.sock.send(json.dumps({
            'type': 'report',
            'reset': True
        }))

    def report_progress(self, current: float, total: float):
        """
        Display the progress of the current action.
        This is shown as progress bar in the frontend.

        current: The current progress. Needs to be smaller than total.
        total: The number of total steps the action takes.
        """
        if not self.assert_sock():
            return
        self.sock.send(json.dumps({
            'type': 'status',
            'current': current,
            'total': total
        }))

    def report_success(self):
        """
        Instantly set the progress bar to complete.
        Can be useful when the action has completed to make sure the bar is
        shown as full.
        """
        if not self.assert_sock():
            return
        self.sock.send(json.dumps({
            'type': 'status',
            'current': 1,
            'total': 1
        }))

    def display_intermediate_result(self, data: str):
        """
        Display the intermediate result of an attack (e.g. the response of an
        LLM under test). Will be displayed as a chat message with different
        style.
        """
        if not self.assert_sock():
            return
        self.sock.send(json.dumps({
            'type': 'intermediate',
            'data': data
        }))

    def display_report_card(self, suite_results: SuiteResult):
        """
        Send a vulnerability card to the frontend to display a report card.
        AttackResults are sorted by vulnerability type.
        """
        reports_by_vuln: dict[list] = {}
        for result in suite_results.results:
            vuln = result.vulnerability_type
            if vuln in reports_by_vuln:
                reports_by_vuln[vuln].append(asdict(result))
            else:
                reports_by_vuln[vuln] = [asdict(result)]
        full_report = [{'vulnerability': v, 'reports': r}
                       for v, r in reports_by_vuln.items()]
        name = suite_results.automatic_save_to_file()
        self.sock.send(json.dumps({
            'type': 'vulnerability-report',
            'data': full_report,
            'name': name
        }))

    ###########################################################################
    #                              TRACING
    #
    # All actions performed by the tool are traced.
    # This means that the action is logged to a file after it is completed,
    # along with meta information, such as time and parameters.
    # For actions that use LLMs, all calls to the LLM are logged.
    #
    # Note that there is only at most one trace going on at any time. Anything
    # that happens during the lifetime of the trace will be written into that
    # object and written to a file at the end.
    ###########################################################################

    def start_trace(self, name: str, parameters: dict, source: str):
        self.trace = {}
        self.trace['name'] = name
        self.trace['source'] = source
        self.trace['parameters'] = parameters
        self.trace['start'] = datetime.datetime.now().isoformat()
        self.trace['llm_messages'] = []

    def trace_llm(self,
                  model_identifier: str,
                  prompt: Union[str, dict],
                  response: LLMResponse):
        """
        Add the input and output of an LLM to the trace.
        """
        message = {
            'model': model_identifier,
            'time': datetime.datetime.now().isoformat(),
            'prompt': prompt,
            'response': response.to_dict()
        }
        self.trace['llm_messages'].append(message)

    def finish_trace(self, completed: bool, output: str):
        """
        Add some more information to the trace and write it to a file.
        """
        self.trace['log'] = self.trace_logging.flush()
        self.trace['completed'] = completed
        self.trace['output'] = str(output)
        file_name = f"{datetime.datetime.now().isoformat()}-{self.trace['name']}.json"  # noqa: E501

        if not os.path.exists(TRACES_DIRECTORY):
            os.makedirs(TRACES_DIRECTORY)

        with open(os.path.join(TRACES_DIRECTORY, file_name), 'w') as f:
            json.dump(self.trace, f, indent=2)

    class TraceLoggingHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.buffer = []

        def emit(self, record):
            self.buffer.append(self.format(record))

        def flush(self):
            output = self.buffer
            self.buffer = []
            return output

    trace_logging = TraceLoggingHandler()


# Instantiation of the Singleton
status = StatusReporter()


class Step:
    """
    Context manager to send reports to the frontend.
    Opening a context represents starting an (atomic) step.
    """

    def __init__(self, title: str):
        self.title = title

    def __enter__(self):
        status.report(self.title, status.RUNNING)

    def __exit__(self, exc_type, exc_value, exc_tb):
        if isinstance(exc_value, Exception):
            status.report(self.title, status.FAILED)
            return False
        else:
            status.report(self.title, status.COMPLETED)


class LangchainStatusCallbackHandler(BaseCallbackHandler):
    """
    This call back handler for Langchain is used to show the user in the
    frontend which tool is currently run (and show when it finishes/ fails).
    """
    raise_error = False
    current_tool = None

    def on_tool_start(
        self, serialized, input_str: str, **kwargs
    ):
        self.current_tool = serialized['name']
        status.report(self.current_tool, StatusReporter.RUNNING)

    def on_tool_end(self, output, **kwargs):
        status.report(self.current_tool, StatusReporter.COMPLETED)

    def on_tool_error(
        self, error, **kwargs
    ):
        status.report(self.current_tool, StatusReporter.FAILED)


class Trace:
    """
    Context manager to manage traces when starting attacks using a spec.
    Managing of traces using the agent is done in the
    LangchainStatusCallbackHandler class above.
    """

    def __init__(self, name: str, parameters: dict):
        status.start_trace(name, parameters, source='spec')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if isinstance(exc_value, Exception):
            status.finish_trace(False, str(exc_value))
            return False
        else:
            pass

    def trace(self, output, print_output=True):
        status.finish_trace(True, output)
        if print_output:
            print(output)
        return output
