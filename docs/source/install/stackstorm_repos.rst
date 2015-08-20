.. _stackstorm-repos:

StackStorm Repositories
=======================

This section contain information about StackStorm APT and Yum repositories
which host StackStorm components and other dependencies such as winexe which
are required by StackStorm.

APT Repositories
----------------

::

  deb http://downloads.stackstorm.net/deb/ trusty_stable main

This repository contains latest stable version of StackStorm components
and dependencies.

::

  deb http://downloads.stackstorm.net/deb/ trusty_unstable main

This repository contains latest in development version of StackStorm components
and dependencies.

YUM Repositories
-----------------

::

  [st2-f20-deps]
  Name=StackStorm Dependencies Fedora repository
  baseurl=http://downloads.stackstorm.net/rpm/fedora/20/deps/
  enabled=1
  gpgcheck=0

This repository contains StackStorm dependencies.

::

  [st2-f20-components]
  Name=StackStorm Dependencies Fedora repository
  baseurl=http://downloads.stackstorm.net/rpm/fedora/20/stable/
  enabled=1
  gpgcheck=0

This repository contains latest stable version of StackStorm components.

::

  [st2-f20-components]
  Name=StackStorm Dependencies Fedora repository
  baseurl=http://downloads.stackstorm.net/rpm/fedora/20/unstable/
  enabled=1
  gpgcheck=0

This repository contains latest in development version of StackStorm components.
