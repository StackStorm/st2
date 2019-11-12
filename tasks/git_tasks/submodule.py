from invoke import run, task


@task
def update(ctx, recursive=True):
    try:
        from git import Repo
    except ImportError:
        # Some of the tests rely on submodule so we need to make sure submodules are check out
        run("git submodule update --recursive --remote")
    else:
        repo = Repo()
        repo.submodule_update(recursive=recursive)
