# Development Guide

## Git Branching


## Versioning

Our Python versioning strategy is informed by 
[Semantic Versioning](https://semver.org/) and 
[PEP-440](https://www.python.org/dev/peps/pep-0440/). 
We employ single-source versioning, the version number is defined in `src/dug/_version.py`. 
All build and automation tools should ultimately reference that file, or something that in turn references that file.
