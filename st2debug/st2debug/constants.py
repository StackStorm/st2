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
    'GPG_KEY',
    'GPG_KEY_FINGERPRINT'
]

# Public part of the GPG key which is used to encrypt tarballs with debugging
# information
GPG_KEY = '''
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1

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
=asEc
-----END PGP PUBLIC KEY BLOCK-----
'''

# Fingerprint of the public key
GPG_KEY_FINGERPRINT = 'BDE989A1F308B18D29789C717064B11C82F62D6F'

# Bucket where the encrypted tarballs are uploaded (bucket is writeable
# by everyone, but only reeadable by StackStorm)
S3_BUCKET_URL = 'https://st2debuginfo.s3.amazonaws.com/'

# Default company name used in interactive prompts
COMPANY_NAME = 'StackStorm'

# Default command line argument list
ARG_NAMES = ['exclude_logs', 'exclude_configs', 'exclude_content',
             'exclude_system_info']
