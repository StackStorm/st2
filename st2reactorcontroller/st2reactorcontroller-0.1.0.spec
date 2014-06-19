Summary: Stanley Reactor Controller
Name: st2reactorcontroller
Version: 0.1.0
Release: 1
License: derp
Group: Applications/Engineering
Source: /opt/git/stanley/streactorcontroller-0.1.0.tar.gz
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

mkdir -p %{buildroot}/etc/st2reactorcontroller
cp -R st2reactorcontroller/st2reactorcontroller %{buildroot}/%{python2_sitelib}/
cp -R st2reactorcontroller/conf/* %{buildroot}/etc/st2reactorcontroller
install -m755 st2reactorcontroller/bin/reactor_controller %{buildroot}/usr/bin/reactor_controller

%files

/usr/lib/python2.7/site-packages/st2reactorcontroller*
/usr/bin/reactor_controller
/etc/st2reactorcontroller*
