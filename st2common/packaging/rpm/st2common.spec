Summary: Stanley Common Libraries
Name: st2common
Version: 0.4.0
Release: 1
License: Apache
Group: Applications/Engineering
BuildArch: noarch
Source: /opt/git/stanley/st2common.tar.gz
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
sed -i -r "s~(st2.*)/conf~/etc/\1~g" stanley/stanley.conf
sed -i -r "s~logs~/var/log/stanley~g" conf/logging.conf
sed -i "/modules_path/a system_path = %{python2_sitelib}/st2reactor/contrib/sensors" stanley/stanley.conf
sed -i "s/vagrant/stanley/g" stanley/stanley.conf

%install

mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/var/log/stanley
mkdir -p %{buildroot}/etc/stanley
mkdir -p %{buildroot}/etc/st2common
mkdir -p %{buildroot}/opt/stackstorm
cp -R bin st2common/
cp -R contrib/core/rules %{buildroot}/opt/stackstorm/
cp -R contrib/core/sensors %{buildroot}/opt/stackstorm/
cp -R contrib/core/actions %{buildroot}/opt/stackstorm/
cp -R external/mirantis %{buildroot}%{python2_sitelib}/
cp -R st2common %{buildroot}/%{python2_sitelib}/
install stanley/stanley.conf %{buildroot}/etc/stanley/stanley.conf
install conf/logging.conf %{buildroot}/etc/st2common/logging.conf


%files
%{python2_sitelib}/st2common*
%{python2_sitelib}/mirantis*
/etc/st2common/*
/etc/stanley/*
/opt/stackstorm/*
