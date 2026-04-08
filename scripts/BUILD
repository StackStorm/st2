python_sources(
    overrides={
        # TODO: delete fixate*.py and lockfiles_to_reqs.py once migration to pants is complete.
        "lockfiles_to_reqs.py": dict(
            # Run this with `pants run scripts/lockfiles_to_reqs.py`
            # It runs in-repo (aka in the workspace) and directly edits files.
            run_goal_use_sandbox=False,
        )
    }
)

shell_sources(
    name="shell",
    skip_shfmt=True,
)
