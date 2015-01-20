SHELL := /bin/bash
REPO_ROOT := ..
VIRTUALENV_DIR=virtualenv
RPM_ROOT=~/rpmbuild
RPM_SOURCES_DIR := $(RPM_ROOT)/SOURCES/
RPM_SPECS_DIR := $(RPM_ROOT)/SPECS/
COMPONENTS := st2auth
VER=0.4.0
PEP8_CONFIG := $(REPO_ROOT)/.pep8
FLAKE8_CONFIG := $(REPO_ROOT)/.flake8

.PHONY: clean
clean:
	rm -rf *.egg-info
	rm -rf build
	find . -name \*.pyc -type f -delete
	find . -name \*.pyo -type f -delete

.PHONY: test
test:
	. ../$(VIRTUALENV_DIR)/bin/activate; PECAN_CONFIG=tests/config.py python setup.py test -q

.PHONY: pep8
pep8:
	pep8 --config $(PEP8_CONFIG) $(COMPONENTS)

.PHONY: flake8
flake8:
	flake8 --config $(FLAKE8_CONFIG) $(COMPONENTS)

.PHONY: rpm
rpm:
	pushd ~ && rpmdev-setuptree && popd
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ -czf $(RPM_SOURCES_DIR)/$(COMPONENTS).tar.gz bin conf $(COMPONENTS)
	cp packaging/rpm/$(COMPONENTS).spec $(RPM_SPECS_DIR)/
	cd $(RPM_SPECS_DIR) && rpmbuild --clean --rmsource -ba $(COMPONENTS).spec

.PHONY: rhel-rpm
rhel-rpm:
	pushd ~ && rpmdev-setuptree && popd
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ -czf $(RPM_SOURCES_DIR)/$(COMPONENTS).tar.gz bin conf $(COMPONENTS)
	cp packaging/rpm/$(COMPONENTS)-rhel6.spec $(RPM_SPECS_DIR)/
	cd $(RPM_SPECS_DIR) && rpmbuild --clean --rmsource -ba $(COMPONENTS)-rhel6.spec

.PHONY: deb
deb:
	mkdir -p ~/debbuild
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ -czf ~/$(COMPONENTS).tar.gz bin conf $(COMPONENTS) packaging/debian
	pushd ~ && tar -xzf $(COMPONENTS).tar.gz && cd $(COMPONENTS)-$(VER) && cp -Rf packaging/debian ./ && dpkg-buildpackage -us -uc -b && popd
	cp -f ~/$(COMPONENT)*.deb ~/debbuild/
