# Copyright 2023 The StackStorm Authors.
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
from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent

from uses_services.platform_rules import Platform


@dataclass(frozen=True)
class ServiceSpecificMessages:
    service: str

    service_start_cmd_el_7: str
    service_start_cmd_el: str
    not_installed_clause_el: str
    install_instructions_el: str

    service_start_cmd_deb: str
    not_installed_clause_deb: str
    install_instructions_deb: str

    service_start_cmd_generic: str

    env_vars_hint: str = ""


class ServiceMissingError(Exception):
    """Error raised when a test uses a service but that service is missing."""

    def __init__(
        self, service: str, platform: Platform, instructions: str = "", msg=None
    ):
        if msg is None:
            msg = f"The {service} service does not seem to be running or is not accessible!"
            if instructions:
                msg += f"\n{instructions}"
        super().__init__(msg)
        self.service = service
        self.platform = platform
        self.instructions = instructions

    @classmethod
    def generate(
        cls, platform: Platform, messages: ServiceSpecificMessages
    ) -> ServiceMissingError:
        service = messages.service

        supported = False
        if platform.distro in ["centos", "rhel"] or "rhel" in platform.distro_like:
            supported = True
            if platform.distro_major_version == "7":
                service_start_cmd = messages.service_start_cmd_el_7
            else:
                service_start_cmd = messages.service_start_cmd_el
            not_installed_clause = messages.not_installed_clause_el
            install_instructions = messages.install_instructions_el

        elif (
            platform.distro in ["ubuntu", "debian"] or "debian" in platform.distro_like
        ):
            supported = True
            service_start_cmd = messages.service_start_cmd_deb
            not_installed_clause = messages.not_installed_clause_deb
            install_instructions = messages.install_instructions_deb

        if supported:
            instructions = dedent(
                f"""\
                If {service} is installed, but not running try:

                {service_start_cmd}

                If {service} is not installed, {not_installed_clause}:

                """
            ).format(
                service=service,
                service_start_cmd=service_start_cmd,
                not_installed_clause=not_installed_clause,
            )
            instructions += install_instructions
        elif platform.os == "Linux":
            instructions = dedent(
                f"""\
                You are on Linux using {platform.distro_name}, which is not
                one of our generally supported distributions. We recommend
                you use vagrant for local development with something like:

                vagrant init stackstorm/st2
                vagrant up
                vagrant ssh

                Please see: https://docs.stackstorm.com/install/vagrant.html

                For anyone who wants to attempt local development without vagrant,
                you are pretty much on your own. At a minimum you need to install
                and start {service} with something like:

                {messages.service_start_cmd_generic}

                We would be interested to hear about alternative distros people
                are using for development. If you are able, please let us know
                on slack which distro you are using:

                Arch: {platform.arch}
                Distro: {platform.distro}
                Distro Name: {platform.distro_name}
                Distro Codename: {platform.distro_codename}
                Distro Family: {platform.distro_like}
                Distro Major Version: {platform.distro_major_version}
                Distro Version: {platform.distro_version}

                Thanks and Good Luck!
                """
            )
        elif platform.os == "Darwin":  # MacOS
            instructions = dedent(
                f"""\
                You are on Mac OS. Generally we recommend using vagrant for local
                development on Mac OS with something like:

                vagrant init stackstorm/st2
                vagrant up
                vagrant ssh

                Please see: https://docs.stackstorm.com/install/vagrant.html

                For anyone who wants to attempt local development without vagrant,
                you may run into some speed bumps. Other StackStorm developers have
                been known to use Mac OS for development, so feel free to ask for
                help in slack. At a minimum you need to install and start {service}.
                """
            )
        else:
            instructions = dedent(
                f"""\
                You are not on Linux. In this case we recommend using vagrant
                for local development with something like:

                vagrant init stackstorm/st2
                vagrant up
                vagrant ssh

                Please see: https://docs.stackstorm.com/install/vagrant.html

                For anyone who wants to attempt local development without vagrant,
                you are pretty much on your own. At a minimum you need to install
                and start {service}. Good luck!

                Detected OS: {platform.os}
                """
            )

        if messages.env_vars_hint:
            instructions += f"\n\n{messages.env_vars_hint}"

        return cls(
            service=service,
            platform=platform,
            instructions=instructions,
        )
