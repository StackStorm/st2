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

mI0EVNkBNwEEAOAYu3FL6NTYtMPuhbOk8P4QrSm+U+oT9+xuxcU1LRTOjIHMhTe/
xa18KVYoMSmiT3rOEj14PATvrrcOUX7hXVyfFSa/WBAjUvdeYq15GXNklxysZwsS
jSUnKCoCO8z33vGqHlFZHaPCtt/cio0KlJj13tMtdSSKSmNM2OjjV5WRABEBAAG0
GmZvbyBmb28gdGVzdCA8Zm9vQGZvby5jb20+iLcEEwEIACEFAlTZATcCGwMFCwkI
BwMFFQoJCAsFFgMCAQACHgECF4AACgkQPoqt0DG6DblH7wP+JXfj90UW4sJxWyQn
tyrbMXrZ4TibMxG5xSs36xpDqBasmptTI16tX5KzvXzYVAD3p0gPIOBjuXIC6mRh
xjTXYAdsQGWmJqlkLbM+/eATgnQsUoKGHYaqyb1GGDT3BI6j7QgwtkofJB+li07C
6dGDO2/P7fy2AOAmCM5/N5SPsKS4jQRU2QE3AQQAx9ldA6L9Ts5p1NBRPltH5E+5
k0HdzwTSLRR+MS5/kTTMajXL7tU6iXXaLKNw7SAzh+jK7wEajGPT29Na3fgfSmiB
fUWeqVWI+v9aedcdwk11uZgtuxu7DHUB5Phj9QAKMX+8l9c2iq0XYNl2ZW3izxVv
0E7a3FzYD2PJ/Vd/vIcAEQEAAYifBBgBCAAJBQJU2QE3AhsMAAoJED6KrdAxug25
CnMEANXJudLotn6lTABHMcMlwFhHL+yP9XTKlB8DvCMmRFpvaXF7WMwr9ytZEgx3
zjsWX3LvgPY+c0hxbBdfEf9YBIH3N4RYBheCBkJfHDgkmacQqnmVC4GcN22zarhq
QDvt0qBYuZcFha2fVlWzgLkFO+VfQcArb8E/5xT8KmtSNmHA
=yS0f
-----END PGP PUBLIC KEY BLOCK-----
'''

# Fingerprint of the public key
GPG_KEY_FINGERPRINT = '00FA 3B29 7305 4B94 37EC  5EDB 3E8A ADD0 31BA 0DB9'

# Bucket where the encrypted tarballs are uploaded (bucket is writeable
# by everyone, but only reeadable by StackStorm)
S3_BUCKET_URL = 'https://testbucket222211234123.s3.amazonaws.com/'
