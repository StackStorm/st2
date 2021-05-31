from pants.engine.target import COMMON_TARGET_FIELDS, Dependencies, Target
from pants.core.target_types import FilesSources


class PackMetadataSources(FilesSources):
    required = False
    default = (
        # metadata does not include any python, shell, or other sources.
        "pack.yaml",
        "config.schema.yaml",
        "*.yaml.example",
        "**/*.yaml",
        "**/*.yml",
        "icon.png",  # used in st2web ui
        "requirements*.txt",
        # "README.md",
        # "HISTORY.md",
    )


class PackMetadata(Target):
    alias = "pack_metadata"
    core_fields = (*COMMON_TARGET_FIELDS, Dependencies, PackMetadataSources)
    help = (
        "Loose pack metadata files.\n\n"
        "Pack metadata includes top-level files (pack.yaml, <pack>.yaml.examle, "
        "config.schema.yaml, icon.png, and requirements.txt) and metadata for actions, "
        "action-aliases, policies, rules, and sensors."
    )
