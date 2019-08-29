ROOT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
OS := $(shell uname)

# We separate the OSX X and Linux virtualenvs so we can run in a Docker
# container (st2devbox) while doing things on our host Mac machine
ifeq ($(OS),Darwin)
	VIRTUALENV_DIR ?= virtualenv-osx
else
	VIRTUALENV_DIR ?= virtualenv
endif

PYTHON_VERSION ?= python2.7

COMPONENTS := $(shell ls -a | grep ^st2 | grep -v .egg-info)
COMPONENTS_RUNNERS := $(wildcard contrib/runners/*)
COMPONENTS_WITH_RUNNERS := $(COMPONENTS) $(COMPONENTS_RUNNERS)

space_char :=
space_char +=
COMPONENT_PYTHONPATH = $(subst $(space_char),:,$(realpath $(COMPONENTS_WITH_RUNNERS)))

.PHONY: all
all: invoke
	@$(VIRTUALENV_DIR)/bin/invoke all

.PHONY: clean
clean:
	@echo "Removing all .pyc files"
	find . -name \*.pyc -type f -print0 | xargs -0 -I {} rm {}

.PHONY: distclean
distclean: clean
	@echo
	@echo "==================== distclean ===================="
	@echo
	rm -rf $(VIRTUALENV_DIR)
	if [ -d virtualenv-st2client ]; then rm -rf virtualenv-st2client; fi
	if [ -d virtualenv-components ]; then rm -rf virtualenv-components; fi

# Optional virtualenv wrapper
ifneq ($(VIRTUALENV_DIR),virtualenv)
.PHONY: virtualenv
virtualenv: $(VIRTUALENV_DIR)
endif

.PHONY: $(VIRTUALENV_DIR)
	# Note: We always want to update virtualenv/bin/activate file to make sure
	# PYTHONPATH is up to date and to avoid caching issues on Travis
$(VIRTUALENV_DIR):
	# Note: We pass --no-download flag to make sure version of pip which we install (9.0.1) is used
	# instead of latest version being downloaded from PyPi
	test -f $(VIRTUALENV_DIR)/bin/activate || virtualenv --python=$(PYTHON_VERSION) --no-site-packages $(VIRTUALENV_DIR) --no-download

	@echo
	@echo "==================== requirements ===================="
	@echo
	# Make sure we use latest version of pip which is 19
	$(VIRTUALENV_DIR)/bin/pip --version
	$(VIRTUALENV_DIR)/bin/pip install --upgrade "pip>=19.0,<20.0"
	$(VIRTUALENV_DIR)/bin/pip install --upgrade "virtualenv==16.6.0" # Required for packs.install in dev envs

	# Setup PYTHONPATH in bash activate script...
	# Delete existing entries (if any)
ifeq ($(OS),Darwin)
	echo 'Setting up virtualenv on $(OS)...'
	sed -i '' '/_OLD_PYTHONPATH/d' $(VIRTUALENV_DIR)/bin/activate
	sed -i '' '/PYTHONPATH=/d' $(VIRTUALENV_DIR)/bin/activate
	sed -i '' '/export PYTHONPATH/d' $(VIRTUALENV_DIR)/bin/activate
else
	echo 'Setting up virtualenv on $(OS)...'
	sed -i '/_OLD_PYTHONPATH/d' $(VIRTUALENV_DIR)/bin/activate
	sed -i '/PYTHONPATH=/d' $(VIRTUALENV_DIR)/bin/activate
	sed -i '/export PYTHONPATH/d' $(VIRTUALENV_DIR)/bin/activate
endif

	echo '_OLD_PYTHONPATH=$$PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	#echo 'PYTHONPATH=$$_OLD_PYTHONPATH:$(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'PYTHONPATH=${ROOT_DIR}:$(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'export PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	touch $(VIRTUALENV_DIR)/bin/activate

virtualenv-components:
	virtualenv --python=$(PYTHON_VERSION) --no-site-packages $@ --no-download

virtualenv-st2client:
	virtualenv --python=$(PYTHON_VERSION) --no-site-packages $@ --no-download

$(VIRTUALENV_DIR)/bin/invoke: $(VIRTUALENV_DIR)
	. $(VIRTUALENV_DIR)/bin/activate && pip install invoke

.PHONY: invoke
invoke: $(VIRTUALENV_DIR)/bin/invoke

# https://stackoverflow.com/a/33018558
# Workaround to support all previous make targets
# This default target simply passes all targets on to invoke
# We can't add invoke as a make dependency for the .DEFAULT target since the
# dependency will get overridden by whatever target is passed in
.DEFAULT:
	@# Manually make virtualenv target
	if [ ! -d $(VIRTUALENV_DIR) ]; then make virtualenv; fi
	@# Manually make invoke target
	if [ ! -e $(VIRTUALENV_DIR)/bin/invoke ]; then make invoke; fi
	. $(VIRTUALENV_DIR)/bin/activate && invoke $@
	@#. $(VIRTUALENV_DIR)/bin/activate && echo $$PYTHONPATH
