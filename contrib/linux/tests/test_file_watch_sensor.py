#!/usr/bin/env python

# Copyright 2020 The StackStorm Authors.
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

import logging
import os
import pathlib

# import sys
# import threading
import time

import eventlet
import mock
from file_watch_sensor import FileWatchSensor

WAIT_TIME = 1

logger = logging.getLogger(__name__)


def test_file_watch_sensor():
    mock_sensor_service = mock.MagicMock()
    mock_logger = mock.MagicMock()

    filename = "test.txt"
    filepath = pathlib.Path(filename).absolute().resolve()
    filepath.touch()

    fws = FileWatchSensor(
        sensor_service=mock_sensor_service, config={}, logger=mock_logger
    )

    time.sleep(WAIT_TIME)

    fws.setup()

    time.sleep(WAIT_TIME)

    # th = threading.Thread(target=fws.run)
    th = eventlet.spawn(fws.run)
    th.start()

    time.sleep(WAIT_TIME)

    fws.add_trigger(
        {
            "id": "asdf.adsfasdf-asdf-asdf-asdfasdfasdf",
            "pack": "linux",
            "name": "asdf.adsfasdf-asdf-asdf-asdfasdfasdf",
            "ref": "linux.asdf.adsfasdf-asdf-asdf-asdfasdfasdf",
            "uid": "trigger:linux:asdf.adsfasdf-asdf-asdf-asdfasdfasdf",
            "type": "linux.file_watch.line",
            "parameters": {
                "file_path": filepath,
                "follow": True,
            },
        }
    )

    time.sleep(WAIT_TIME)

    with open(filepath, "a") as f:
        f.write("Added line 1\n")

    time.sleep(WAIT_TIME)

    with open(filepath, "a") as f:
        f.write("Added line 2\n")

    time.sleep(WAIT_TIME)

    expected_calls = [
        mock.call(
            trigger="linux.asdf.adsfasdf-asdf-asdf-asdfasdfasdf",
            payload={
                "file_path": pathlib.PosixPath("/vagrant/contrib/linux/test.txt"),
                "file_name": "test.txt",
                "line": "Added line 1",
            },
        ),
        mock.call(
            trigger="linux.asdf.adsfasdf-asdf-asdf-asdfasdfasdf",
            payload={
                "file_path": pathlib.PosixPath("/vagrant/contrib/linux/test.txt"),
                "file_name": "test.txt",
                "line": "Added line 2",
            },
        ),
    ]
    mock_sensor_service.dispatch.assert_has_calls(expected_calls, any_order=False)
    print(mock_logger.method_calls)
    # th.join()

    fws.cleanup()

    os.unlink(filepath)


def test_file_watch_sensor_without_trigger_filepath():
    mock_sensor_service = mock.MagicMock()
    mock_logger = mock.MagicMock()

    filename = "test.txt"
    filepath = pathlib.Path(filename).absolute().resolve()
    filepath.touch()

    fws = FileWatchSensor(
        sensor_service=mock_sensor_service, config={}, logger=mock_logger
    )

    time.sleep(WAIT_TIME)

    fws.setup()

    time.sleep(WAIT_TIME)

    # th = threading.Thread(target=fws.run)
    th = eventlet.spawn(fws.run)
    th.start()

    time.sleep(WAIT_TIME)

    fws.add_trigger(
        {
            "id": "asdf.adsfasdf-asdf-asdf-asdfasdfasdf",
            "pack": "linux",
            "name": "asdf.adsfasdf-asdf-asdf-asdfasdfasdf",
            "ref": "linux.asdf.adsfasdf-asdf-asdf-asdfasdfasdf",
            "uid": "trigger:linux:asdf.adsfasdf-asdf-asdf-asdfasdfasdf",
            "type": "linux.file_watch.line",
            "parameters": {
                # 'file_path': filepath,
                "follow": True,
            },
        }
    )


def test_file_watch_sensor_without_trigger_ref():
    mock_sensor_service = mock.MagicMock()
    mock_logger = mock.MagicMock()

    filename = "test.txt"
    filepath = pathlib.Path(filename).absolute().resolve()
    filepath.touch()

    fws = FileWatchSensor(
        sensor_service=mock_sensor_service, config={}, logger=mock_logger
    )

    time.sleep(WAIT_TIME)

    fws.setup()

    time.sleep(WAIT_TIME)

    # th = threading.Thread(target=fws.run)
    th = eventlet.spawn(fws.run)
    th.start()

    time.sleep(WAIT_TIME)

    try:
        fws.add_trigger(
            {
                "id": "asdf.adsfasdf-asdf-asdf-asdfasdfasdf",
                "pack": "linux",
                "name": "asdf.adsfasdf-asdf-asdf-asdfasdfasdf",
                # 'ref': 'linux.asdf.adsfasdf-asdf-asdf-asdfasdfasdf',
                "uid": "trigger:linux:asdf.adsfasdf-asdf-asdf-asdfasdfasdf",
                "type": "linux.file_watch.line",
                "parameters": {
                    "file_path": filepath,
                    "follow": True,
                },
            }
        )
    except Exception as e:
        # Make sure we ignore the right exception
        if "did not contain a ref" not in str(e):
            raise e
    else:
        raise AssertionError(
            "FileWatchSensor.add_trigger() did not raise an "
            "exception when passed a trigger without a ref"
        )
    finally:
        os.unlink(filepath)


if __name__ == "__main__":
    # logger.setLevel(logging.DEBUG)

    # handler = logging.StreamHandler(sys.stderr)
    # handler.setLevel(logging.DEBUG)
    # formatter = logging.Formatter('%(name)s: %(levelname)s: %(message)s')

    # logger.addHandler(handler)

    test_file_watch_sensor()
    test_file_watch_sensor_without_trigger_filepath()
    test_file_watch_sensor_without_trigger_ref()
