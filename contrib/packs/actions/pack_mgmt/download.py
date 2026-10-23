# -*- coding: utf-8 -*-
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

import six

from st2common.runners.base_action import Action
from st2common.util.pack_management import download_pack

__all__ = ["DownloadGitRepoAction"]


class DownloadGitRepoAction(Action):
    def __init__(self, config=None, action_service=None):
        super(DownloadGitRepoAction, self).__init__(
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

        # This is needed for git binary to work with a proxy
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

    def run(
        self,
        packs,
        abs_repo_base,
        verifyssl=True,
        force=False,
        dependency_list=None,
        checkout_submodules=False,
    ):
        result = {}
        pack_url = None

        if dependency_list:
            for pack_dependency in dependency_list:
                pack_result = download_pack(
                    pack=pack_dependency,
                    abs_repo_base=abs_repo_base,
                    verify_ssl=verifyssl,
                    force=force,
                    proxy_config=self.proxy_config,
                    force_permissions=True,
                    logger=self.logger,
                    checkout_submodules=checkout_submodules,
                )
                pack_url, pack_ref, pack_result = pack_result
                result[pack_ref] = pack_result
        else:
            for pack in packs:
                pack_result = download_pack(
                    pack=pack,
                    abs_repo_base=abs_repo_base,
                    verify_ssl=verifyssl,
                    force=force,
                    proxy_config=self.proxy_config,
                    force_permissions=True,
                    logger=self.logger,
                    checkout_submodules=checkout_submodules,
                )
                pack_url, pack_ref, pack_result = pack_result
                result[pack_ref] = pack_result

        return self._validate_result(result=result, repo_url=pack_url)

    @staticmethod
    def _validate_result(result, repo_url):
        atleast_one_success = False
        sanitized_result = {}

        for k, v in six.iteritems(result):
            atleast_one_success |= v[0]
            sanitized_result[k] = v[1]

        if not atleast_one_success:
            message_list = []
            message_list.append(
                'The pack has not been downloaded from "%s".\n' % (repo_url)
            )
            message_list.append("Errors:")

            for pack, value in result.items():
                success, error = value
                message_list.append(error)

            message = "\n".join(message_list)
            raise Exception(message)

        return sanitized_result
