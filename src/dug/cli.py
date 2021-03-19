"""
Represents the entrypointpoint for command line tools.

Currently the CLI code lives in core. That needs to be moved into here,
once we have removed/updated all other references to core
"""

from dug import core


def main():
    core.main()


if __name__ == '__main__':
    main()