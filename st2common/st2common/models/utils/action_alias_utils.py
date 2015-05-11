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

from st2common.exceptions import content


class JsonValueParser(object):
    """
    Sort of but not really JSON parsing. This parser only really cares if there are matching
    braces to stop the iteration.

    """
    start = '{'
    end = '}'

    @staticmethod
    def is_applicable(first_char):
        return first_char == JsonValueParser.start

    @staticmethod
    def parse(start, stream):
        end = 0
        char_idx = start
        message_depth = 0
        while not end:
            char = stream[char_idx]
            if char == JsonValueParser.start:
                message_depth += 1
            elif char == JsonValueParser.end:
                message_depth -= 1
            if not message_depth:
                end = char_idx
            else:
                char_idx += 1
                if char_idx == len(stream):
                    raise content.ParseException('What sort of messed up stream did you provide!')
        # preserve the start and end chars
        return start, stream[start:end + 1], end + 1


class StringValueParser(object):
    start = '"'
    end = '"'
    escape = '\\'

    @staticmethod
    def is_applicable(first_char):
        return first_char == StringValueParser.start

    @staticmethod
    def parse(start, stream):
        end = 0
        char_idx = start + 1
        while not end:
            char = stream[char_idx]
            if char == StringValueParser.end and stream[char_idx - 1] != StringValueParser.escape:
                end = char_idx
            else:
                char_idx += 1
                if char_idx == len(stream):
                    raise content.ParseException('What sort of messed up stream did you provide!')
        # skip the start and end chars
        return start, stream[start + 1:end], end + 1


class DefaultParser(object):

    end = ' '

    @staticmethod
    def is_applicable(first_char):
        return True

    @staticmethod
    def parse(start, stream):
        end = stream.find(DefaultParser.end, start)
        # if not found pick until end of stream. In this way the default parser is different
        # from other parser as they would always requires an end marker
        if end == -1:
            end = len(stream)
        try:
            return start, stream[start:end], end
        except IndexError:
            raise content.ParseException('What sort of messed up stream did you provide!')

PARSERS = [JsonValueParser, StringValueParser, DefaultParser]


class ActionAliasFormatParser(object):

    FORMAT_MARKER_START = '{{'
    FORMAT_MARKER_END = '}}'
    PARAM_DEFAULT_VALUE_SEPARATOR = '='

    def __init__(self, alias_format, param_stream):
        self._format = alias_format
        self._param_stream = param_stream or ''
        self._alias_fmt_ptr = 0
        self._param_strm_ptr = 0

    def __iter__(self):
        return self

    def next(self):
        try:
            p_start, param_format, p_end = self._get_next_param_format()
            param_name, default_value = self._get_param_name_default_value(param_format)
        except ValueError:
            # If we get back a ValueError then time to stop the iteration.
            raise StopIteration()

        # compute forward progress of the alias format pointer
        v_start = p_start - self._alias_fmt_ptr + self._param_strm_ptr
        value = None

        # make sure v_start is within param_stream
        if v_start < len(self._param_stream):
            _, value, v_end = self._get_next_value(v_start)

            # move the alias_fmt_ptr to one beyond the end of each
            self._alias_fmt_ptr = p_end
            self._param_strm_ptr = v_end
        elif v_start < len(self._format):
            # Advance in the format string
            # Note: We still want to advance in the format string even though
            # there is nothing left in the param stream since we support default
            # values and param_stream can be empty
            self._alias_fmt_ptr = p_end

        if not value and not default_value:
            raise content.ParseException('No value supplied and no default value found.')

        return param_name, value if value else default_value

    def get_extracted_param_value(self):
        return {name: value for name, value in self}

    def _get_next_param_format(self):
        mrkr_strt_ps = self._format.index(self.FORMAT_MARKER_START, self._alias_fmt_ptr)
        try:
            mrkr_end_ps = self._format.index(self.FORMAT_MARKER_END, mrkr_strt_ps)
        except ValueError:
            # A start marker was found but end is not therefore this is a Parser exception.
            raise content.ParseException('Expected end marker.')
        param_format = self._format[mrkr_strt_ps + len(self.FORMAT_MARKER_START): mrkr_end_ps]
        return mrkr_strt_ps, param_format.strip(), mrkr_end_ps + len(self.FORMAT_MARKER_END)

    def _get_param_name_default_value(self, param_format):
        if not param_format:
            return None, None
        values = param_format.split(self.PARAM_DEFAULT_VALUE_SEPARATOR)
        return values[0], values[1] if len(values) > 1 else None

    def _get_next_value(self, start):
        parser = self._get_parser(self._param_stream[start])
        return parser.parse(start, self._param_stream)

    def _get_parser(self, first_char):
        for parser in PARSERS:
            if parser.is_applicable(first_char):
                return parser
        raise Exception('No parser found')
