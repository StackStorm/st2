# Puppet Content Pack

This content pack allows for integration with [Puppet](http://puppetlabs.com/).

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

## How it works

All the actions except `puppet_apply` are Python actios which are executed
on the node where Stanley is running and work by talking to the puppet master
via the REST HTTP API.
