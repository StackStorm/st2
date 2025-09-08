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


def st2_publish_repos():
    """Return the list of repos twine should publish to.

    Twine will publish to ALL of these repos when running `pants publish`.

    We use ST2_PUBLISH_REPO, an env var, To facilitate switching between
    @testpypi and @pypi. That also means someone could publish to their own
    private repo by changing this var.

    Credentials for pypi should be in ~/.pypirc or in TWINE_* env vars.
    """
    return [env("ST2_PUBLISH_REPO", "@pypi")]  # noqa: F821


def st2_license(**kwargs):
    """Copy the LICENSE file into each wheel.

    As long as the file is in the src root when building the sdist/wheel,
    setuptools automatically includes the LICENSE file in the dist-info.
    """
    if "dest" not in kwargs:
        raise ValueError("'dest' path is required for st2_license macro")
    relocated_files(  # noqa: F821
        name="license",
        files_targets=["//:license"],
        src="",
        **kwargs,
    )


def st2_runner_python_distribution(**kwargs):
    """Create a python_distribution (wheel/sdist) for a StackStorm runner."""
    runner_name = kwargs.pop("runner_name")
    description = kwargs.pop("description")

    st2_license(dest=f"contrib/runners/{runner_name}_runner")

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
    for dep in [f"./{runner_name}_runner", ":license"]:
        if dep not in dependencies:
            dependencies.append(dep)

    kwargs["dependencies"] = dependencies
    kwargs["repositories"] = st2_publish_repos()

    python_distribution(**kwargs)  # noqa: F821


def st2_component_python_distribution(**kwargs):
    """Create a python_distribution (wheel/sdist) for a core StackStorm component."""
    st2_component = kwargs.pop("component_name")
    description = (
        f"{st2_component} StackStorm event-driven automation platform component"
    )
    # setup(scripts=[...]) is for pre-made scripts, which we have.
    # TODO: use entry_points.console_scripts instead of hand-generating these.
    scripts = kwargs.pop("scripts", [])

    st2_license(dest=st2_component)

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
    for dep in [st2_component, ":license"] + scripts:
        dep = f"./{dep}" if dep[0] != ":" else dep
        if dep not in dependencies:
            dependencies.append(dep)

        # see st2_shell_sources_and_resources below
        if dep.endswith(":shell"):
            dep_res = f"{dep}_resources"
            if dep_res not in dependencies:
                dependencies.append(dep_res)

    kwargs["dependencies"] = dependencies
    kwargs["repositories"] = st2_publish_repos()

    python_distribution(**kwargs)  # noqa: F821


# Default copied from PEX (which uses zipfile standard MS-DOS epoch).
# https://github.com/pex-tool/pex/blob/v2.1.137/pex/common.py#L39-L45
MTIME = "1980-01-01T00:00:00Z"

# These are used for system packages (rpm/deb)
ST2_PACKS_GROUP = "st2packs"
ST2_SVC_USER = "st2"


def st2_pack_archive(**kwargs):
    """Create a makeself_archive using files from the given dependencies.

    This macro should be used in the same BUILD file as the pack_metadata target.
    """
    build_file_path = build_file_dir()  # noqa: F821
    if "st2tests" == build_file_path.parts[0]:
        # avoid creating duplicate archive for the core pack
        # which is also located under st2tests/st2tests/fixtures/packs
        return
    pack_name = build_file_path.name  # noqa: F821

    dependencies = kwargs.pop("dependencies", [])
    if ":metadata" not in dependencies:
        dependencies = [":metadata", *dependencies]

    # This is basically a "wrap_as_files" target (which does not exist yet)
    shell_command(  # noqa: F821
        name="files",
        execution_dependencies=dependencies,
        command="true",
        output_directories=["."],
        root_output_directory=".",
    )

    # https://www.pantsbuild.org/stable/docs/shell/self-extractable-archives
    # https://www.pantsbuild.org/stable/reference/targets/makeself_archive
    makeself_archive(  # noqa: F821
        name="archive",
        label=f"{pack_name} StackStorm pack",
        files=[
            ":files",  # archive contents
            "//:license",  # LICENSE file included in archive header, excluded from contents
        ],
        args=(  # see: https://makeself.io/#usage
            # Makeself expects '--arg value' (space) not '--arg=value' (equals) for cmdline
            "--license",
            "__archive/LICENSE",
            "--target",
            f"/opt/stackstorm/packs/{pack_name}",
            # reproducibility flags:
            "--tar-extra",  # extra tar args: '--arg=value' (equals delimited) space separated
            f"--owner=root --group={ST2_PACKS_GROUP} --mtime={MTIME} --exclude=LICENSE",
            "--packaging-date",
            MTIME,
        ),
        output_path=f"packaging/packs/{pack_name}.tgz.run",
    )

    nfpm_content_file(  # noqa: F821
        name="archive_for_nfpm",
        dependencies=[":archive"],
        src=f"packaging/packs/{pack_name}.tgz.run",
        dst=f"/opt/stackstorm/install/packs/{pack_name}.tgz.run",
        file_owner="root",
        file_group=ST2_PACKS_GROUP,
        file_mode="rwxr-x---",
    )


def st2_shell_sources_and_resources(**kwargs):
    """This creates a shell_sources and a resources target.

    This is needed because python_sources dependencies on shell_sources
    are silently ignored. So, we also need the resources target
    to allow depending on them.
    """
    shell_sources(**kwargs)  # noqa: F821

    kwargs.pop("skip_shellcheck", None)
    kwargs.pop("skip_shfmt", None)

    kwargs["name"] += "_resources"
    resources(**kwargs)  # noqa: F821


# these are referenced by the logging.*.conf files.
_st2common_logging_deps = (
    "//st2common/st2common/log.py",
    "//st2common/st2common/logging/formatters.py",
)


def st2_logging_conf_files(**kwargs):
    """This creates a files target with logging dependencies."""
    deps = kwargs.pop("dependencies", []) or []
    deps = list(deps) + list(_st2common_logging_deps)
    kwargs["dependencies"] = tuple(deps)
    files(**kwargs)  # noqa: F821


def st2_logging_conf_file(**kwargs):
    """This creates a file target with logging dependencies."""
    deps = kwargs.pop("dependencies", []) or []
    deps = list(deps) + list(_st2common_logging_deps)
    kwargs["dependencies"] = tuple(deps)
    file(**kwargs)  # noqa: F821


def st2_logging_conf_resources(**kwargs):
    """This creates a resources target with logging dependencies."""
    deps = kwargs.pop("dependencies", []) or []
    deps = list(deps) + list(_st2common_logging_deps)
    kwargs["dependencies"] = tuple(deps)
    resources(**kwargs)  # noqa: F821


def st2_logging_conf_for_nfpm(**kwargs):
    deps = kwargs.pop("dependencies") or []

    shell_command(  # noqa: F821
        name="package_logging_conf",
        execution_dependencies=deps,
        # Using "-E" and specifying the ".bak" suffix makes this portable
        command="""
        sed -E -i.bak "/args[[:space:]]*=[[:space:]]*/s:logs/:/var/log/st2/:g" logging.*conf;
        for conf_file in logging.*conf syslog.*conf; do
            crudini --verbose --set "${conf_file}" logger_root level INFO;
        done
        """,
        runnable_dependencies=["//:crudini"],
        tools=["sed"],
        output_files=["*.conf"],
    )

    nfpm_content_files(  # noqa: F821
        name="packaged_conf_files",
        dependencies=[":package_logging_conf"],
        file_owner="root",
        file_group="root",
        file_mode="rw-r--r--",
        content_type="config|noreplace",
        **kwargs,
    )
