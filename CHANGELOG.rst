Changelog
=========

in development
--------------

v0.6.0 - TBD
--------------

Docs: http://docs.stackstorm.com/latest

* Separate virtualenv per pack. (Pythonic sensors and actions use them by default.)
* Install pip requirements from requiremets.txt in packs by default.
* Sensors are now run in their own process for isolation.
* Python Actions are now run in their own process for isolation.
* Add Sensor and PollingSensor base classes. (Sensors API change is non-backward compatible.)
* Separate out rules_engine into own process.
* YAML support for action, rules and chain meta.
* Add sensor meta support (JSON/YAML) to specify trigger types.
* Packs default path moves from /opt/stackstorm to /opt/stackstorm/packs/.
* Webhooks are not part of a sensor. They are now part of core API. (Authentication may
  be required.)
* Numerous bug fixes.


v0.5.0 - November 3rd, 2014
---------------------------

Docs: http://docs.stackstorm.com/0.5.0/

* Initial public release
