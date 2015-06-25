* ``skip_notify`` (array) - List of tasks to skip notifications for.
* ``task`` (string) - The name of the task to run for reverse workflow.
* ``context`` (object) - Additional workflow inputs.
* ``workflow`` (string) - The name of the workflow to run if the entry_point is a workbook of many workflows. The name should be in the format "<pack_name>.<action_name>.<workflow_name>". If entry point is a workflow or a workbook with a single workflow, the runner will identify the workflow automatically.