kandra
======

### Prerequisites 
The dev environment with all the prerequisites installed via Vagrant: https://github.com/StackStorm/devenv. 
The list of prerequisites: 
* nodejs and npm - http://nodejs.org/
* MongoDB -http://docs.mongodb.org/manual/installation
* Python, pip, virtualenv, tox

### Using make for typical tasks
* To create virtualenv, install dependencies, and run tests
 
        make all

* To run all tests
 
        make tests

* To drop virtualenv

        make distclean

* To install updated requirements
 
        make requirements

* To just create virtualenv:

        make virtualenv
