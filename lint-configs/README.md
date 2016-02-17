# StackStorm Lint Configs

This repository contains lint configs for different programming languages and
tools (flake8, pylint, etc.) used by different StackStorm repositories.

Configs are grouped in sub-directories by programming language.

## Usage

To use those configs, add this repository as a git subtree to the repository
where you want to utilize those configs. After that is done, update make
targets (or similar) to correctly pass path to the configs to the tools
in question.

```bash
git subtree add --prefix lint-configs https://github.com/StackStorm/lint-configs.git master --squash
```

To use it (example with pylint)

```bash
pylint -E --rcfile=./lint-configs/python/.pylintrc
...
```

And once you want to pull changes / updates from the lint-configs repository:

```bash
git subtree pull --prefix lint-configs https://github.com/StackStorm/lint-configs.git master --squash
```
