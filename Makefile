TOX_DIR := .tox
#VIRTUALENV_DIR := $(TOX_DIR)/py27
VIRTUALENV_DIR := virtualenv

BINARIES := bin

# All components are prefixed by st2
COMPONENTS := $(wildcard st2*)

# Components that implement a component-controlled test-runner. These components provide an
# in-component Makefile. (Temporary fix until I can generalize the pecan unittest setup. -mar)
COMPONENT_SPECIFIC_TESTS := st2actioncontroller st2reactorcontroller

EXTERNAL_DIR := external

# nasty hack to get a space into a variable
space_char :=
space_char +=
COMPONENT_PYTHONPATH = $(subst $(space_char),:,$(realpath $(COMPONENTS) $(EXTERNAL_DIR)))
COMPONENTS_TEST := $(foreach component,$(filter-out $(COMPONENT_SPECIFIC_TESTS),$(COMPONENTS)),$(component)/tests)

PYTHON_TARGET := 2.7
REQUIREMENTS := requirements.txt test-requirements.txt

.PHONY: all
all: requirements tests

# Target for debugging Makefile variable assembly
.PHONY: play
play:
	echo $(COMPONENTS_TEST)

.PHONY: distclean
distclean:
	rm -rf $(VIRTUALENV_DIR)

.PHONY: requirements
requirements: virtualenv requirements.txt test-requirements.txt
	. $(VIRTUALENV_DIR)/bin/activate ; pip install -U $(foreach req,$(REQUIREMENTS),-r $(req))

.PHONY: virtualenv
virtualenv: $(VIRTUALENV_DIR)/bin/activate
$(VIRTUALENV_DIR)/bin/activate:
	@echo ""
	@echo "Creating python virtual environment"
	@echo
	test -d $(VIRTUALENV_DIR) || virtualenv --no-site-packages $(VIRTUALENV_DIR)

	# Setup PYTHONPATH in bash activate script...
	echo '' >> $(VIRTUALENV_DIR)/bin/activate
	echo '_OLD_PYTHONPATH=$$PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'PYTHONPATH=$$_OLD_PYTHONPATH:$(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'export PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	touch $(VIRTUALENV_DIR)/bin/activate

	# Setup PYTHONPATH in fish activate script...
	echo '' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo 'set -gx _OLD_PYTHONPATH $$PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo 'set -gx PYTHONPATH $$_OLD_PYTHONPATH $(COMPONENT_PYTHONPATH)' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo 'functions -c deactivate old_deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo 'function deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo '  if test -n $$_OLD_PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo '    set -gx PYTHONPATH $$_OLD_PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo '    set -e _OLD_PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo '  end' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo '  old_deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo '  functions -e old_deactivate' >> $(VIRTUALENV_DIR)/bin/activate.fish
	echo 'end' >> $(VIRTUALENV_DIR)/bin/activate.fish
	touch $(VIRTUALENV_DIR)/bin/activate.fish

.PHONY: tests
tests: requirements
	. $(VIRTUALENV_DIR)/bin/activate; nosetests -v $(COMPONENTS_TEST)
