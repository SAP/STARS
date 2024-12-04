# Tutorial

This document should guide you through the usage of the STARS.

![Screenshot of initial page](initial.png)

When starting the tool, a list of functions is provided to the user.

You can interact with the tool like you would with a chatbot, because it
*is* a highly specialized chatbot, what we call "agent".

For example, you could start with:

> How does a vulnerability scan work?

in the chat input (labeled "Your request"). Do not worry too much about
correct spelling, the agent is usually smart enough to understand you.

![Screenshot of question and answer](howdoesscanwork.png)

Indeed a vulnerability scan can easily be started by stating

> Start the vulnerability scan

The agent will then ask for the model to be scanned. In this case spelling is
important, because the exact name of the model will be used to find it.

![Request to start the vulnerability scan](startvulnscan.png)

Some actions, like the vulnerability scan can take some time. But at the end,
you will receive a vulnerability report.

![Vulnerability Report Card](report.png)

While a vulnerability scan contains many attacks, we can also run a single attack framework.
As specified, we have different frameworks available. Let's start with prompt map and ask

> Run a pentest on a Large Language Model using prompt map

For most attack, the agent needs additional information to start the pentest.
In that case the agent will ask for the information.

![The agent is asking which LLM is to test](agentinquire.png)

Provide this information and start the pentest.

> Use gpt-35-turbo

The agent will start the pentest. This may take a while. In our case, we can
see a progress bar indicating how far the attack has progressed.

![A progress bar is shown](progressbar.png)

The agent will provide the result of the pentest. We can ask for additional
information on the pentest.

![The result of the attack](successful.png)

This procedure is applicable to other attacks and other frameworks as well:

- Specify which attack you want to run
- Answer questions to give parameters of the attack
- Wait for the attack to run
- Ask further questions about the result of the pentest if you need more
  information
