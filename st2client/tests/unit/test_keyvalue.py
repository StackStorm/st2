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

from __future__ import absolute_import
import argparse
import json
import logging
import mock
import os
import requests
import tempfile
import yaml

from tests import base
from st2client import shell

LOG = logging.getLogger(__name__)

KEYVALUE = {
    'id': 'kv_name',
    'name': 'kv_name.',
    'value': 'super cool value',
    'scope': 'system'
}

KEYVALUE_USER = {
    'id': 'kv_name',
    'name': 'kv_name.',
    'value': 'super cool value',
    'scope': 'system',
    'user': 'stanley'
}

KEYVALUE_SECRET = {
    'id': 'kv_name',
    'name': 'kv_name.',
    'value': 'super cool value',
    'scope': 'system',
    'secret': True
}

KEYVALUE_TTL = {
    'id': 'kv_name',
    'name': 'kv_name.',
    'value': 'super cool value',
    'scope': 'system',
    'ttl': 100
}

KEYVALUE_OBJECT = {
    'id': 'kv_name',
    'name': 'kv_name.',
    'value': {'obj': [1, True, 23.4, 'abc']},
    'scope': 'system',
}

KEYVALUE_ALL = {
    'id': 'kv_name',
    'name': 'kv_name.',
    'value': 'super cool value',
    'scope': 'system',
    'user': 'stanley',
    'secret': True,
    'ttl': 100
}

KEYVALUE_MISSING_NAME = {
    'id': 'kv_name',
    'value': 'super cool value'
}

KEYVALUE_MISSING_VALUE = {
    'id': 'kv_name',
    'name': 'kv_name.'
}


class TestKeyValueBase(base.BaseCLITestCase):
    """Base class for "key" CLI tests
    """

    capture_output = True

    def __init__(self, *args, **kwargs):
        super(TestKeyValueBase, self).__init__(*args, **kwargs)

        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-t', '--token', dest='token')
        self.parser.add_argument('--api-key', dest='api_key')
        self.shell = shell.Shell()

    def setUp(self):
        super(TestKeyValueBase, self).setUp()

    def tearDown(self):
        super(TestKeyValueBase, self).tearDown()


class TestKeyValueLoad(TestKeyValueBase):

    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(KEYVALUE), 200, 'OK')))
    def test_load_keyvalue_json(self):
        """Test loading of key/value pair in JSON format
        """
        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(KEYVALUE, indent=4))

            args = ['key', 'load', path]
            retcode = self.shell.run(args)
            self.assertEqual(retcode, 0)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(KEYVALUE), 200, 'OK')))
    def test_load_keyvalue_yaml(self):
        """Test loading of key/value pair in YAML format
        """
        fd, path = tempfile.mkstemp(suffix='.yaml')
        try:
            with open(path, 'a') as f:
                f.write(yaml.safe_dump(KEYVALUE))

            args = ['key', 'load', path]
            retcode = self.shell.run(args)
            self.assertEqual(retcode, 0)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(KEYVALUE_USER), 200, 'OK')))
    def test_load_keyvalue_user(self):
        """Test loading of key/value pair with the optional user field
        """
        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(KEYVALUE_USER, indent=4))

            args = ['key', 'load', path]
            retcode = self.shell.run(args)
            self.assertEqual(retcode, 0)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(KEYVALUE_SECRET), 200, 'OK')))
    def test_load_keyvalue_secret(self):
        """Test loading of key/value pair with the optional secret field
        """
        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(KEYVALUE_SECRET, indent=4))

            args = ['key', 'load', path]
            retcode = self.shell.run(args)
            self.assertEqual(retcode, 0)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(KEYVALUE_TTL), 200, 'OK')))
    def test_load_keyvalue_ttl(self):
        """Test loading of key/value pair with the optional ttl field
        """
        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(KEYVALUE_TTL, indent=4))

            args = ['key', 'load', path]
            retcode = self.shell.run(args)
            self.assertEqual(retcode, 0)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(KEYVALUE_OBJECT), 200, 'OK')))
    def test_load_keyvalue_object(self):
        """Test loading of key/value pair where the value is an object
        """
        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(KEYVALUE_OBJECT, indent=4))

            # test converting with short option
            args = ['key', 'load', '-c', path]
            retcode = self.shell.run(args)
            self.assertEqual(retcode, 0)

            # test converting with long option
            args = ['key', 'load', '--convert', path]
            retcode = self.shell.run(args)
            self.assertEqual(retcode, 0)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(KEYVALUE_OBJECT), 200, 'OK')))
    def test_load_keyvalue_object_fail(self):
        """Test failure to load key/value pair where the value is an object
           and the -c/--convert option is not passed
        """
        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(KEYVALUE_OBJECT, indent=4))

            # test converting with short option
            args = ['key', 'load', path]
            retcode = self.shell.run(args)
            self.assertNotEqual(retcode, 0)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(KEYVALUE_ALL), 200, 'OK')))
    def test_load_keyvalue_all(self):
        """Test loading of key/value pair with all optional fields
        """
        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(KEYVALUE_ALL, indent=4))

            args = ['key', 'load', path]
            retcode = self.shell.run(args)
            self.assertEqual(retcode, 0)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(KEYVALUE_ALL),
                                                      200, 'OK')))
    def test_load_keyvalue_array(self):
        """Test loading an array of key/value pairs
        """
        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            array = [KEYVALUE, KEYVALUE_ALL]
            json_str = json.dumps(array, indent=4)
            LOG.info(json_str)
            with open(path, 'a') as f:
                f.write(json_str)

            args = ['key', 'load', path]
            retcode = self.shell.run(args)
            self.assertEqual(retcode, 0)
        finally:
            os.close(fd)
            os.unlink(path)

    def test_load_keyvalue_missing_name(self):
        """Test loading of a key/value pair with the required field 'name' missing
        """
        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(KEYVALUE_MISSING_NAME, indent=4))

            args = ['key', 'load', path]
            retcode = self.shell.run(args)
            self.assertEqual(retcode, 1)
        finally:
            os.close(fd)
            os.unlink(path)

    def test_load_keyvalue_missing_value(self):
        """Test loading of a key/value pair with the required field 'value' missing
        """
        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(KEYVALUE_MISSING_VALUE, indent=4))

            args = ['key', 'load', path]
            retcode = self.shell.run(args)
            self.assertEqual(retcode, 1)
        finally:
            os.close(fd)
            os.unlink(path)

    def test_load_keyvalue_missing_file(self):
        """Test loading of a key/value pair with a missing file
        """
        path = '/some/file/that/doesnt/exist.json'
        args = ['key', 'load', path]
        retcode = self.shell.run(args)
        self.assertEqual(retcode, 1)

    def test_load_keyvalue_bad_file_extension(self):
        """Test loading of a key/value pair with a bad file extension
        """
        fd, path = tempfile.mkstemp(suffix='.badext')
        try:
            args = ['key', 'load', path]
            retcode = self.shell.run(args)
            self.assertEqual(retcode, 1)
        finally:
            os.close(fd)
            os.unlink(path)
