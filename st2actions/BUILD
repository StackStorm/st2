st2_component_python_distribution(
    component_name="st2actions",
    scripts=[
        "bin/st2actionrunner",
        "bin/st2notifier",
        "bin/st2workflowengine",
        "bin/st2scheduler",
        "bin/runners.sh:shell",  # used by service files installed by st2-packaging
    ],
    dependencies=[
        # policies get wired up by metadata in st2common/st2common/policies/meta/*.yaml
        "./st2actions/policies",
        # backwards compat API:
        # st2actions.runners.pythonrunner.Action moved to st2common.runners.base_action.Action
        "./st2actions/runners/pythonrunner.py",
    ],
)
