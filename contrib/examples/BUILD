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
