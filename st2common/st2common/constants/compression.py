# Copyright 2020 The StackStorm Authors.
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

"""
Mongoengine is licensed under MIT.
"""


import enum
import zstandard

ZSTANDARD_COMPRESS = "zstandard"
NO_COMPRESSION = "none"

VALID_COMPRESS = [ZSTANDARD_COMPRESS, NO_COMPRESSION]


class JSONDictFieldCompressionAlgorithmEnum(enum.Enum):
    """
    Enum which represents compression algorithm (if any) used for a specific JSONDictField value.
    """

    ZSTANDARD = b"z"


VALID_JSON_DICT_COMPRESSION_ALGORITHMS = [
    JSONDictFieldCompressionAlgorithmEnum.ZSTANDARD.value,
]


def zstandard_compress(data):
    data = (
        JSONDictFieldCompressionAlgorithmEnum.ZSTANDARD.value
        + zstandard.ZstdCompressor().compress(data)
    )
    return data


def zstandard_uncompress(data):
    data = zstandard.ZstdDecompressor().decompress(data)
    return data


MAP_COMPRESS = {
    ZSTANDARD_COMPRESS: zstandard_compress,
}


MAP_UNCOMPRESS = {
    JSONDictFieldCompressionAlgorithmEnum.ZSTANDARD.value: zstandard_uncompress,
}
