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


def st2_runner_python_distribution(**kwargs):
    runner_name = kwargs.pop("runner_name")
    description = kwargs.pop("description")

    kwargs["provides"] = python_artifact(  # noqa: F821
        name=f"stackstorm-runner-{runner_name.replace('_', '-')}",
        description=description,
        version_file=f"{runner_name}_runner/__init__.py",  # custom for our release plugin
        # test_suite="tests",
        zip_safe=kwargs.pop(
            "zip_safe", True
        ),  # most runners are safe to run from a zipapp
    )

    dependencies = kwargs.pop("dependencies", [])
    for dep in [f"./{runner_name}_runner"]:
        if dep not in dependencies:
            dependencies.append(dep)
    kwargs["dependencies"] = dependencies

    repositories = kwargs.pop("repositories", [])
    for repo in ["@pypi"]:
        if repo not in repositories:
            repositories.append(repo)
    kwargs["repositories"] = repositories

    python_distribution(**kwargs)  # noqa: F821


def st2_component_python_distribution(**kwargs):
    st2_component = kwargs.pop("component_name")

    description = (
        f"{st2_component} StackStorm event-driven automation platform component"
    )

    scripts = kwargs.pop("scripts", [])

    kwargs["provides"] = python_artifact(  # noqa: F821
        name=st2_component,
        description=description,
        scripts=[
            script[:-6] if script.endswith(":shell") else script for script in scripts
        ],
        version_file=f"{st2_component}/__init__.py",  # custom for our release plugin
        # test_suite=st2_component,
        zip_safe=False,  # We rely on __file__ to load many things, so st2 should not run from a zipapp
    )

    dependencies = kwargs.pop("dependencies", [])

    for dep in [st2_component] + scripts:
        dep = f"./{dep}" if dep[0] != ":" else dep
        if dep not in dependencies:
            dependencies.append(dep)

        # see st2_shell_sources_and_resources below
        if dep.endswith(":shell"):
            dep_res = f"{dep}_resources"
            if dep_res not in dependencies:
                dependencies.append(dep_res)

    kwargs["dependencies"] = dependencies

    repositories = kwargs.pop("repositories", [])
    for repo in ["@pypi"]:
        if repo not in repositories:
            repositories.append(repo)
    kwargs["repositories"] = repositories

    python_distribution(**kwargs)  # noqa: F821


def st2_shell_sources_and_resources(**kwargs):
    """This creates a shell_sources and a resources target.

    This is needed because python_sources dependencies on shell_sources
    are silently ignored. So, we also need the resources target
    to allow depending on them.
    """
    shell_sources(**kwargs)  # noqa: F821

    kwargs.pop("skip_shellcheck", None)

    kwargs["name"] += "_resources"
    resources(**kwargs)  # noqa: F821
