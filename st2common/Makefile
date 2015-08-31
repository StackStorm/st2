# <<<< TO DEPRICATE
SHELL := /bin/bash
RPM_ROOT=~/rpmbuild
RPM_SOURCES_DIR := $(RPM_ROOT)/SOURCES/
RPM_SPECS_DIR := $(RPM_ROOT)/SPECS/
VER=0.4.0

COMPONENTS := st2common

.PHONY: rpm
rpm:
	pushd ~ && rpmdev-setuptree && popd
	mkdir -p st2 && cp -f ../conf/st2.prod.conf st2/st2.conf
	mkdir -p logrotate.d && cp -f ../conf/logrotate.conf logrotate.d/st2.conf
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ --exclude=correlation -czf $(RPM_SOURCES_DIR)/$(COMPONENTS).tar.gz bin st2 logrotate.d $(COMPONENTS) ../contrib ../docs ../tools/ ../requirements.txt
	cp packaging/rpm/$(COMPONENTS).spec $(RPM_SPECS_DIR)/
	cd $(RPM_SPECS_DIR) && rpmbuild --clean --rmsource -ba $(COMPONENTS).spec

.PHONY: rhel-rpm
rhel-rpm:
	pushd ~ && rpmdev-setuptree && popd
	mkdir -p st2 && cp -f ../conf/st2.prod.conf st2/st2.conf
	mkdir -p logrotate.d && cp -f ../conf/logrotate.conf logrotate.d/st2.conf
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ --exclude=correlation -czf $(RPM_SOURCES_DIR)/$(COMPONENTS).tar.gz bin st2 logrotate.d $(COMPONENTS) ../contrib ../docs ../tools/ ../requirements.txt
	cp packaging/rpm/$(COMPONENTS)-rhel6.spec $(RPM_SPECS_DIR)/
	cd $(RPM_SPECS_DIR) && rpmbuild --clean --rmsource -ba $(COMPONENTS)-rhel6.spec

.PHONY: deb
deb:
	mkdir -p ~/debbuild
	mkdir -p st2 && cp -f ../conf/st2.prod.conf st2/st2.conf
	mkdir -p logrotate.d && cp -f ../conf/logrotate.conf logrotate.d/st2.conf
	tar --transform=s~^~$(COMPONENTS)-$(VER)/~ --exclude=correlation -czf ~/$(COMPONENTS).tar.gz bin st2 logrotate.d $(COMPONENTS) ../contrib ../docs ../tools/ ../requirements.txt packaging/debian
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

install: wheelhouse changelog pre_install

post_install: bdist_wheel

pre_install:
	# Write temp files which will be processed by debhelpers
	install -D -m644 ../conf/st2.package.conf $(DESTDIR)/etc/st2/st2.conf
	install -D -m644 ../conf/logrotate.conf $(DESTDIR)/etc/logrotate.d/st2

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
	touch $@

bdist_wheel: .stamp-bdist_wheel
.stamp-bdist_wheel: populate_version
	# All other components depend on st2common, so we create st2common
	# in the shared WHEELHOUSE directory.
	python setup.py bdist_wheel -d $(WHEELDIR)
	touch $@
