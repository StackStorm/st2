Summary: ST2 Common Libraries
Name: st2common
Version: 0.4.0
Release: 1
License: Apache
Group: Applications/Engineering
BuildArch: noarch
Source: /opt/git/st2/st2common.tar.gz
URL: https://github.com/StackStorm/st2
Vendor: StackStorm
Packager: Estee Tew <st2@stackstorm.com>
Requires:	python-devel
Requires:   	python-pip
Requires:     mongodb
Requires:     mongodb-server

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%build
sed -i -r "s~(st2.*)/conf~/etc/\1~g" st2/st2.conf
sed -i "s~vagrant~/home/stanley~g" st2/st2.conf

%install

mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/var/log/st2
mkdir -p %{buildroot}/etc/st2
mkdir -p %{buildroot}/opt/stackstorm/packs
mkdir -p %{buildroot}/usr/share/doc/st2
cp -R contrib/core %{buildroot}/opt/stackstorm/packs/
cp -R contrib/packs %{buildroot}/opt/stackstorm/packs/
cp -R contrib/examples %{buildroot}/usr/share/doc/st2/
cp -R docs/* %{buildroot}/usr/share/doc/st2/
cp -R st2common %{buildroot}/%{python2_sitelib}/
cp -R bin %{buildroot}/%{python2_sitelib}/st2common/
install st2/st2.conf %{buildroot}/etc/st2/st2.conf
install -m755 tools/st2ctl %{buildroot}/usr/bin/st2ctl

%files
%{python2_sitelib}/st2common*
/usr/share/doc/st2/*
/etc/st2/*
/opt/stackstorm/*
/var/log/st2
/usr/bin/st2ctl
