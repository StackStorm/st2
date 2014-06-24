Summary: Stanley Common Libraries
Name: st2common
Version: 0.1.0
Release: 1
License: license
Group: Applications/Engineering
Source: /opt/git/stanley/st2common-0.1.0.tar.gz
URL: https://github.com/StackStorm/stanley
Vendor: StackStorm
Packager: Stormin Stanley <stanley@stackstorm.com>
Requires:	python-devel
Requires:   	python-pip
Requires:     mongodb
Requires:     mongodb-server

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%build
sed -i -r "s~(st2.*)/conf~/etc/\1~g" conf/stanley.conf
sed -i -r "s~st2reactor/(st2reactor/sensor/samples)~/etc/\1~g" conf/stanley.conf

%install

mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/etc/stanley
#/bin/pip install --install-option="--prefix=%{buildroot}" -r requirements.txt
cp -R external/mirantis %{buildroot}%{python2_sitelib}/
cp -R st2common %{buildroot}/%{python2_sitelib}/
install conf/stanley.conf %{buildroot}/etc/stanley/stanley.conf


%files
%{python2_sitelib}/st2common*
%{python2_sitelib}/mirantis*
/etc/stanley/*

