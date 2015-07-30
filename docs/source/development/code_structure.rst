:orphan:

Code structure
==============

You might be tempted to contribute to |st2| by this point. Let us walk you through the code a
bit.

StackStorm/st2 repo
===================

|st2| is made up of individual services viz. `st2auth`, `st2api`, `st2rulesengine`,
`st2sensorcontainer`, `st2actionrunner`, `st2notifier`.

Also, |st2| has a CLI and client library. Code for all these services and components are laid
out in different folders in the repo root.

st2common
=========

Common code that contains db and api data models, utility functions and common service code
that all of |st2| needs. Each service package (deb/rpm) has a dependency on st2common package
being available. So if you want common code that should be shared amongst components written,
you'd add them here.

st2api
======

This folder contains code for API controllers in |st2|. APIs are versioned and so are controllers.
Experimental controllers are added to `exp` folder inside st2api and when they mature, they are
moved to folders containing versioned controllers.

st2auth
=======

Contains code for st2auth endpoint. Since this endpoint needs to deployed separately than st2api,
it is available as a separate app.

st2actions
==========

Contains code for action runners. A new runner written for |st2| would be added to
st2actions/st2actions/runners. Also, this folder contains the code for worker node that scans
rabbitmq for incoming executions.

Notifier and results tracker are also part of this code base. Notifier is the component that
sends notification triggers and action triggers at the end of action execution. Results tracker
is an advanced async results querier for certain kind of runners like mistral where execution of
a workflow is kicked off remotely and you have to hit the mistral APIs to collect results in a
polling fashion.

st2client
=========

Contains code for both |st2| client library and |st2| cli bundled into one folder. We will
eventually split them out.

st2debug
========

If you are familiar with ``st2-submit-debug-info`` tool, the code for that is present in this folder.
This tool provides a way to share logs and other info with a |st2| engineer for troubleshooting.

st2reactor
==========

Contains code for both sensor container and rules engine.

st2tests
========

Shared code containing fixtures and test utilities that helps in unit and integration testing
for all |st2| components.
