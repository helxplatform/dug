"""
Represents the entrypoint for command line tools.

Currently the CLI code lives in core. That needs to be moved into this file,
once we have removed/updated other references to core
"""

from dug import core


def main():
    core.main()


if __name__ == '__main__':
    main()