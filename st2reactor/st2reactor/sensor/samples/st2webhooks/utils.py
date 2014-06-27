import os


def test_depends(foo):
    return foo + ' from ' + os.getcwd()
