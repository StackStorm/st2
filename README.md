Stanley
======

Integrate and automate your cloud operations.

### Prerequisites 
To setup the development environment with all the prerequisites installed via Vagrant, please refer to the README under https://github.com/StackStorm/devenv.

The list of prerequisites:
* MongoDB -http://docs.mongodb.org/manual/installation
* Python, pip, virtualenv, tox
* For Web UI: 	
	* nodejs and npm - http://nodejs.org/
	* [bower](http://bower.io/), [gulp.js](http://gulpjs.com/)
 	

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

## Copyright and license
<br>Copyright 2014 StackStorm, Inc.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this work except in compliance with the License. You may obtain a copy of the License in the LICENSE file, or at:

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
