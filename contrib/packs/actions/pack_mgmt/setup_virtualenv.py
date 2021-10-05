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

import os

from st2common.runners.base_action import Action
from st2common.util.virtualenvs import setup_pack_virtualenv

__all__ = ["SetupVirtualEnvironmentAction"]


class SetupVirtualEnvironmentAction(Action):
    """
    Action which sets up virtual environment for the provided packs.

    Setup consists of the following step:

    1. Create virtual environment for the pack
    2. Install base requirements which are common to all the packs
    3. Install pack-specific requirements (if any)

    If the 'update' parameter is set to True, the setup skips the deletion and
    creation of the virtual environment and performs an update of the
    current dependencies as well as an installation of new dependencies
    """

    def __init__(self, config=None, action_service=None):
        super(SetupVirtualEnvironmentAction, self).__init__(
            config=config, action_service=action_service
        )

        self.https_proxy = os.environ.get(
            "https_proxy", self.config.get("https_proxy", None)
        )
        self.http_proxy = os.environ.get(
            "http_proxy", self.config.get("http_proxy", None)
        )
        self.proxy_ca_bundle_path = os.environ.get(
            "proxy_ca_bundle_path", self.config.get("proxy_ca_bundle_path", None)
        )
        self.no_proxy = os.environ.get("no_proxy", self.config.get("no_proxy", None))

        self.proxy_config = None

        if self.http_proxy or self.https_proxy:
            self.logger.debug(
                "Using proxy %s",
                self.http_proxy if self.http_proxy else self.https_proxy,
            )
            self.proxy_config = {
                "https_proxy": self.https_proxy,
                "http_proxy": self.http_proxy,
                "proxy_ca_bundle_path": self.proxy_ca_bundle_path,
                "no_proxy": self.no_proxy,
            }

        if self.https_proxy and not os.environ.get("https_proxy", None):
            os.environ["https_proxy"] = self.https_proxy

        if self.http_proxy and not os.environ.get("http_proxy", None):
            os.environ["http_proxy"] = self.http_proxy

        if self.no_proxy and not os.environ.get("no_proxy", None):
            os.environ["no_proxy"] = self.no_proxy

        if self.proxy_ca_bundle_path and not os.environ.get(
            "proxy_ca_bundle_path", None
        ):
            os.environ["no_proxy"] = self.no_proxy

    def run(self, packs, update=False, no_download=True):
        """
        :param packs: A list of packs to create the environment for.
        :type: packs: ``list``

        :param update: True to update dependencies inside the virtual environment.
        :type update: ``bool``
        """

        for pack_name in packs:
            setup_pack_virtualenv(
                pack_name=pack_name,
                update=update,
                logger=self.logger,
                proxy_config=self.proxy_config,
                no_download=no_download,
            )

        message = "Successfully set up virtualenv for the following packs: %s" % (
            ", ".join(packs)
        )
        return message
