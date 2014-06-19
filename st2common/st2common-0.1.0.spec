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
BuildRequires:	python-devel
Requires:   	python-pip
Requires:     mongodb
Requires:     mongodb-server

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%build

%install

mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/etc/stanley
/bin/pip install --install-option="--prefix=%{buildroot}" -r requirements.txt
cp -R external/mirantis %{buildroot}%{python2_sitelib}/
cp -R st2common/st2common %{buildroot}/%{python2_sitelib}/
install conf/stanley.conf %{buildroot}/etc/stanley/stanley.conf

%files
/usr/lib/python2.7/site-packages/st2common*
/usr/lib/mirantis*
/etc/stanley/*

