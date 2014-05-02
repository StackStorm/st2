TOX_DIR := .tox
#VIRTUALENV_DIR := $(TOX_DIR)/py27
VIRTUALENV_DIR := virtualenv

BINARIES := bin

# Components are all directories that start with "st2"
COMPONENTS := $(wildcard st2*)
EXTERNAL_DIR := external

# nasty hack to get a space into a variable
space_char :=
space_char +=
COMPONENT_PYTHONPATH = $(subst $(space_char),:,$(realpath $(COMPONENTS)))

PYTHON_TARGET := 2.7
REQUIREMENTS := requirements.txt test-requirements.txt

.PHONY: all
all: virtualenv

distclean:
	rm -rf $(VIRTUALENV_DIR)

virtualenv: $(VIRTUALENV_DIR)/bin/activate
$(VIRTUALENV_DIR)/bin/activate: requirements.txt test-requirements.txt
	@echo ""
	@echo "Creating python virtual environment"
	@echo
	test -d $(VIRTUALENV_DIR) || virtualenv --no-site-packages $(VIRTUALENV_DIR)

	# Setup PYTHONPATH in bash activate script...
	echo '' >> $(VIRTUALENV_DIR)/bin/activate
	echo '_OLD_PYTHONPATH=$$PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'PYTHONPATH=$$_OLD_PYTHONPATH:$(COMPONENT_PYTHONPATH):$(EXTERNAL_DIR)' >> $(VIRTUALENV_DIR)/bin/activate
	echo 'export PYTHONPATH' >> $(VIRTUALENV_DIR)/bin/activate
	. $(VIRTUALENV_DIR)/bin/activate ; pip install -U $(foreach req,$(REQUIREMENTS),-r $(req))
	touch $(VIRTUALENV_DIR)/bin/activate

