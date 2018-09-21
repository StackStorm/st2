# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__all__ = [
    'PACK_VIRTUALENV_DOESNT_EXIST',
    'PACK_VIRTUALENV_USES_PYTHON3'
]

PACK_VIRTUALENV_DOESNT_EXIST = '''
The virtual environment (%(virtualenv_path)s) for pack "%(pack)s" does not exist. Normally this is
created when you install a pack using "st2 pack install". If you installed your pack by some other
means, you can create a new virtual environment using the command:
"st2 run packs.setup_virtualenv packs=%(pack)s"
'''

PACK_VIRTUALENV_USES_PYTHON3 = '''
Virtual environment (%(virtualenv_path)s) for pack "%(pack)s" is using Python 3.
Using Python 3 virtual environments in mixed deployments is only supported for Python runner
actions and not sensors. If you want to run this sensor, please re-recreate the
virtual environment with python2 binary:
"st2 run packs.setup_virtualenv packs=%(pack)s python3=false"
'''
