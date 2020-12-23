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

import functools
import os
import pathlib
import time

from file_watch_sensor import SingleFileTail, TailManager

WAIT_TIME = 0.1


def test_single_file_tail_read_chunk_over_multibyte_character_boundary():
    wide_characters = [None, None, '\u0130', '\u2050', '\U00088080']
    for n in range(2, 5):
        yield from _gen_n_byte_character_tests(1024, n, wide_characters[n])

    for n in range(2, 5):
        yield from _gen_n_byte_character_tests(2048, n, wide_characters[n])

    for n in range(2, 5):
        yield from _gen_n_byte_character_tests(4096, n, wide_characters[n])


def _gen_n_byte_character_tests(chunk_size, n, char):
    for length in range(chunk_size, chunk_size + n + 1):
        yield _run_n_byte_character_tests, chunk_size, n, length, char


def _run_n_byte_character_tests(chunk_size, n, length, char):
    filename = f'chunk_boundary_{n}u_{length}.txt'

    with open(filename, 'wb+') as f:
        # Write out a file that is of the given length
        # aaaaaa...aaa\x82
        f.write(('a' * (length - n) + char).encode('utf-8'))

    fd = os.open(filename, os.O_RDONLY)

    sft = SingleFileTail(None, None, fd=fd)

    result = sft.read_chunk(fd, chunk_size=chunk_size)

    os.close(fd)
    os.unlink(filename)

    if length < chunk_size + n:
        assert result == ('a' * (length - n) + char)
    else:
        assert result == ('a' * chunk_size)


def test_single_file_tail_read_chunk_with_bad_utf8_character():
    filename = 'bad_utf8_character.txt'

    utf8_str = '\U00088080'
    utf8_bytes = utf8_str.encode('utf-8')
    chopped_utf8_bytes = utf8_bytes[:-1]

    with open(filename, 'wb+') as f:
        # Write out a file that is of the given length
        # aaaaaa...aaa\x82
        f.write(b'a')
        f.write(chopped_utf8_bytes)
        f.write(b'a')

    fd = os.open(filename, os.O_RDONLY)

    sft = SingleFileTail(None, None, fd=fd)

    err = None
    try:
        sft.read_chunk(fd)
    except Exception as e:
        err = e
    finally:
        assert err is not None
        assert isinstance(err, UnicodeDecodeError)

        os.close(fd)
        os.unlink(filename)


def test_single_file_tail_append_to_watched_file_with_absolute_path():
    tailed_filename = (pathlib.Path.cwd() / pathlib.Path('tailed_file.txt')).resolve()
    with open(tailed_filename, 'w+') as f:
        f.write("Preexisting text line 1\n")
        f.write("Preexisting text line 2\n")

    appended_lines = []

    def append_to_list(list_to_append, path, element):
        list_to_append.append(element)

    append_to_list_partial = functools.partial(append_to_list, appended_lines)

    tm = TailManager()
    tm.tail_file(tailed_filename, handler=append_to_list_partial)
    tm.start()

    with open(tailed_filename, 'a+') as f:
        f.write("Added line 1\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    tm.stop_tailing_file(tailed_filename, handler=append_to_list_partial)

    tm.stop()

    os.unlink(tailed_filename)


def test_single_file_tail_not_watched_file():
    tailed_filename = 'tailed_file.txt'
    not_tailed_filename = 'not_tailed_file.txt'
    new_not_tailed_filename = not_tailed_filename.replace('.txt', '_moved.txt')
    with open(tailed_filename, 'w+') as f:
        f.write("Preexisting text line 1\n")
        f.write("Preexisting text line 2\n")

    appended_lines = []

    def append_to_list(list_to_append, path, element):
        list_to_append.append(element)

    append_to_list_partial = functools.partial(append_to_list, appended_lines)

    tm = TailManager()
    tm.tail_file(tailed_filename, handler=append_to_list_partial)
    tm.start()

    with open(tailed_filename, 'a+') as f:
        f.write("Added line 1\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    with open(not_tailed_filename, 'a+') as f:
        f.write("Added line 1 - not tailed\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    os.replace(not_tailed_filename, new_not_tailed_filename)
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    tm.stop_tailing_file(tailed_filename, handler=append_to_list_partial)

    tm.stop()
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    os.unlink(tailed_filename)
    os.unlink(new_not_tailed_filename)


def test_single_file_tail_watch_nonexistent_file():
    tailed_filename = 'tailed_file.txt'

    if os.path.exists(tailed_filename):
        os.unlink(tailed_filename)

    appended_lines = []

    def append_to_list(list_to_append, path, element):
        list_to_append.append(element)

    append_to_list_partial = functools.partial(append_to_list, appended_lines)

    tm = TailManager()
    tm.tail_file(tailed_filename, handler=append_to_list_partial)
    tm.start()
    time.sleep(WAIT_TIME)

    assert appended_lines == []

    with open(tailed_filename, 'w+') as f:
        f.write("Added line 1\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    tm.stop_tailing_file(tailed_filename, handler=append_to_list_partial)

    tm.stop()
    time.sleep(WAIT_TIME)

    os.unlink(tailed_filename)


def test_single_file_tail_follow_watched_file_moved():
    tailed_filename = 'tailed_file_to_move.txt'
    new_filename = tailed_filename.replace('_to_move.txt', '_moved.txt')

    if os.path.exists(new_filename):
        os.unlink(new_filename)
    if os.path.exists(tailed_filename):
        os.unlink(tailed_filename)

    with open(tailed_filename, 'w+') as f:
        f.write("Preexisting text line 1\n")
        f.write("Preexisting text line 2\n")

    appended_lines = []

    def append_to_list(list_to_append, path, element):
        list_to_append.append(element)

    append_to_list_partial = functools.partial(append_to_list, appended_lines)

    tm = TailManager()
    tm.tail_file(tailed_filename, handler=append_to_list_partial, follow=True)
    tm.start()

    with open(tailed_filename, 'a+') as f:
        f.write("Added line 1\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write("Added line 2")  # No newline
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    os.replace(tailed_filename, new_filename)
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    with open(new_filename, 'a+') as f:
        f.write(" - end of line 2\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
        "Added line 2 - end of line 2",
    ]

    with open(tailed_filename, 'w+') as f:
        f.write("New file - text line 1\n")
        f.write("New file - text line 2\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
        "Added line 2 - end of line 2",
    ]

    tm.stop_tailing_file(tailed_filename, handler=append_to_list_partial)

    tm.stop()

    os.unlink(new_filename)
    os.unlink(tailed_filename)


def test_single_file_tail_not_followed_watched_file_moved():
    tailed_filename = 'tailed_file_to_move.txt'
    new_filename = tailed_filename.replace('_to_move.txt', '_moved.txt')

    if os.path.exists(new_filename):
        os.unlink(new_filename)
    if os.path.exists(tailed_filename):
        os.unlink(tailed_filename)

    with open(tailed_filename, 'w+') as f:
        f.write("Preexisting text line 1\n")
        f.write("Preexisting text line 2\n")

    appended_lines = []

    def append_to_list(list_to_append, path, element):
        list_to_append.append(element)

    append_to_list_partial = functools.partial(append_to_list, appended_lines)

    tm = TailManager()
    tm.tail_file(tailed_filename, handler=append_to_list_partial, follow=False)
    tm.start()

    with open(tailed_filename, 'a+') as f:
        f.write("Added line 1\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write("Added line 2")  # No newline
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    os.replace(tailed_filename, new_filename)
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
        "Added line 2",
    ]

    with open(new_filename, 'a+') as f:
        f.write(" - end of line 2\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
        "Added line 2",
    ]

    with open(tailed_filename, 'w+') as f:
        f.write("Recreated file - text line 1\n")
        f.write("Recreated file - text line 2\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
        "Added line 2",
        "Recreated file - text line 1",
        "Recreated file - text line 2",
    ]

    tm.stop_tailing_file(tailed_filename, handler=append_to_list_partial)

    tm.stop()

    os.unlink(new_filename)
    os.unlink(tailed_filename)


def test_single_file_tail_non_watched_file_moved():
    tailed_filename = 'tailed_file_to_move.txt'
    not_tailed_filename = f'not_{tailed_filename}'
    new_not_tailed_filename = not_tailed_filename.replace('_to_move.txt', '_moved.txt')

    if os.path.exists(not_tailed_filename):
        os.unlink(not_tailed_filename)
    if os.path.exists(new_not_tailed_filename):
        os.unlink(new_not_tailed_filename)
    if os.path.exists(tailed_filename):
        os.unlink(tailed_filename)

    with open(not_tailed_filename, 'w+') as f:
        f.write("Text here will not be monitored\n")

    with open(tailed_filename, 'w+') as f:
        f.write("Preexisting text line 1\n")
        f.write("Preexisting text line 2\n")

    appended_lines = []

    def append_to_list(list_to_append, path, element):
        list_to_append.append(element)

    append_to_list_partial = functools.partial(append_to_list, appended_lines)

    tm = TailManager()
    tm.tail_file(tailed_filename, handler=append_to_list_partial)
    tm.start()

    with open(tailed_filename, 'a+') as f:
        f.write("Added line 1\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    os.replace(not_tailed_filename, new_not_tailed_filename)
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    tm.stop_tailing_file(tailed_filename, handler=append_to_list_partial)

    tm.stop()

    os.unlink(new_not_tailed_filename)
    os.unlink(tailed_filename)


def test_single_file_tail_watched_file_deleted():
    tailed_filename = 'tailed_file_deleted.txt'
    with open(tailed_filename, 'w+') as f:
        f.write("Preexisting text line 1\n")
        f.write("Preexisting text line 2\n")

    appended_lines = []

    def append_to_list(list_to_append, path, element):
        list_to_append.append(element)

    append_to_list_partial = functools.partial(append_to_list, appended_lines)

    tm = TailManager()
    tm.tail_file(tailed_filename, handler=append_to_list_partial)
    tm.start()

    os.unlink(tailed_filename)

    tm.stop()


def test_tail_manager_append_to_watched_file():
    tailed_filename = 'tailed_file.txt'
    with open(tailed_filename, 'w+') as f:
        f.write("Preexisting text line 1\n")
        f.write("Preexisting text line 2\n")

    appended_lines = []

    def append_to_list(list_to_append, path, element):
        list_to_append.append(element)

    append_to_list_partial = functools.partial(append_to_list, appended_lines)

    tm = TailManager()
    tm.tail_file(tailed_filename, handler=append_to_list_partial)
    tm.start()

    with open(tailed_filename, 'a+') as f:
        f.write("Added line 1\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write("Added line 2\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
        "Added line 2",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write("Start of added partial line 1")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
        "Added line 2",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write(" - finished partial line 1\nStart of added partial line 2")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
        "Added line 2",
        "Start of added partial line 1 - finished partial line 1",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write(" - finished partial line 2\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
        "Added line 2",
        "Start of added partial line 1 - finished partial line 1",
        "Start of added partial line 2 - finished partial line 2",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write("Final line without a newline")
    time.sleep(WAIT_TIME)

    tm.stop_tailing_file(tailed_filename, handler=append_to_list_partial)

    tm.stop()

    time.sleep(WAIT_TIME)
    assert appended_lines == [
        "Added line 1",
        "Added line 2",
        "Start of added partial line 1 - finished partial line 1",
        "Start of added partial line 2 - finished partial line 2",
        "Final line without a newline",
    ]

    os.unlink(tailed_filename)


def test_tail_manager_tail_file_twice():
    tailed_filename = 'tailed_file.txt'
    with open(tailed_filename, 'w+') as f:
        f.write("Preexisting text line 1\n")
        f.write("Preexisting text line 2\n")

    appended_lines = []

    def append_to_list(list_to_append, path, element):
        list_to_append.append(element)

    append_to_list_partial = functools.partial(append_to_list, appended_lines)

    tm = TailManager()
    tm.tail_file(tailed_filename, handler=append_to_list_partial)
    tm.tail_file(tailed_filename, handler=append_to_list_partial)
    tm.start()

    with open(tailed_filename, 'a+') as f:
        f.write("Added line 1\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write("Added line 2\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
        "Added line 2",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write("Start of added partial line 1")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
        "Added line 2",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write(" - finished partial line 1\nStart of added partial line 2")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
        "Added line 2",
        "Start of added partial line 1 - finished partial line 1",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write(" - finished partial line 2\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
        "Added line 2",
        "Start of added partial line 1 - finished partial line 1",
        "Start of added partial line 2 - finished partial line 2",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write("Final line without a newline")
    time.sleep(WAIT_TIME)

    tm.stop_tailing_file(tailed_filename, handler=append_to_list_partial)

    tm.stop()

    time.sleep(WAIT_TIME)
    assert appended_lines == [
        "Added line 1",
        "Added line 2",
        "Start of added partial line 1 - finished partial line 1",
        "Start of added partial line 2 - finished partial line 2",
        "Final line without a newline",
    ]

    os.unlink(tailed_filename)


def test_tail_manager_stop():
    tailed_filename = 'tailed_file_stop.txt'
    with open(tailed_filename, 'w+') as f:
        f.write("Preexisting text line 1\n")
        f.write("Preexisting text line 2\n")

    appended_lines = []

    def append_to_list(list_to_append, path, element):
        list_to_append.append(element)

    append_to_list_partial = functools.partial(append_to_list, appended_lines)

    tm = TailManager()
    tm.tail_file(tailed_filename, handler=append_to_list_partial)
    tm.start()

    with open(tailed_filename, 'a+') as f:
        f.write("Added line 1\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write("Final line without a newline")
    time.sleep(WAIT_TIME)

    tm.stop()

    time.sleep(WAIT_TIME)
    assert appended_lines == [
        "Added line 1",
        "Final line without a newline",
    ]

    os.unlink(tailed_filename)


def test_tail_manager_stop_twice():
    tailed_filename = 'tailed_file_stop.txt'
    with open(tailed_filename, 'w+') as f:
        f.write("Preexisting text line 1\n")
        f.write("Preexisting text line 2\n")

    appended_lines = []

    def append_to_list(list_to_append, path, element):
        list_to_append.append(element)

    append_to_list_partial = functools.partial(append_to_list, appended_lines)

    tm = TailManager()
    tm.tail_file(tailed_filename, handler=append_to_list_partial)
    tm.start()

    with open(tailed_filename, 'a+') as f:
        f.write("Added line 1\n")
    time.sleep(WAIT_TIME)

    assert appended_lines == [
        "Added line 1",
    ]

    with open(tailed_filename, 'a+') as f:
        f.write("Final line without a newline")
    time.sleep(WAIT_TIME)

    tm.stop()
    tm.stop()

    time.sleep(WAIT_TIME)
    assert appended_lines == [
        "Added line 1",
        "Final line without a newline",
    ]

    os.unlink(tailed_filename)


if __name__ == '__main__':
    test_single_file_tail_not_followed_watched_file_moved()
