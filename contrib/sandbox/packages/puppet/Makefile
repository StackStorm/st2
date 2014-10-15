ROOT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

.PHONY: all
all: lint

.PHONY: lint
lint: flake8 configs-check

.PHONY: flake8
flake8:
	find ${ROOT_DIR}/*/*.py -print0 | xargs -0 flake8

.PHONY: configs-check
configs-check:
	find ${ROOT_DIR}/*/*.json -print0 | xargs -0 -I FILENAME python -mjson.tool FILENAME
