[![REUSE status](https://api.reuse.software/badge/github.com/SAP/stars)](https://api.reuse.software/info/github.com/SAP/stars)
![Changelog CI Status](https://github.com/SAP/stars/workflows/Changelog%20CI/badge.svg)

# Smart Threat AI Reporting Scanner (STARS)

![stars architecture](docs/stars.png)

## About this project

STARS is a AI agent whose purpose is to conduct vulnerability tests on LLMs from SAP AI Core or from local deployments, or models from HuggingFace. The goal of this project is to identify and correct any potential security vulnerabilities. This can be done using a AI-Agent accessible via a chat frontend or using the CLI.

## Available Attacks

Hereafter, a list with all the attacks the Agent is able to run, grouped by attack type.

### NLP

- [TextAttack](https://github.com/QData/TextAttack)

### Attacks on Large Language Models

- [Promptmap](https://github.com/utkusen/promptmap)
- [GPTFuzz](https://gpt-fuzz.github.io)
- [PyRIT](https://github.com/Azure/PyRIT)
- [CodeAttack](https://github.com/renqibing/CodeAttack)
- [ArtPrompt](https://github.com/uw-nsl/ArtPrompt)
- [Garak](https://github.com/NVIDIA/garak)


## Requirements and Setup

The project is composed of a backend (in `backend-agent` folder) and a UI (an angular application in `frontend` folder). To run the agent both of them are needed, whereas only the backend is needed for the CLI.

For a tutorial on how to use the application, see [the tutorial](docs/Tutorial.md).

Further documentation is available inside the `backend-agent` and `frontend` subdirectories.


## Support, Feedback, Contributing

This project is open to feature requests/suggestions, bug reports etc. via [GitHub issues](https://github.com/SAP/stars/issues). Contribution and feedback are encouraged and always welcome. For more information about how to contribute, the project structure, as well as additional contribution information, see our [Contribution Guidelines](CONTRIBUTING.md).

## Security / Disclosure
If you find any bug that may be a security problem, please follow our instructions at [in our security policy](https://github.com/SAP/stars/security/policy) on how to report it. Please do not create GitHub issues for security-related doubts or problems.

## Code of Conduct

We as members, contributors, and leaders pledge to make participation in our community a harassment-free experience for everyone. By participating in this project, you agree to abide by its [Code of Conduct](https://github.com/SAP/.github/blob/main/CODE_OF_CONDUCT.md) at all times.

## Licensing

Copyright 2024 SAP SE or an SAP affiliate company and stars contributors. Please see our [LICENSE](LICENSE) for copyright and license information. Detailed information including third-party components and their licensing/copyright information is available [via the REUSE tool](https://api.reuse.software/info/github.com/SAP/stars).
