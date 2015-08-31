# <<<< TO DEPRICATE
SHELL := /bin/bash
REPO_ROOT := ..
VIRTUALENV_DIR=virtualenv
RPM_ROOT=~/rpmbuild
RPM_SOURCES_DIR := $(RPM_ROOT)/SOURCES/
RPM_SPECS_DIR := $(RPM_ROOT)/SPECS/
VER=0.4.0
COMPONENTS := st2actions
FLAKE8_CONFIG := $(REPO_ROOT)/.flake8

.PHONY: clean
clean:
	rm -rf *.egg-info
	rm -rf build
	find . -name \*.pyc -type f -delete
	find . -name \*.pyo -type f -delete

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
# >>>>

WHEELDIR ?= /tmp/wheelhouse
ST2_COMPONENT := $(notdir $(CURDIR))
ST2PKG_RELEASE ?= 1
ST2PKG_VERSION ?= 0.1.0

ifneq (,$(wildcard /etc/debian_version))
	DEBIAN := 1
	DESTDIR ?= $(CURDIR)/debian/$(ST2_COMPONENT)
else
	REDHAT := 1
endif

.PHONY: all install wheelhouse
all: install

install: wheelhouse changelog

post_install:
	# post_install is triggered debian/rules file, don't call it from install target!
	# We don't want anything like below to be postinst
	sed -i -r "/args\s*=\s*/s%logs%/var/log/st2%g" $(DESTDIR)/etc/$(ST2_COMPONENT)/logging.*conf

populate_version: .stamp-populate_version
.stamp-populate_version:
	# populate version should be run before any pip/setup.py works
	sh ../scripts/populate-version.sh
	touch $@

requirements:
	python ../scripts/fixate-requirements.py -s in-requirements.txt -f ../fixed-requirements.txt

changelog: populate_version
ifeq ($(DEBIAN),1)
	debchange -v $(ST2PKG_VERSION) -M "automated build version: $(ST2PKG_VERSION)"
endif

wheelhouse: .stamp-wheelhouse
.stamp-wheelhouse: populate_version requirements
	# Install wheels into shared location
	pip wheel --wheel-dir=$(WHEELDIR) -r requirements.txt
	# We can modify requirements ONLY AFTER wheelhouse has been built
	@echo "st2common" >> requirements.txt
	touch $@
