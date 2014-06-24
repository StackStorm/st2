Stanley
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

### Using nosetests to execute specific tests
Activate the virtual environment.
* To run tests in a specific project

        nosetests -v {project_name}/tests

* To run tests in a specific test file

        nosetests -v {project_name}/tests/{path_to_test_file}/{test_file}.py

* To run tests in a specific class

        nosetests -v {project_name}/tests/{path_to_test_file}/{test_file}.py:{Classname} 

* To run a specific test method

        nosetests -v {project_name}/tests/{path_to_test_file}/{test_file}.py:{Classname}.{method_name} 

