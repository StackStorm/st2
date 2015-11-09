# <<<< TO DEPRICATE
SHELL := /bin/bash
PY27 := /usr/bin/python2.7
RPM_ROOT=~/rpmbuild
RPM_SOURCES_DIR := $(RPM_ROOT)/SOURCES/
RPM_SPECS_DIR := $(RPM_ROOT)/SPECS/
VER := $(shell cat ./st2client/__init__.py | grep -Po "__version__ = '\K[^']*")
RELEASE=1
COMPONENTS := st2client

.PHONY: rpm
rpm: 
	$(PY27) setup.py bdist_rpm --python=$(PY27)
	mkdir -p $(RPM_ROOT)/RPMS/noarch
	cp dist/$(COMPONENTS)*noarch.rpm $(RPM_ROOT)/RPMS/noarch/$(COMPONENTS)-$(VER)-$(RELEASE).noarch.rpm
	mkdir -p $(RPM_ROOT)/SRPMS
	cp dist/*src.rpm $(RPM_ROOT)/SRPMS/$(COMPONENTS)-$(VER)-$(RELEASE).src.rpm
	rm -Rf dist $(COMPONENTS).egg-info ChangeLog AUTHORS build

.PHONY: rhel-rpm
rhel-rpm:
	$(PY27) setup.py bdist_rpm --python=$(PY27)
	mkdir -p $(RPM_ROOT)/RPMS/noarch
	cp dist/$(COMPONENTS)*noarch.rpm $(RPM_ROOT)/RPMS/noarch/$(COMPONENTS)-$(VER)-$(RELEASE).noarch.rpm
	mkdir -p $(RPM_ROOT)/SRPMS
	cp dist/*src.rpm $(RPM_ROOT)/SRPMS/$(COMPONENTS)-$(VER)-$(RELEASE).src.rpm
	rm -Rf dist $(COMPONENTS).egg-info ChangeLog AUTHORS build

.PHONY: deb
deb:
	$(PY27) setup.py --command-packages=stdeb.command bdist_deb
	mkdir -p ~/debbuild
	cp deb_dist/python-$(COMPONENTS)*-1_all.deb ~/debbuild/$(COMPONENTS)_$(VER)-$(RELEASE)_amd64.deb
	rm -Rf dist deb_dist $(COMPONENTS)-$(VER).tar.gz $(COMPONENTS).egg-info ChangeLog AUTHORS build
# >>>>

WHEELDIR ?= /tmp/wheelhouse
ST2_COMPONENT := $(notdir $(CURDIR))
ST2PKG_RELEASE ?= 1
ST2PKG_VERSION ?= $(shell python -c "from $(ST2_COMPONENT) import __version__; print __version__,")

ifneq (,$(wildcard /etc/debian_version))
	DEBIAN := 1
	DESTDIR ?= $(CURDIR)/debian/$(ST2_COMPONENT)
else
	REDHAT := 1
endif

.PHONY: all install wheelhouse
all: install

install: wheelhouse injectdeps changelog

post_install: bdist_wheel

populate_version: .stamp-populate_version
.stamp-populate_version:
	# populate version should be run before any pip/setup.py works
	sh ../scripts/populate-version.sh
	touch $@

requirements:
	python ../scripts/fixate-requirements.py -s in-requirements.txt -f ../fixed-requirements.txt

changelog: populate_version
ifeq ($(DEBIAN),1)
	debchange -v $(ST2PKG_VERSION)-$(ST2PKG_RELEASE) -M "automated build version: $(ST2PKG_VERSION)"
endif

wheelhouse: .stamp-wheelhouse
.stamp-wheelhouse: populate_version requirements
	# Install wheels into shared location
	pip wheel --wheel-dir=$(WHEELDIR) -r requirements.txt
	touch $@

injectdeps: .stamp-injectdeps
.stamp-injectdeps:
	# We can modify requirements ONLY AFTER wheelhouse has been built
	@echo "st2common" >> requirements.txt
	touch $@

bdist_wheel: .stamp-bdist_wheel
.stamp-bdist_wheel: populate_version
	python setup.py bdist_wheel -d $(WHEELDIR)
	touch $@