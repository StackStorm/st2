Summary: StackStorm Debug Tool
Name: st2debug
Version: 0.4.0
Release: 1
License: Apache
Group: Applications/Engineering
BuildArch: noarch
Source: /opt/git/st2/st2debug.tar.gz
URL: https://github.com/StackStorm/st2
Vendor: StackStorm
Packager: Estee Tew <st2@stackstorm.com>
Requires:       st2common

%description
An automation plaform that needs a much better description than this.

%prep
%setup

%install

mkdir -p %{buildroot}/usr/local/lib/python2.7/site-packages/
mkdir -p %{buildroot}/usr/bin
cp -R st2debug %{buildroot}/usr/local/lib/python2.7/site-packages/
install -m755 bin/st2-submit-debug-info %{buildroot}/usr/bin/st2-submit-debug-info

%files

/usr/local/lib/python2.7/site-packages/st2debug*
/usr/bin/st2-submit-debug-info
