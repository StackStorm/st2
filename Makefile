ROOT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
SHELL := /bin/bash
OS := $(shell uname)

# We separate the OSX X and Linux virtualenvs so we can run in a Docker
# container (st2devbox) while doing things on our host Mac machine
ifeq ($(OS),Darwin)
	VIRTUALENV_DIR ?= virtualenv-osx
	VIRTUALENV_ST2CLIENT_DIR ?= virtualenv-st2client-osx
	VIRTUALENV_ST2CLIENT_PYPI_DIR ?= virtualenv-st2client-pypi-osx
	VIRTUALENV_COMPONENTS_DIR ?= virtualenv-components-osx
else
	VIRTUALENV_DIR ?= virtualenv
	VIRTUALENV_ST2CLIENT_DIR ?= virtualenv-st2client
	VIRTUALENV_ST2CLIENT_PYPI_DIR ?= virtualenv-st2client-pypi
	VIRTUALENV_COMPONENTS_DIR ?= virtualenv-components
endif

# Assign PYTHON_VERSION if it doesn't already exist
PYTHON_VERSION ?= python3

BINARIES := bin

# All components are prefixed by st2 and not .egg-info.
COMPONENTS := $(shell ls -a | grep ^st2 | grep -v .egg-info)
COMPONENTS_RUNNERS := $(wildcard contrib/runners/*)
MOCK_RUNNERS := $(wildcard st2common/tests/runners/*)
COMPONENTS_WITHOUT_ST2TESTS := $(shell ls -a | grep ^st2 | grep -v .egg-info | grep -v st2tests | grep -v st2exporter)

COMPONENTS_WITH_RUNNERS := $(COMPONENTS) $(COMPONENTS_RUNNERS)

COMPONENTS_TEST_DIRS := $(wildcard st2*/tests) $(wildcard contrib/runners/*/tests)

# Components that implement a component-controlled test-runner. These components provide an
# in-component Makefile. (Temporary fix until I can generalize the pecan unittest setup. -mar)
# Note: We also want to ignore egg-info dir created during build
COMPONENT_SPECIFIC_TESTS := st2tests st2client.egg-info

# nasty hack to get a space into a variable
space_char := $(subst ,, )
colon := :
comma := ,
dot := .
slash := /
COMPONENT_PYTHONPATH = $(subst $(space_char),:,$(realpath $(COMPONENTS_WITH_RUNNERS)))
COMPONENTS_TEST := $(foreach component,$(filter-out $(COMPONENT_SPECIFIC_TESTS),$(COMPONENTS_WITH_RUNNERS)),$(component))
COMPONENTS_TEST_COMMA := $(subst $(slash),$(dot),$(subst $(space_char),$(comma),$(COMPONENTS_TEST)))
COMPONENTS_TEST_MODULES := $(subst $(slash),$(dot),$(COMPONENTS_TEST_DIRS))
COMPONENTS_TEST_MODULES_COMMA := $(subst $(space_char),$(comma),$(COMPONENTS_TEST_MODULES))

COVERAGE_GLOBS := .coverage.unit.* .coverage.integration.*
COVERAGE_GLOBS_QUOTED := $(foreach glob,$(COVERAGE_GLOBS),'$(glob)')

REQUIREMENTS := test-requirements.txt requirements.txt

# Redis config for testing
ST2TESTS_REDIS_HOST := 127.0.0.1
ST2TESTS_REDIS_PORT := 6379

# Pin common pip version here across all the targets
# Note! Periodic maintenance pip upgrades are required to be up-to-date with the latest pip security fixes and updates
PIP_VERSION ?= 25.0.1
SETUPTOOLS_VERSION ?= 75.3.0
PIP_OPTIONS := $(ST2_PIP_OPTIONS)

ifndef PYLINT_CONCURRENCY
	PYLINT_CONCURRENCY := 1
endif

ifndef XARGS_CONCURRENCY
	XARGS_CONCURRENCY := 8
endif

ifndef NODE_INDEX
	NODE_INDEX := 0
endif
ifndef NODE_TOTAL
	NODE_TOTAL := 1
endif

# NOTE: We exclude resourceregistrar DEBUG level log messages since those are very noisy (we
# loaded resources for every tests) which makes tests hard to troubleshoot on failure due to
# pages and pages and pages of noise.
# The minus in front of st2.st2common.bootstrap filters out logging statements from that module.
# https://github.com/pytest-dev/pytest-xdist/issues/71
#PYTEST_OPTS := -n auto --tx 2*popen//execmodel=eventlet
# --suppress-no-test-exit-code is part of the pytest-custom_exit_code plugin
PYTEST_OPTS := --test-group=$(NODE_INDEX) --test-group-count=$(NODE_TOTAL) -s --log-level=error --suppress-no-test-exit-code

ifndef PIP_OPTIONS
	PIP_OPTIONS :=
endif

# NOTE: We only run coverage on master and version branches and not on pull requests since
# it has a big performance overhead and is very slow.
ifeq ($(ENABLE_COVERAGE),yes)
	PYTEST_COVERAGE_FLAGS := --with-coverage --cover-branches --cover-erase
	PYTEST_COVERAGE_PACKAGES := --cover-package=$(COMPONENTS_TEST_COMMA)
else
	INCLUDE_TESTS_IN_COVERAGE :=
endif

# If we aren't running test coverage, don't try to include tests in coverage
# results
ifdef INCLUDE_TESTS_IN_COVERAGE
	PYTEST_COVERAGE_FLAGS += --cover-tests
	PYTEST_COVERAGE_PACKAGES := $(PYTEST_COVERAGE_PACKAGES),$(COMPONENTS_TEST_MODULES_COMMA)
endif

.PHONY: all
all: requirements configgen check tests

.PHONY: .coverage_globs
.coverage_globs:
	@for coverage_result in $$( \
		for coverage_glob in $(COVERAGE_GLOBS_QUOTED); do \
			compgen -G $${coverage_glob}; \
		done; \
	); do \
		echo $${coverage_result}; \
	done

# Target for debugging Makefile variable assembly
.PHONY: play
play:
	@echo PYTHON_VERSION=$(PYTHON_VERSION) \($$($(PYTHON_VERSION) --version)\)
	@echo
	@echo COVERAGE_GLOBS=$(COVERAGE_GLOBS_QUOTED)
	@echo
	@echo COMPONENTS=$(COMPONENTS)
	@echo
	@echo COMPONENTS_WITH_RUNNERS=$(COMPONENTS_WITH_RUNNERS)
	@echo
	@echo COMPONENTS_TEST=$(COMPONENTS_TEST)
	@echo
	@echo COMPONENTS_TEST_COMMA=$(COMPONENTS_TEST_COMMA)
	@echo
	@echo COMPONENTS_TEST_DIRS=$(COMPONENTS_TEST_DIRS)
	@echo
	@echo COMPONENTS_TEST_MODULES=$(COMPONENTS_TEST_MODULES)
	@echo
	@echo COMPONENTS_TEST_MODULES_COMMA=$(COMPONENTS_TEST_MODULES_COMMA)
	@echo
	@echo COMPONENT_PYTHONPATH=$(COMPONENT_PYTHONPATH)
	@echo
	@echo TRAVIS_PULL_REQUEST=$(TRAVIS_PULL_REQUEST)
	@echo
	@echo TRAVIS_EVENT_TYPE=$(TRAVIS_EVENT_TYPE)
	@echo
	@echo GITHUB_EVENT_NAME=$(GITHUB_EVENT_NAME)
	@echo
	@echo PYTEST_OPTS=$(PYTEST_OPTS)
	@echo
	@echo ENABLE_COVERAGE=$(ENABLE_COVERAGE)
	@echo
	@echo PYTEST_COVERAGE_FLAGS=$(PYTEST_COVERAGE_FLAGS)
	@echo
	@echo PYTEST_COVERAGE_PACKAGES=$(PYTEST_COVERAGE_PACKAGES)
	@echo
	@echo INCLUDE_TESTS_IN_COVERAGE=$(INCLUDE_TESTS_IN_COVERAGE)
	@echo
	@echo shard: NODE_INDEX/NODE_TOTAL=$(NODE_INDEX)/$(NODE_TOTAL)
	@echo

.PHONY: check
check: check-requirements check-sdist-requirements flake8 checklogs

# NOTE: We pass --no-deps to the script so we don't install all the
# package dependencies which are already installed as part of "requirements"
# make targets. This speeds up the build
.PHONY: install-runners
install-runners:
	@echo ""
	@echo "================== INSTALL RUNNERS ===================="
	@echo ""
	# NOTE: We use xargs to speed things up by installing runners in parallel
	echo -e "$(COMPONENTS_RUNNERS)" | tr -d "\n" | xargs -P $(XARGS_CONCURRENCY) -d " " -n1 -i sh -c ". $(VIRTUALENV_DIR)/bin/activate; cd $$(pwd)/{} ; python setup.py develop --no-deps"
	#@for component in $(COMPONENTS_RUNNERS); do \
	#	echo "==========================================================="; \
	#	echo "Installing runner:" $$component; \
	#	echo "==========================================================="; \
	#	#(. $(VIRTUALENV_DIR)/bin/activate; cd $$component; python setup.py develop --no-deps); \
	#done

.PHONY: install-mock-runners
install-mock-runners:
	@echo ""
	@echo "================== INSTALL MOCK RUNNERS ===================="
	@echo ""
	# NOTE: We use xargs to speed things up by installing runners in parallel
	echo -e "$(MOCK_RUNNERS)" | tr -d "\n" | xargs -P $(XARGS_CONCURRENCY) -d " " -n1 -i sh -c ". $(VIRTUALENV_DIR)/bin/activate; cd $$(pwd)/{} ; python setup.py develop --no-deps"
	#@for component in $(MOCK_RUNNERS); do \
	#	echo "==========================================================="; \
	#	echo "Installing mock runner:" $$component; \
	#	echo "==========================================================="; \
	#	(. $(VIRTUALENV_DIR)/bin/activate; cd $$component; python setup.py develop --no-deps); \
	#done

.PHONY: check-requirements
.check-requirements:
	@echo
	@echo "============== CHECKING REQUIREMENTS =============="
	@echo
	# Update requirements and then make sure no files were changed
	git status -- *requirements.txt */*requirements.txt | grep -q "nothing to commit" || { \
		echo "It looks like you directly modified a requirements.txt file, an"; \
		echo "in-requirements.txt file, or fixed-requirements.txt without running:"; \
		echo ""; \
		echo "    make .requirements"; \
		echo ""; \
		echo "Please update all of the requirements.txt files by running that command"; \
		echo "and committing all of the changed files. You can quickly check the results"; \
		echo "with:"; \
		echo ""; \
		echo "    make .check-requirements"; \
		echo ""; \
		exit 1; \
	}
	@echo "All requirements files are up-to-date!"

.PHONY: check-requirements
check-requirements: .requirements .check-requirements

.PHONY: .check-sdist-requirements
.check-sdist-requirements:
	@echo
	@echo "============== CHECKING SDIST REQUIREMENTS =============="
	@echo
	# Update requirements and then make sure no files were changed
	git status -- */dist_utils.py contrib/runners/*/dist_utils.py | grep -q "nothing to commit" || { \
		echo "It looks like you directly modified a dist_utils.py, or the source "; \
		echo "scripts/dist_utils.py file without running:"; \
		echo ""; \
		echo "    make .sdist-requirements"; \
		echo ""; \
		echo "Please update all of the dist_utils.py files by running that command"; \
		echo "and committing all of the changed files. You can quickly check the results"; \
		echo "with:"; \
		echo ""; \
		echo "    make .check-sdist-requirements"; \
		echo ""; \
		exit 1; \
	}
	@echo "All dist_utils.py files are up-to-date!"

.PHONY: check-sdist-requirements
check-sdist-requirements: .sdist-requirements .check-sdist-requirements

.PHONY: check-python-packages
check-python-packages:
	# Make target which verifies all the components Python packages are valid
	@echo ""
	@echo "================== CHECK PYTHON PACKAGES ===================="
	@echo ""
	test -f $(VIRTUALENV_COMPONENTS_DIR)/bin/activate || $(PYTHON_VERSION) -m venv $(VIRTUALENV_COMPONENTS_DIR) --system-site-packages
	@for component in $(COMPONENTS_WITHOUT_ST2TESTS); do \
		echo "==========================================================="; \
		echo "Checking component:" $$component; \
		echo "==========================================================="; \
		(set -e; cd $$component; ../$(VIRTUALENV_COMPONENTS_DIR)/bin/python setup.py --version) || exit 1; \
	done

.PHONY: check-python-packages-nightly
check-python-packages-nightly:
	# NOTE: This is subset of check-python-packages target.
	# We run more extensive and slower tests as part of the nightly build to speed up PR builds
	@echo ""
	@echo "================== CHECK PYTHON PACKAGES ===================="
	@echo ""

	test -f $(VIRTUALENV_COMPONENTS_DIR)/bin/activate || $(PYTHON_VERSION) -m venv $(VIRTUALENV_COMPONENTS_DIR) --system-site-packages
	$(VIRTUALENV_COMPONENTS_DIR)/bin/pip install wheel
	@for component in $(COMPONENTS_WITHOUT_ST2TESTS); do \
		echo "==========================================================="; \
		echo "Checking component:" $$component; \
		echo "==========================================================="; \
		(set -e; cd $$component; ../$(VIRTUALENV_COMPONENTS_DIR)/bin/python setup.py --version) || exit 1; \
		(set -e; cd $$component; ../$(VIRTUALENV_COMPONENTS_DIR)/bin/python setup.py sdist bdist_wheel) || exit 1; \
		(set -e; cd $$component; ../$(VIRTUALENV_COMPONENTS_DIR)/bin/python setup.py develop --no-deps) || exit 1; \
		($(VIRTUALENV_COMPONENTS_DIR)/bin/python -c "import $$component") || exit 1; \
		(set -e; cd $$component; rm -rf dist/; rm -rf $$component.egg-info) || exit 1; \
	done

.PHONY: ci-checks-nightly
# TODO: Ony run micro-benchmarks once a week since they are extremly slow on CI
ci-checks-nightly: check-python-packages-nightly
#ci-checks-nightly: check-python-packages-nightly micro-benchmarks

# CI checks which are very slow and only run on a weekly basic
.PHONY: ci-checks-weekly
ci-checks-weekly: micro-benchmarks

.PHONY: checklogs
checklogs:
	@echo
	@echo "================== LOG WATCHER ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; python ./tools/log_watcher.py 10

.PHONY: pylint
pylint: requirements .pylint

.PHONY: configgen
configgen: requirements .configgen

.PHONY: .shellcheck
.shellcheck:
	@echo
	@echo "================== shellcheck ===================="
	@echo
	shellcheck scripts/ci/*.sh
	shellcheck scripts/github/*.sh
	shellcheck scripts/*.sh

.PHONY: .configgen
.configgen:
	@echo
	@echo "================== config gen ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; python ./tools/config_gen.py > conf/st2.conf.sample;

.PHONY: schemasgen
schemasgen: requirements .schemasgen

.PHONY: .schemasgen
.schemasgen:
	@echo
	@echo "================== content model schemas gen ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; python ./st2common/bin/st2-generate-schemas;

.PHONY: .pylint
.pylint:
	@echo
	@echo "================== pylint ===================="
	@echo
	@echo "==========================================================="; \
	echo "Test our custom pylint plugins before we use them"; \
	echo "==========================================================="; \
	. $(VIRTUALENV_DIR)/bin/activate ; pytest pylint_plugins || exit 1
	# Lint st2 components
	@for component in $(COMPONENTS); do\
		echo "==========================================================="; \
		echo "Running pylint on" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate ; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models --load-plugins=pylint_plugins.db_models $$component/$$component || exit 1; \
	done
	# Lint runner modules and packages
	@for component in $(COMPONENTS_RUNNERS); do\
		echo "==========================================================="; \
		echo "Running pylint on" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate ; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models --load-plugins=pylint_plugins.db_models $$component/*.py || exit 1; \
	done
	# Lint Python pack management actions
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models contrib/packs/actions/*.py || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models contrib/packs/actions/*/*.py || exit 1;
	# Lint other packs
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models contrib/linux/*/*.py || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models contrib/chatops/*/*.py || exit 1;
	# Lint Python scripts
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models scripts/*.py || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc --load-plugins=pylint_plugins.api_models tools/*.py || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; pylint -j $(PYLINT_CONCURRENCY) -E --rcfile=./lint-configs/python/.pylintrc pylint_plugins/*.py || exit 1;

# Black task which checks if the code comforts to black code style
.PHONY: black-check
black: requirements .black-check

.PHONY: .black-check
.black-check:
	@echo
	@echo "================== black-check ===================="
	@echo
	# st2 components
	@for component in $(COMPONENTS); do\
		echo "==========================================================="; \
		echo "Running black on" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate ; black --check --config pyproject.toml $$component/ || exit 1; \
		if [ -d "$$component/bin" ]; then \
			. $(VIRTUALENV_DIR)/bin/activate ; black $$(grep -rl '^#!/.*python' $$component/bin) || exit 1; \
		fi \
	done
	# runner modules and packages
	@for component in $(COMPONENTS_RUNNERS); do\
		echo "==========================================================="; \
		echo "Running black on" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate ; black --check --config pyproject.toml $$component/ || exit 1; \
		if [ -d "$$component/bin" ]; then \
			. $(VIRTUALENV_DIR)/bin/activate ; black $$(grep -rl '^#!/.*python' $$component/bin) || exit 1; \
		fi \
	done
	. $(VIRTUALENV_DIR)/bin/activate; black --check --config pyproject.toml contrib/ || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; black --check --config pyproject.toml scripts/*.py || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; black --check --config pyproject.toml tools/*.py || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; black --check --config pyproject.toml pylint_plugins/*.py || exit 1;

# Black task which reformats the code using black
.PHONY: black
black: requirements .black-format

.PHONY: .black-format
.black-format:
	@echo
	@echo "================== black ===================="
	@echo
	# st2 components
	@for component in $(COMPONENTS); do\
		echo "==========================================================="; \
		echo "Running black on" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate ; black --config pyproject.toml $$component/ || exit 1; \
		if [ -d "$$component/bin" ]; then \
			. $(VIRTUALENV_DIR)/bin/activate ; black --config pyproject.toml $$(grep -rl '^#!/.*python' $$component/bin) || exit 1; \
		fi \
	done
	# runner modules and packages
	@for component in $(COMPONENTS_RUNNERS); do\
		echo "==========================================================="; \
		echo "Running black on" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate ; black --config pyproject.toml  $$component/ || exit 1; \
		if [ -d "$$component/bin" ]; then \
			. $(VIRTUALENV_DIR)/bin/activate ; black --config pyproject.toml $$(grep -rl '^#!/.*python' $$component/bin) || exit 1; \
		fi \
	done
	. $(VIRTUALENV_DIR)/bin/activate; black --config pyproject.toml contrib/ || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; black --config pyproject.toml scripts/*.py || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; black --config pyproject.toml tools/*.py || exit 1;
	. $(VIRTUALENV_DIR)/bin/activate; black --config pyproject.toml pylint_plugins/*.py || exit 1;

.PHONY: pre-commit-checks
black: requirements .pre-commit-checks

# Ensure all files contain no trailing whitespace + that all YAML files are valid.
.PHONY: .pre-commit-checks
.pre-commit-checks:
	@echo
	@echo "================== pre-commit-checks ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; pre-commit run trailing-whitespace --all --show-diff-on-failure
	. $(VIRTUALENV_DIR)/bin/activate; pre-commit run check-yaml --all --show-diff-on-failure
.PHONY: lint-api-spec
lint-api-spec: requirements .lint-api-spec

.PHONY: .lint-api-spec
.lint-api-spec:
	@echo
	@echo "================== Lint API spec ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; python st2common/bin/st2-validate-api-spec --config-file conf/st2.dev.conf

.PHONY: generate-api-spec
generate-api-spec: requirements .generate-api-spec

.PHONY: .generate-api-spec
.generate-api-spec: .lint-api-spec
	@echo
	@echo "================== Generate openapi.yaml file ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; python st2common/bin/st2-generate-api-spec --config-file conf/st2.dev.conf > st2common/st2common/openapi.yaml

.PHONY: circle-lint-api-spec
circle-lint-api-spec:
	@echo
	@echo "================== Lint API spec ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; python st2common/bin/st2-validate-api-spec --config-file conf/st2.dev.conf || echo "Open API spec lint failed."

.PHONY: flake8
flake8: requirements .flake8

.PHONY: .flake8
.flake8:
	@echo
	@echo "==================== flake ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 $(COMPONENTS)
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 $(COMPONENTS_RUNNERS)
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 contrib/packs/actions/
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 contrib/linux
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 contrib/chatops/
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 scripts/
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 tools/
	. $(VIRTUALENV_DIR)/bin/activate; flake8 --config ./lint-configs/python/.flake8 pylint_plugins/

# Make task which verifies st2client README will parse pypi checks
.PHONY: .st2client-pypi-check
.st2client-pypi-check:
	@echo
	@echo "==================== st2client pypi check ===================="
	@echo
	test -f $(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/activate || $(PYTHON_VERSION) -m venv $(VIRTUALENV_ST2CLIENT_PYPI_DIR)

	# Setup PYTHONPATH in bash activate script...
	# Delete existing entries (if any)
	sed -i '/_OLD_PYTHONPATHp/d' $(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/activate
	sed -i '/PYTHONPATH=/d' $(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/activate
	sed -i '/export PYTHONPATH/d' $(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/activate
	echo '_OLD_PYTHONPATH=$$PYTHONPATH' >> $(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/activate
	echo 'PYTHONPATH=${ROOT_DIR}:$(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/activate
	echo 'export PYTHONPATH' >> $(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/activate
	touch $(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/activate
	chmod +x $(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/activate

	$(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/pip install --upgrade "pip==$(PIP_VERSION)"
	$(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/pip install --upgrade "readme_renderer"
	$(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/pip install --upgrade "restructuredtext-lint"

	# Check with readme-renderer
	. $(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/activate; cd st2client ; ../$(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/python -m readme_renderer README.rst
	# Check with rst-lint - encounters errors that readme_renderer doesn't, but pypi complains about
	. $(VIRTUALENV_ST2CLIENT_PYPI_DIR)/bin/activate; cd st2client ; rst-lint README.rst

# Make task which verifies st2client installs and works fine
.PHONY: .st2client-install-check
.st2client-install-check:
	@echo
	@echo "==================== st2client install check ===================="
	@echo
	test -f $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate || $(PYTHON_VERSION) -m venv $(VIRTUALENV_ST2CLIENT_DIR)

	# Setup PYTHONPATH in bash activate script...
	# Delete existing entries (if any)
	sed -i '/_OLD_PYTHONPATHp/d' $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate
	sed -i '/PYTHONPATH=/d' $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate
	sed -i '/export PYTHONPATH/d' $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate

	echo '_OLD_PYTHONPATH=$$PYTHONPATH' >> $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate
	echo 'PYTHONPATH=${ROOT_DIR}:$(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate
	echo 'export PYTHONPATH' >> $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate
	touch $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate
	chmod +x $(VIRTUALENV_ST2CLIENT_DIR)/bin/activate

	$(VIRTUALENV_ST2CLIENT_DIR)/bin/pip install --upgrade "pip==$(PIP_VERSION)"
	$(VIRTUALENV_ST2CLIENT_DIR)/bin/pip install --upgrade "setuptools==$(SETUPTOOLS_VERSION)"

	$(VIRTUALENV_ST2CLIENT_DIR)/bin/activate; cd st2client ; ../$(VIRTUALENV_ST2CLIENT_DIR)/bin/python setup.py install ; cd ..
	$(VIRTUALENV_ST2CLIENT_DIR)/bin/st2 --version
	$(VIRTUALENV_ST2CLIENT_DIR)/bin/python -c "import st2client"

.PHONY: bandit
bandit: requirements .bandit

.PHONY: .bandit
.bandit:
	@echo
	@echo "==================== bandit ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; bandit -r $(COMPONENTS_WITH_RUNNERS) -lll -x build,dist

.PHONY: lint
lint: requirements .lint

.PHONY: .lint
.lint: .generate-api-spec .black-check .pre-commit-checks .flake8 .pylint .st2client-dependencies-check .st2common-circular-dependencies-check .rst-check .st2client-install-check

.PHONY: clean
clean: .cleanpycs

.PHONY: compilepy3
compilepy3:
	@echo "======================= compile ========================"
	@echo "------- Compile all .py files (syntax check test - Python 3) ------"
	python3 -m compileall -f -q -x 'virtualenv|virtualenv-osx|virtualenv-py3|.tox|.git|.venv-st2devbox|./st2tests/st2tests/fixtures/packs/test|./pants-plugins' .

.PHONY: .cleanpycs
.cleanpycs:
	@echo "Removing all .pyc files"
	find $(COMPONENTS_WITH_RUNNERS)  -name \*.pyc -type f -print0 | xargs -0 -I {} rm {}

.PHONY: .st2client-dependencies-check
.st2client-dependencies-check:
	@echo "Checking for st2common imports inside st2client"
	find ${ROOT_DIR}/st2client/st2client/ -name \*.py -type f -print0 | xargs -0 cat | grep st2common ; test $$? -eq 1

.PHONY: .st2common-circular-dependencies-check
.st2common-circular-dependencies-check:
	@echo "Checking st2common for circular dependencies"
	find ${ROOT_DIR}/st2common/st2common/ -name \*.py -type f -print0 | xargs -0 cat | grep st2reactor ; test $$? -eq 1
	find ${ROOT_DIR}/st2common/st2common/ \( -name \*.py ! -name runnersregistrar\.py -name \*.py ! -name compat\.py ! -name inquiry\.py \) -type f -print0 | xargs -0 cat | grep st2actions ; test $$? -eq 1
	find ${ROOT_DIR}/st2common/st2common/ -name \*.py -type f -print0 | xargs -0 cat | grep st2api ; test $$? -eq 1
	find ${ROOT_DIR}/st2common/st2common/ -name \*.py -type f -print0 | xargs -0 cat | grep st2auth ; test $$? -eq 1
	find ${ROOT_DIR}/st2common/st2common/ \( -name \*.py ! -name router\.py -name \*.py \) -type f -print0 | xargs -0 cat | grep st2stream; test $$? -eq 1
	find ${ROOT_DIR}/st2common/st2common/ -name \*.py -type f -print0 | xargs -0 cat | grep st2exporter; test $$? -eq 1

.PHONY: micro-benchmarks
micro-benchmarks: requirements .micro-benchmarks

.PHONY: .micro-benchmarks
.micro-benchmarks:
	@echo
	@echo "==================== micro-benchmarks ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:fixture_file -s -v st2common/benchmarks/micro/test_mongo_field_types.py -k "test_save_large_execution"
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:fixture_file -s -v st2common/benchmarks/micro/test_mongo_field_types.py -k "test_read_large_execution"
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:fixture_file -s -v st2common/benchmarks/micro/test_mongo_field_types.py -k "test_save_multiple_fields"
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:fixture_file -s -v st2common/benchmarks/micro/test_mongo_field_types.py -k "test_save_large_string_value"
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:fixture_file -s -v st2common/benchmarks/micro/test_mongo_field_types.py -k "test_read_large_string_value"
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:fixture_file -s -v st2common/benchmarks/micro/test_mongo_transport_compression.py -k "test_save_execution"
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:fixture_file -s -v st2common/benchmarks/micro/test_mongo_transport_compression.py -k "test_read_execution"
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:dict_keys_count_and_depth -s -v st2common/benchmarks/micro/test_fast_deepcopy.py -k "test_fast_deepcopy_with_dict_values"
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:fixture_file -s -v st2common/benchmarks/micro/test_fast_deepcopy.py -k "test_fast_deepcopy_with_json_fixture_file"
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:fixture_file,param:indent_sort_keys_tuple -s -v st2common/benchmarks/micro/test_json_serialization_and_deserialization.py -k "test_json_dumps"
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:fixture_file -s -v st2common/benchmarks/micro/test_json_serialization_and_deserialization.py -k "test_json_loads"
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:fixture_file -s -v st2common/benchmarks/micro/test_json_serialization_and_deserialization.py -k "test_orjson_dumps"
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:fixture_file -s -v st2common/benchmarks/micro/test_publisher_compression.py -k "test_pickled_object_compression"
	. $(VIRTUALENV_DIR)/bin/activate; pytest --benchmark-histogram=benchmark_histograms/benchmark --benchmark-only --benchmark-name=short --benchmark-columns=min,max,mean,stddev,median,ops,rounds --benchmark-group-by=group,param:fixture_file -s -v st2common/benchmarks/micro/test_publisher_compression.py -k "test_pickled_object_compression_publish"

.PHONY: .cleanmongodb
.cleanmongodb:
	@echo "==================== cleanmongodb ===================="
	@echo "----- Dropping all MongoDB databases -----"
	@sudo pkill -9 mongod
	@sudo rm -rf /var/lib/mongodb/*
	@sudo chown -R mongodb:mongodb /var/lib/mongodb/
	@sudo service mongodb start
	@sleep 15
	@mongo --eval "rs.initiate()"
	@sleep 15

.PHONY: .cleanrabbitmq
.cleanrabbitmq:
	@echo "==================== cleanrabbitmq ===================="
	@echo "Deleting all RabbitMQ queue and exchanges"
	@sudo rabbitmqctl stop_app
	@sudo rabbitmqctl reset
	@sudo rabbitmqctl start_app

.PHONY: .cleancoverage
.cleancoverage:
	@echo "==================== cleancoverage ===================="
	@echo "Removing all coverage results directories"
	@echo
	rm -rf .coverage $(COVERAGE_GLOBS) \
		.coverage.unit .coverage.integration

.PHONY: distclean
distclean: clean
	@echo
	@echo "==================== distclean ===================="
	@echo
	rm -rf $(VIRTUALENV_DIR)

.PHONY: .sdist-requirements
.sdist-requirements:
	# Copy over shared dist utils module which is needed by setup.py
	@for component in $(COMPONENTS_WITH_RUNNERS); do\
		cp -f ./scripts/dist_utils.py $$component/dist_utils.py;\
		scripts/write-headers.sh $$component/dist_utils.py || break;\
	done

	# Copy over CHANGELOG.RST, CONTRIBUTING.RST and LICENSE file to each component directory
	#@for component in $(COMPONENTS_TEST); do\
	#	test -s $$component/README.rst || cp -f README.rst $$component/; \
	#	cp -f CONTRIBUTING.rst $$component/; \
	#	cp -f LICENSE $$component/; \
	#done

.PHONY: .requirements
.requirements: virtualenv
	$(VIRTUALENV_DIR)/bin/pip install --upgrade "pip==$(PIP_VERSION)"
	# Print out pip version
	$(VIRTUALENV_DIR)/bin/pip --version
	# Generate all requirements to support current CI pipeline.
	$(VIRTUALENV_DIR)/bin/python scripts/fixate-requirements.py --skip=virtualenv,virtualenv-osx -s st2*/in-requirements.txt contrib/runners/*/in-requirements.txt -f fixed-requirements.txt -o requirements.txt

	# Remove any *.egg-info files which polute PYTHONPATH
	rm -rf *.egg-info*

	# Generate finall requirements.txt file for each component
	# NOTE: We use xargs to speed things up by running commands in parallel
	echo -e "$(COMPONENTS_WITH_RUNNERS)" | tr -d "\n" | xargs -P $(XARGS_CONCURRENCY) -d " " -n1 -i sh -c "$(VIRTUALENV_DIR)/bin/python scripts/fixate-requirements.py --skip=virtualenv,virtualenv-osx -s {}/in-requirements.txt -f fixed-requirements.txt -o {}/requirements.txt"

	#@for component in $(COMPONENTS_WITH_RUNNERS); do\
	#	echo "==========================================================="; \
	#	echo "Generating requirements.txt for" $$component; \
	#	$(VIRTUALENV_DIR)/bin/python scripts/fixate-requirements.py --skip=virtualenv,virtualenv-osx -s $$component/in-requirements.txt -f fixed-requirements.txt -o $$component/requirements.txt; \
	#done

	@echo "==========================================================="

.PHONY: requirements
requirements: virtualenv .requirements .sdist-requirements install-runners install-mock-runners
	@echo
	@echo "==================== requirements ===================="
	@echo
	# Show pip installed packages before we start
	echo ""
	$(VIRTUALENV_DIR)/bin/pip list
	echo ""

	# Note: Use the verison of virtualenv pinned in fixed-requirements.txt so we
	#       only have to update it one place when we change the version
	$(VIRTUALENV_DIR)/bin/pip install --upgrade $(shell grep "^virtualenv" fixed-requirements.txt)
	$(VIRTUALENV_DIR)/bin/pip install --upgrade "setuptools==$(SETUPTOOLS_VERSION)"  # workaround for pbr issue

	# Install requirements
	for req in $(REQUIREMENTS); do \
		echo "Installing $$req..." ; \
		$(VIRTUALENV_DIR)/bin/pip install $(PIP_OPTIONS) -r $$req ; \
	done

	# Install st2common package to load drivers defined in st2common setup.py
	# NOTE: We pass --no-deps to the script so we don't install all the
	# package dependencies which are already installed as part of "requirements"
	# make targets. This speeds up the build
	(cd ${ROOT_DIR}/st2common; ${ROOT_DIR}/$(VIRTUALENV_DIR)/bin/python setup.py develop --no-deps)

	# Install st2common to register metrics drivers
	# NOTE: We pass --no-deps to the script so we don't install all the
	# package dependencies which are already installed as part of "requirements"
	# make targets. This speeds up the build
	(cd ${ROOT_DIR}/st2common; ${ROOT_DIR}/$(VIRTUALENV_DIR)/bin/python setup.py develop --no-deps)

	# Install st2auth to register SSO drivers
	# NOTE: We pass --no-deps to the script so we don't install all the
	# package dependencies which are already installed as part of "requirements"
	# make targets. This speeds up the build
	(cd ${ROOT_DIR}/st2auth; ${ROOT_DIR}/$(VIRTUALENV_DIR)/bin/python setup.py develop --no-deps)

	# Some of the tests rely on submodule so we need to make sure submodules are check out
	git submodule update --init --recursive --remote

	# Show currently install requirements
	echo ""
	$(VIRTUALENV_DIR)/bin/pip list
	echo ""

.PHONY: check-dependency-conflicts
check-dependency-conflicts:
	@echo
	@echo "==================== check-dependency-conflicts ===================="
	@echo
	# Verify there are no conflicting dependencies
	cat st2*/requirements.txt contrib/runners/*/requirements.txt | sort -u > req.txt && \
	$(VIRTUALENV_DIR)/bin/pip-compile --strip-extras --output-file req.out req.txt || exit 1; \
	rm -f req.txt req.out

.PHONY: virtualenv
	# Note: We always want to update virtualenv/bin/activate file to make sure
	# PYTHONPATH is up to date and to avoid caching issues on Travis
virtualenv:
	@echo
	@echo "==================== virtualenv ===================="
	@echo
	test -f $(VIRTUALENV_DIR)/bin/activate || $(PYTHON_VERSION) -m venv $(VIRTUALENV_DIR)

	# Setup PYTHONPATH in bash activate script...
	# Delete existing entries (if any)
ifeq ($(OS),Darwin)
	echo 'Setting up virtualenv on $(OS)...'
	sed -i '' '/_OLD_PYTHONPATHp/d' $(VIRTUALENV_DIR)/bin/activate
	sed -i '' '/PYTHONPATH=/d' $(VIRTUALENV_DIR)/bin/activate
	sed -i '' '/export PYTHONPATH/d' $(VIRTUALENV_DIR)/bin/activate
else
	echo 'Setting up virtualenv on $(OS)...'
	sed -i '/_OLD_PYTHONPATHp/d' $(VIRTUALENV_DIR)/bin/activate
	sed -i '/PYTHONPATH=/d' $(VIRTUALENV_DIR)/bin/activate
	sed -i '/export PYTHONPATH/d' $(VIRTUALENV_DIR)/bin/activate
endif

	echo '_OLD_PYTHONPATH=$$PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	#echo 'PYTHONPATH=$$_OLD_PYTHONPATH:$(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'PYTHONPATH=${ROOT_DIR}:$(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'export PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	touch $(VIRTUALENV_DIR)/bin/activate

	# Setup PYTHONPATH in fish activate script...
	#echo '' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo 'set -gx _OLD_PYTHONPATH $$PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo 'set -gx PYTHONPATH $$_OLD_PYTHONPATH $(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo 'functions -c deactivate old_deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo 'function deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo '  if test -n $$_OLD_PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo '    set -gx PYTHONPATH $$_OLD_PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo '    set -e _OLD_PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo '  end' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo '  old_deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo '  functions -e old_deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#echo 'end' >> $(VIRTUALENV_DIR)/bin/activate.fish
	#touch $(VIRTUALENV_DIR)/bin/activate.fish

	# debug pip installed packages
	$(VIRTUALENV_DIR)/bin/pip list

.PHONY: reset-submodules
reset-submodules:
	git submodule foreach --recursive git reset --hard

.PHONY: reinit-submodules
reinit-submodules:
	# Unbind all submodules
	git submodule deinit -f .
	# Checkout again
	git submodule update --init --recursive

.PHONY: tests
tests: pytests

.PHONY: pytests
pytests: compilepy3 requirements .flake8 .pylint .pytests-coverage

.PHONY: .pytests
.pytests: compilepy3 .configgen .generate-api-spec .unit-tests clean

.PHONY: .pytests-coverage
.pytests-coverage: .unit-tests-coverage-html clean

.PHONY: unit-tests
unit-tests: requirements .unit-tests

.PHONY: .unit-tests
.unit-tests:
	@echo
	@echo "==================== tests ===================="
	@echo
	@echo "----- Dropping st2-test db -----"
	@mongosh st2-test --eval "db.dropDatabase();"
	@failed=0; \
	for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "-----------------------------------------------------------"; \
		. $(VIRTUALENV_DIR)/bin/activate; \
		 ST2TESTS_REDIS_HOST=$(ST2TESTS_REDIS_HOST) \
		 ST2TESTS_REDIS_PORT=$(ST2TESTS_REDIS_PORT) \
		    pytest -rx --verbose \
		    $$component/tests/unit || ((failed+=1)); \
		echo "-----------------------------------------------------------"; \
		echo "Done running tests in" $$component; \
		echo "==========================================================="; \
	done; \
	echo pytest runs failed=$$failed; \
	if [ $$failed -gt 0 ]; then exit 1; fi

.PHONY: .run-unit-tests-coverage
ifdef INCLUDE_TESTS_IN_COVERAGE
.run-unit-tests-coverage: PYTEST_COVERAGE_PACKAGES := $(PYTEST_COVERAGE_PACKAGES),tests.unit
endif
.run-unit-tests-coverage:
	@echo
	@echo "==================== unit tests with coverage  ===================="
	@echo
	@echo "----- Dropping st2-test db -----"
	@mongosh st2-test --eval "db.dropDatabase();"
	failed=0; \
	for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "-----------------------------------------------------------"; \
		. $(VIRTUALENV_DIR)/bin/activate; \
		 ST2TESTS_REDIS_HOST=$(ST2TESTS_REDIS_HOST) \
		 ST2TESTS_REDIS_PORT=$(ST2TESTS_REDIS_PORT) \
		    COVERAGE_FILE=.coverage.unit.$$(echo $$component | tr '/' '.') \
		    pytest --verbose $(PYTEST_OPTS) --cov=$$component --cov-branch \
		    $$component/tests/unit || ((failed+=1)); \
		echo "-----------------------------------------------------------"; \
		echo "Done running tests in" $$component; \
		echo "==========================================================="; \
	done; \
	echo pytest runs failed=$$failed; \
	if [ $$failed -gt 0 ]; then exit 1; fi

.PHONY: .combine-unit-tests-coverage
.combine-unit-tests-coverage: .run-unit-tests-coverage
	@if [ -n "$(PYTEST_COVERAGE_FLAGS)" ]; then \
	    . $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.unit \
	        coverage combine .coverage.unit.*; \
	fi

.coverage.unit:
	@if compgen -G '.coverage.unit.*'; then \
		for coverage_result in $$(compgen -G '.coverage.unit.*'); do \
			echo "Combining data from $${coverage_result}"; \
			. $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.unit \
			coverage combine $${coverage_result}; \
		done; \
	else \
		echo "Running unit tests"; \
		make .combine-unit-tests-coverage; \
	fi

.PHONY: .report-unit-tests-coverage
.report-unit-tests-coverage: .coverage.unit
	@if [ -n "$(PYTEST_COVERAGE_FLAGS)" ]; then \
	    . $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.unit \
	        coverage report; \
	fi

.PHONY: .unit-tests-coverage-html
.unit-tests-coverage-html: .coverage.unit
	@if [ -n "$(PYTEST_COVERAGE_FLAGS)" ]; then \
	    . $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.unit \
	        coverage html; \
	fi

.PHONY: itests
itests: requirements .itests

.PHONY: .itests
.itests:
	@echo
	@echo "==================== integration tests ===================="
	@echo
	@echo "----- Dropping st2-test db -----"
	@mongosh st2-test --eval "db.dropDatabase();"
	@failed=0; \
	for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running integration tests in" $$component; \
		echo "-----------------------------------------------------------"; \
		. $(VIRTUALENV_DIR)/bin/activate; \
		    pytest --capture=no --verbose $(PYTEST_OPTS) \
		    $$component/tests/integration || ((failed+=1)); \
		echo "-----------------------------------------------------------"; \
		echo "Done running integration tests in" $$component; \
		echo "==========================================================="; \
	done; \
	echo pytest runs failed=$$failed; \
	if [ $$failed -gt 0 ]; then exit 1; fi

.PHONY: .run-integration-tests-coverage
ifdef INCLUDE_TESTS_IN_COVERAGE
.run-integration-tests-coverage: PYTEST_COVERAGE_PACKAGES := $(PYTEST_COVERAGE_PACKAGES),tests.integration
endif
.run-integration-tests-coverage:
	@echo
	@echo "================ integration tests with coverage ================"
	@echo
	@echo "----- Dropping st2-test db -----"
	@mongosh st2-test --eval "db.dropDatabase();"
	@failed=0; \
	for component in $(COMPONENTS_TEST); do\
		echo "==========================================================="; \
		echo "Running integration tests in" $$component; \
		echo "-----------------------------------------------------------"; \
		. $(VIRTUALENV_DIR)/bin/activate; \
		    COVERAGE_FILE=.coverage.integration.$$(echo $$component | tr '/' '.') \
		    pytest --capture=no --verbose $(PYTEST_OPTS) --cov=$$component --cov-branch \
		    $$component/tests/integration || ((failed+=1)); \
		echo "-----------------------------------------------------------"; \
		echo "Done integration running tests in" $$component; \
		echo "==========================================================="; \
	done; \
	echo pytest runs failed=$$failed; \
	if [ $$failed -gt 0 ]; then exit 1; fi
	# NOTE: If you also want to run orquesta tests which seem to have a bunch of race conditions, use
	# ci-integration-full target
#	@echo
#	@echo "==================== Orquesta integration tests with coverage (HTML reports) ===================="
#	@echo "The tests assume st2 is running on 127.0.0.1."
#	@echo
#	. $(VIRTUALENV_DIR)/bin/activate; \
@#		COVERAGE_FILE=.coverage.integration.orquesta \
@#		pytest --capture=no --verbose $(PYTEST_OPTS) \
@#		$(PYTEST_COVERAGE_FLAGS) $(PYTEST_COVERAGE_PACKAGES) st2tests/integration/orquesta || exit 1; \

.PHONY: .combine-integration-tests-coverage
.combine-integration-tests-coverage: .run-integration-tests-coverage
	@if [ -n "$(PYTEST_COVERAGE_FLAGS)" ]; then \
	    . $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.integration \
	        coverage combine .coverage.integration.*; \
	fi

.coverage.integration:
	@if compgen -G '.coverage.integration.*'; then \
		for coverage_result in $$(compgen -G '.coverage.integration.*'); do \
			echo "Combining data from $${coverage_result}"; \
			. $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.integration \
			coverage combine $${coverage_result}; \
		done; \
	else \
		echo "Running integration tests"; \
		make .combine-integration-tests-coverage; \
	fi

.PHONY: .report-integration-tests-coverage
.report-integration-tests-coverage: .coverage.integration
	@if [ -n "$(PYTEST_COVERAGE_FLAGS)" ]; then \
	    . $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.integration \
	        coverage report; \
	fi

.PHONY: .integration-tests-coverage-html
.integration-tests-coverage-html: .coverage.integration
	@if [ -n "$(PYTEST_COVERAGE_FLAGS)" ]; then \
	    . $(VIRTUALENV_DIR)/bin/activate; COVERAGE_FILE=.coverage.integration \
	        coverage html; \
	fi

.PHONY: .itests-coverage-html
.itests-coverage-html: .integration-tests-coverage-html

.PHONY: .coverage-combine
.coverage-combine: .run-unit-tests-coverage .run-integration-tests-coverage
	. $(VIRTUALENV_DIR)/bin/activate; coverage combine $(COVERAGE_GLOBS)

# This is a real target, but we need to do our own make trickery in case some
# but not all of the prerequisites are available
.coverage:
	@NUM_COVERAGE_RESULTS=0; \
	for coverage_result in $$( \
		for coverage_glob in $(COVERAGE_GLOBS_QUOTED); do \
			compgen -G $${coverage_glob}; \
		done; \
	); do \
		NUM_COVERAGE_RESULTS=$$(( NUM_COVERAGE_RESULTS+1 )); \
		echo "Combining $${coverage_result}: $$NUM_COVERAGE_RESULTS"; \
		. $(VIRTUALENV_DIR)/bin/activate; coverage combine $${coverage_result}; \
	done; \
	if [ $${NUM_COVERAGE_RESULTS} -eq 0 ]; then \
		make .coverage-combine; \
	fi

# @for coverage_result in $(COVERAGE_GLOBS); do \
# 	[ -e $${coverage_result} ] || echo "$${coverage_result} does not exist." && continue; \
# 	echo "Combining data from $${coverage_result}"; \
# 	. $(VIRTUALENV_DIR)/bin/activate; coverage combine $${coverage_result}; \
# done || \
# (echo "Running .coverage-combine"; make .coverage-combine)

.PHONY: .coverage-report
.coverage-report: .coverage
	. $(VIRTUALENV_DIR)/bin/activate; coverage report

.PHONY: .coverage-html
.coverage-html: .coverage
	. $(VIRTUALENV_DIR)/bin/activate; coverage html

.PHONY: orquesta-itests
orquesta-itests: requirements .orquesta-itests

.PHONY: .orquesta-itests
.orquesta-itests:
	@echo
	@echo "==================== Orquesta integration tests ===================="
	@echo "The tests assume st2 is running on 127.0.0.1."
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; pytest --capture=no --verbose $(PYTEST_OPTS) st2tests/integration/orquesta || exit 1;

.PHONY: .orquesta-itests-coverage-html
.orquesta-itests-coverage-html:
	@echo
	@echo "==================== Orquesta integration tests with coverage (HTML reports) ===================="
	@echo "The tests assume st2 is running on 127.0.0.1."
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; pytest --capture=no --verbose $(PYTEST_OPTS) --cov=orquesta --cov-branch  st2tests/integration/orquesta || exit 1;

.PHONY: packs-tests
packs-tests: requirements .packs-tests

.PHONY: .packs-tests
.packs-tests:
	@echo
	@echo "==================== packs-tests ===================="
	@echo
	# Install st2common to register metrics drivers
	(cd ${ROOT_DIR}/st2common; ${ROOT_DIR}/$(VIRTUALENV_DIR)/bin/python setup.py develop --no-deps)
	. $(VIRTUALENV_DIR)/bin/activate; find ${ROOT_DIR}/contrib/* -maxdepth 0 -type d -print0 | xargs -0 -I FILENAME ./st2common/bin/st2-run-pack-tests -c -t -x -p FILENAME


.PHONY: runners-tests
runners-tests: requirements .runners-tests

.PHONY: .runners-tests
.runners-tests:
	@echo
	@echo "==================== runners-tests ===================="
	@echo
	@echo "----- Dropping st2-test db -----"
	@mongosh st2-test --eval "db.dropDatabase();"
	@failed=0; \
	for component in $(COMPONENTS_RUNNERS); do\
		echo "==========================================================="; \
		echo "Running tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; pytest --capture=no --verbose $(PYTEST_OPTS) $$component/tests/unit || ((failed+=1)); \
	done; \
	if [ $$failed -gt 0 ]; then exit 1; fi

.PHONY: runners-itests
runners-itests: requirements .runners-itests

.PHONY: .runners-itests
.runners-itests:
	@echo
	@echo "==================== runners-itests ===================="
	@echo
	@echo "----- Dropping st2-test db -----"
	@failed=0; \
	for component in $(COMPONENTS_RUNNERS); do\
		echo "==========================================================="; \
		echo "Running integration tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; pytest --capture=no --verbose $(PYTEST_OPTS) $$component/tests/integration || ((failed+=1)); \
	done; \
	echo pytest runs failed=$$failed; \
	if [ $$failed -gt 0 ]; then exit 1; fi

.PHONY: .runners-itests-coverage-html
.runners-itests-coverage-html:
	@echo
	@echo "============== runners-itests-coverage-html =============="
	@echo
	@echo "The tests assume st2 is running on 127.0.0.1."
	@failed=0; \
	for component in $(COMPONENTS_RUNNERS); do\
		echo "==========================================================="; \
		echo "Running integration tests in" $$component; \
		echo "==========================================================="; \
		. $(VIRTUALENV_DIR)/bin/activate; pytest --capture=no --verbose $(PYTEST_OPTS) \
			--cov=$$component --cov-report=html $$component/tests/integration || ((failed+=1)); \
	done; \
	echo pytest runs failed=$$failed; \
	if [ $$failed -gt 0 ]; then exit 1; fi

.PHONY: cli
cli:
	@echo
	@echo "=================== Building st2 client ==================="
	@echo
	pushd $(CURDIR) && cd st2client && ((python setup.py develop || printf "\n\n!!! ERROR: BUILD FAILED !!!\n") || popd)

.PHONY: rpms
rpms:
	@echo
	@echo "==================== rpm ===================="
	@echo
	rm -Rf ~/rpmbuild
	$(foreach COM,$(COMPONENTS), pushd $(COM); make rpm; popd;)
	pushd st2client && make rpm && popd

.PHONY: debs
debs:
	@echo
	@echo "==================== deb ===================="
	@echo
	rm -Rf ~/debbuild
	$(foreach COM,$(COMPONENTS), pushd $(COM); make deb; popd;)
	pushd st2client && make deb && popd


.PHONY: ci
ci: ci-checks ci-unit ci-integration ci-packs-tests

# NOTE: pylint is moved to ci-compile so we more evenly spread the load across
# various different jobs to make the whole workflow complete faster
.PHONY: ci-checks
ci-checks: .generated-files-check .shellcheck .black-check .pre-commit-checks .flake8 check-requirements check-sdist-requirements .st2client-dependencies-check .st2common-circular-dependencies-check circle-lint-api-spec .rst-check .st2client-install-check check-python-packages .st2client-pypi-check

.PHONY: .rst-check
.rst-check:
	@echo
	@echo "==================== rst-check ===================="
	@echo
	. $(VIRTUALENV_DIR)/bin/activate; rstcheck --report-level WARNING CHANGELOG.rst

.PHONY: .generated-files-check
.generated-files-check:
	# Verify that all the files which are automatically generated have indeed been re-generated and
	# committed
	@echo "==================== generated-files-check ===================="

	# 1. Sample config - conf/st2.conf.sample
	cp conf/st2.conf.sample /tmp/st2.conf.sample.upstream
	make .configgen
	diff conf/st2.conf.sample /tmp/st2.conf.sample.upstream || (echo "conf/st2.conf.sample hasn't been re-generated and committed. Please run \"make configgen\" and include and commit the generated file." && exit 1)
	# 2. OpenAPI definition file - st2common/st2common/openapi.yaml (generated from
	# st2common/st2common/openapi.yaml.j2)
	cp st2common/st2common/openapi.yaml /tmp/openapi.yaml.upstream
	make .generate-api-spec
	diff st2common/st2common/openapi.yaml  /tmp/openapi.yaml.upstream || (echo "st2common/st2common/openapi.yaml hasn't been re-generated and committed. Please run \"make generate-api-spec\" and include and commit the generated file." && exit 1)
	# 3. Schemas for the content models - st2common/bin/st2-generate-schemas
	cp contrib/schemas/pack.json /tmp/pack.json.upstream
	cp contrib/schemas/action.json /tmp/action.json.upstream
	cp contrib/schemas/alias.json /tmp/alias.json.upstream
	cp contrib/schemas/policy.json /tmp/policy.json.upstream
	cp contrib/schemas/rule.json /tmp/rule.json.upstream
	make .schemasgen
	diff contrib/schemas/pack.json /tmp/pack.json.upstream || (echo "contrib/schemas/pack.json hasn't been re-generated and committed. Please run \"make schemasgen\" and include and commit the generated file." && exit 1)
	diff contrib/schemas/action.json /tmp/action.json.upstream || (echo "contrib/schemas/pack.json hasn't been re-generated and committed. Please run \"make schemasgen\" and include and commit the generated file." && exit 1)
	diff contrib/schemas/alias.json /tmp/alias.json.upstream || (echo "contrib/schemas/pack.json hasn't been re-generated and committed. Please run \"make schemasgen\" and include and commit the generated file." && exit 1)
	diff contrib/schemas/policy.json /tmp/policy.json.upstream || (echo "contrib/schemas/pack.json hasn't been re-generated and committed. Please run \"make schemasgen\" and include and commit the generated file." && exit 1)
	diff contrib/schemas/rule.json /tmp/rule.json.upstream || (echo "contrib/schemas/pack.json hasn't been re-generated and committed. Please run \"make schemasgen\" and include and commit the generated file." && exit 1)
	@echo "All automatically generated files are up to date."

.PHONY: ci-unit
ci-unit: .unit-tests-coverage-html

.PHONY: .ci-prepare-integration
.ci-prepare-integration:
	@echo
	@echo "==================== prepare integration ===================="
	@echo
	sudo -E ./scripts/github/prepare-integration.sh

.PHONY: ci-integration-full
ci-integration-full: .ci-prepare-integration .itests-coverage-html  .orquesta-itests-coverage-html

# All integration tests minus orquesta ones
.PHONY: ci-integration
ci-integration: .ci-prepare-integration .itests-coverage-html

.PHONY: ci-runners
ci-runners: .ci-prepare-integration .runners-itests-coverage-html

.PHONY: ci-orquesta
ci-orquesta: .ci-prepare-integration .orquesta-itests-coverage-html

.PHONY: ci-packs-tests
ci-packs-tests: .packs-tests

.PHONY: ci-compile
ci-compile: check-dependency-conflicts compilepy3 .pylint
