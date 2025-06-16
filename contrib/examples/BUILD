__defaults__(all=dict(inject_pack_python_path=True))

pack_metadata(
    name="metadata",
)

# Using `python_requirements()` here results in:
# ">1 target exports this module, so it is ambiguous which to use"
# This error refers to the "requests" module.
# So, we explicitly list deps instead.

python_requirement(
    name="beautifulsoup4",
    requirements=["beautifulsoup4"],
)

python_requirement(
    name="flask",
    requirements=["flask"],
)

# Also capture the requirements file for distribution in the pack archive.
files(
    name="reqs",
    sources=["requirements*.txt"],
)

st2_pack_archive(
    # we need to list targets of all files because transitive dep targets are NOT included
    dependencies=[
        ":metadata",
        ":reqs",
        "./actions",
        "./actions:shell",
        "./actions/bash_exit_code",
        "./actions/bash_ping",
        "./actions/bash_random",
        "./actions/pythonactions",
        "./actions/ubuntu_pkg_info",
        "./actions/ubuntu_pkg_info/lib",
        "./actions/windows",
        "./lib",
        "./sensors",
        "./tests",
    ],
)
