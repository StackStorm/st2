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
sed -i "/content_packs_base_path/a system_path = %{python2_sitelib}/st2reactor/contrib/sensors" stanley/stanley.conf
sed -i "s~vagrant~/home/stanley~g" stanley/stanley.conf

%install

mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/var/log/stanley
mkdir -p %{buildroot}/etc/stanley
mkdir -p %{buildroot}/opt/stackstorm
mkdir -p %{buildroot}/usr/share/doc/stanley
rm -Rf contrib/core/correlation
cp -R contrib/core %{buildroot}/opt/stackstorm/
cp -R contrib/examples %{buildroot}/usr/share/doc/stanley/
cp -R contrib/sandbox %{buildroot}/usr/share/doc/stanley/
cp -R docs/* %{buildroot}/usr/share/doc/stanley/
cp -R st2common %{buildroot}/%{python2_sitelib}/
cp -R bin %{buildroot}/%{python2_sitelib}/st2common/
install stanley/stanley.conf %{buildroot}/etc/stanley/stanley.conf


%files
%{python2_sitelib}/st2common*
/usr/share/doc/stanley/*
/etc/stanley/*
/opt/stackstorm/*
