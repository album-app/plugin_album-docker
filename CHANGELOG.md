# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

We use the following:

- `Added` for new features.
- `Changed` for changes in existing functionality.
- `Deprecated` for soon-to-be removed features.
- `Removed` for now removed features.
- `Fixed` for any bug fixes.
- `Security` in case of vulnerabilities.

## [unreleased]

## [0.2.2]

### Fixed

- the image archive keeps the image tag (it is saved under the tag `<group>_<name>_<version>:latest` that was just built), so `docker load -i <group>_<name>_<version>_image.tar` and `docker run <group>_<name>_<version>` work on another host
- the Dockerfile uses `WORKDIR /` and the absolute `ENTRYPOINT ["/solution/solution_entrypoint.sh"]`, so the image also starts when the working directory differs (e.g. `docker run -w ...`)
- a solution passed as coordinates (`group:name:version`) copies the whole folder of the resolved solution into the image, not only its `solution.py`
- a solution passed as a single file is copied as `solution.py`, so `album install` finds it inside the image; a warning states that sibling files are not included
- a solution passed as a local zip archive is extracted by Album and the extracted folder is copied into the image, not the archive itself
- image archives (`*_image.tar`) inside the output directory are not copied into the image, so earlier archives do not end up in the next image when the output directory lies inside the solution folder (e.g. `--solution . --output .`)
- the solution is resolved only once, so a DOI or URL is downloaded only once
- `--solution` is required (omitting it crashed with a `TypeError`)
- the output directory is created including missing parent directories
- no `None` line in the Dockerfile when `create_dockerfile` is called without install dependencies
- the output of a failed Docker build is logged up to the error, not only the final error message

### Changed

- the image tag and the path of the image archive are logged at the end of the build
- `--output` has no (unused) default anymore and `--install-deps` help states that the value is added verbatim as a Dockerfile `RUN` line, e.g. `apt-get update && apt-get install -y g++ cmake`
- README: correct `--output` flag, image tag and archive names, `docker load` / `docker run` usage, GPU usage and apt example
- Python 3.14 is listed among the supported Python versions; the CI tests it
- requires album 1.0 (`album>=1.0.0,<2.0.0`, was `album>=0.12.0,<0.13.0`)

## [0.2.1]

### Changed

- pyproject.toml over setup.cfg

## [0.2.0]

### Added

- changelog to the repository

[unreleased]: https://gitlab.com/album-app/album-docker/-/compare/v0.2.2...HEAD
[0.2.2]: https://gitlab.com/album-app/album-docker/-/compare/v0.2.1...v0.2.2
[0.2.1]: https://gitlab.com/album-app/album-docker/-/compare/v0.2.0...v0.2.1
[0.2.0]: https://gitlab.com/album-app/album-docker/-/tags/v0.2.0
