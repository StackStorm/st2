RPM_ROOT=~/rpmbuild
RPM_SOURCES_DIR := $(RPM_ROOT)/SOURCES/
RPM_SPECS_DIR := $(RPM_ROOT)/SPECS/
VER=0.1.0
COMPONENTS := st2client

.PHONY: rpm
rpm: 
	python setup.py bdist_rpm
	mkdir -p $(RPM_ROOT)/RPMS/noarch
	cp dist/$(COMPONENTS)-$(VER)*noarch.rpm $(RPM_ROOT)/RPMS/noarch/$(COMPONENTS)-$(VER)-1.noarch.rpm
	cp dist/*src.rpm $(RPM_ROOT)/SRPMS/$(COMPONENTS)-$(VER)-1.src.rpm
	rm -Rf dist pbr-0.8.2-py2.7.egg st2client.egg-info ChangeLog AUTHORS build
