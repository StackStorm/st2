from unmatched_globs.target_types import (
    PackMetadataNoUnmatchedGlobs,
    PythonLibraryNoUnmatchedGlobs,
)


def target_types():
    return [PackMetadataNoUnmatchedGlobs, PythonLibraryNoUnmatchedGlobs]
