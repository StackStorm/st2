# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import setup

REQUIRES = [
    'flake8'
]

setup(
    name='st2_flake8_plugins',
    version='0.1.0',
    author='StackStorm',
    author_email='info@stackstorm.com',
    url='https://www.stackstorm.com',
    packages=[
        'flake8_plugins'
    ],
    install_requires=REQUIRES,
    license='Apache License (2.0)',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6'
    ],
    entry_points={
        'flake8.extension': [
            'L = flake8_plugins.license_rules:LicenseChecker',
        ]
    }
)
