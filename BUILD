python_requirements(
    name="reqs",
    source="requirements-pants.txt",
    overrides={
        # flex and stevedore uses pkg_resources w/o declaring the dep
        ("flex", "stevedore"): dict(
            dependencies=[
                "//:reqs#setuptools",
            ]
        ),
        # do not use the prance[flex] extra as that pulls in an old version of flex
        "prance": dict(
            dependencies=[
                "//:reqs#flex",
            ]
        ),
        # tooz needs one or more backends (tooz is used by the st2 coordination backend)
        "tooz": dict(
            dependencies=[
                "//:reqs#redis",
                "//:reqs#zake",
            ]
        ),
        # make sure anything that uses st2-auth-ldap gets the st2auth constant
        "st2-auth-ldap": dict(
            dependencies=[
                "st2auth/st2auth/backends/constants.py",
            ]
        ),
        # make sure anything that uses st2-rbac-backend gets its deps
        "st2-rbac-backend": dict(
            dependencies=[
                # alphabetical order
                "st2common/st2common/config.py",
                "st2common/st2common/constants/keyvalue.py",
                "st2common/st2common/constants/triggers.py",
                "st2common/st2common/content/loader.py",
                "st2common/st2common/exceptions/db.py",
                "st2common/st2common/exceptions/rbac.py",
                "st2common/st2common/log.py",
                "st2common/st2common/models/api/rbac.py",
                "st2common/st2common/models/db/action.py",
                "st2common/st2common/models/db/auth.py",
                "st2common/st2common/models/db/pack.py",
                "st2common/st2common/models/db/rbac.py",
                "st2common/st2common/models/db/webhook.py",
                "st2common/st2common/models/system/common.py",
                "st2common/st2common/persistence/auth.py",
                "st2common/st2common/persistence/execution.py",
                "st2common/st2common/persistence/rbac.py",
                "st2common/st2common/rbac/backends/__init__.py",
                "st2common/st2common/rbac/backends/base.py",
                "st2common/st2common/rbac/types.py",
                "st2common/st2common/script_setup.py",
                "st2common/st2common/util/action_db.py",
                "st2common/st2common/util/misc.py",
                "st2common/st2common/util/uid.py",
            ]
        ),
    },
)

target(
    name="auth_backends",
    dependencies=[
        "//:reqs#st2-auth-backend-flat-file",
        "//:reqs#st2-auth-ldap",
        "//:reqs#st2-auth-backend-pam",
    ],
)

target(
    name="rbac_backends",
    dependencies=[
        "//:reqs#st2-rbac-backend",
    ],
)

python_test_utils(
    name="test_utils",
    skip_pylint=True,
)

file(
    name="license",
    source="LICENSE",
)

shell_sources(
    name="root",
)

file(
    name="logs_directory",
    source="logs/.gitignore",
)

files(
    name="gitmodules",
    sources=[
        ".gitmodules",
        "**/.git",
    ],
)

shell_command(
    name="capture_git_modules",
    environment="in_repo_workspace",
    command="cp -r .git/modules {chroot}/.git",
    tools=["cp"],
    # execution_dependencies allows pants to invalidate the output
    # of this command if the .gitmodules file changes (for example:
    # if a submodule gets updated to a different repo).
    # Sadly this does not get invalidated if the submodule commit
    # is updated. In our case, that should be rare. To work around
    # this, kill the `pantsd` process after updating a submodule.
    execution_dependencies=[":gitmodules"],
    output_dependencies=[":gitmodules"],
    output_directories=[".git/modules"],
    workdir="/",
)
