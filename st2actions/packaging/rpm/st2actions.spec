Summary: Stanley Actions
Name: st2actions
Version: 0.4.0
Release: 1
License: Apache
Group: Applications/Engineering
BuildArch: noarch
Source: /opt/git/stanley/st2actions.tar.gz
URL: https://github.com/StackStorm/stanley
Vendor: StackStorm
Packager: Stormin Stanley <stanley@stackstorm.com>
Requires:     st2common

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%build
sed -i -r "s~logs~/var/log/stanley~g" conf/logging*.conf

%install

mkdir -p %{buildroot}/etc/st2actions
mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/usr/bin
cp -R st2actions %{buildroot}%{python2_sitelib}/
cp -R conf/* %{buildroot}/etc/st2actions
install -m755 bin/actionrunner %{buildroot}/usr/bin/actionrunner

%files

/usr/lib/python2.7/site-packages/st2actions*
/usr/bin/actionrunner
/etc/st2actions*
