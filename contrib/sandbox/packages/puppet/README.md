# Puppet Content Pack

This content pack allows for integration with [Puppet](http://puppetlabs.com/).

Note: Puppet actions are executed using a remote runner which means they
run on the remote hosts.

## Actions

Currently, the following actions listed bellow are supported:

### Core

* Applying a standalone manifest to a local system - `puppet_apply`
* Run puppet agent - `puppet_run_agent`

### Certificate Management

* Certificate generation - `puppet_cert_generate`
* Certificate signing - `puppet_cert_sign`
* Certificate revocation - `puppet_cert_revoke`
* Certificate cleaning - `puppet_cert_clean`
