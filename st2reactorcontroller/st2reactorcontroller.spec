Summary: Stanley Reactor Controller
Name: st2reactorcontroller
Version: 0.1.0
Release: 1
License: license
Group: Applications/Engineering
BuildArch: noarch
Source: /opt/git/stanley/st2reactorcontroller.tar.gz
URL: https://github.com/StackStorm/stanley
Vendor: StackStorm
Packager: Stormin Stanley <stanley@stackstorm.com>
Requires:     st2common

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%build
sed -i -r "s~logs~/var/log/stanley~g" conf/logging.conf

%install

mkdir -p %{buildroot}/etc/st2reactorcontroller
mkdir -p %{buildroot}%{python2_sitelib}
mkdir -p %{buildroot}/usr/bin
cp -R st2reactorcontroller %{buildroot}/%{python2_sitelib}/
cp -R conf/* %{buildroot}/etc/st2reactorcontroller
install -m755 bin/reactor_controller %{buildroot}/usr/bin/reactor_controller

%files

/usr/lib/python2.7/site-packages/st2reactorcontroller*
/usr/bin/reactor_controller
/etc/st2reactorcontroller*
