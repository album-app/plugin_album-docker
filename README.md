# Album plugin for creating Docker images from solutions

Plugin for creating Docker images from Album solutions.

The plugin allows you to package an Album solution into a Docker image, which can then be used to run the solution in a containerized environment,
containing all necessary dependencies and configurations.
Behavior of the container will be similar to the `album run` command, but the solution will be installed in a
Docker image instead of the local environment.
This is particularly useful for ensuring that the solution runs with all its dependencies in a consistent environment.

## Installation:

1. [Install Album](https://docs.album.solutions/en/latest/installation-instructions.html#)
2. Activate the album environment:

```
micromamba activate album
```

3. Install the album docker plugin:

```
micromamba install album-docker -c conda-forge
```

Or via pip:

```
pip install album-docker
```

## Usage:

To create a docker image which contains Album with the passed solution installed run following command:

```
album docker --solution mySolutionFolder --output /your/output/path
```

The `--solution` argument accepts:

- a solution folder (recommended): the whole folder, i.e. the `solution.py` file together with all its sibling files and subfolders, is copied into the image.
  If your `solution.py` is located in a folder with unrelated files, copy it (and the files it needs) into a new folder first, e.g. `mySolutionFolder`:

  ```
  mkdir mySolutionFolder
  cp /path/to/your/solution.py mySolutionFolder/
  ```

- the coordinates `<group>:<name>:<version>` of a solution in your Album collection: the folder of the resolved solution, including all its sibling files, is copied into the image.
- a direct path to a solution file: only this file is copied into the image (as `solution.py`), sibling files are not included (pass the folder instead). A warning is logged in this case.
- a zip archive of a solution folder: Album extracts it and the extracted folder is copied into the image.
- a URL or DOI of a solution: Album downloads it, and the downloaded solution (a single file or the extracted folder) is copied into the image.

The outcome is a docker image with the tag `<group>_<name>_<version>`, where `<group>`, `<name>`, and `<version>` are defined in the solution and the tag is lowercased
(e.g. the solution `my-group:My-Solution:0.1.0` gets the tag `my-group_my-solution_0.1.0`).
The image is available in the local Docker installation and is additionally saved as the archive `<group>_<name>_<version>_image.tar` (lowercased as well) in the output directory.
If the output directory lies inside the solution folder (e.g. `--solution . --output .`), the image archives (`*_image.tar`) of earlier runs in the output directory are not copied into the image.

### Input parameter:

- `--solution` (required): The album solution which should be packed into the image (folder, coordinates, solution file, zip archive, URL or DOI, see above).
- `--output` (required): The directory where the image archive `<group>_<name>_<version>_image.tar` is saved. It is created if it does not exist.
- `--install-flags`: Flags to pass to the `album install` command inside the image. Use the `=` form, because the value starts with `--`, e.g. `--install-flags=--allow-recursive`.
- `--install-deps`: A command which is added verbatim as a `RUN` line to the Dockerfile before the solution is installed, e.g. `apt-get update && apt-get install -y g++ cmake`.
  The image is based on Ubuntu, so use the apt package names (e.g. `g++`, not the conda package name `gxx`).

## Running the image:

Load the archive (e.g. on another machine) and run the image by its tag:

```
docker load -i /your/output/path/<group>_<name>_<version>_image.tar && docker run --rm -v /path/on/host:/data <group>_<name>_<version> --arg value
```

Everything after the image name is passed to `album run` of the installed solution,
i.e. the example above runs `album run /solution/solution.py --arg value` inside the container.
Use `-v` to mount folders of the host and pass the paths as they are seen inside the container (e.g. `/data/...`).

Docker options have to come BEFORE the image name, otherwise they are passed to `album run`.
For example, to give the container access to the GPUs (requires the NVIDIA Container Toolkit on the host) use:

```
docker run --rm --gpus all -v /path/on/host:/data <group>_<name>_<version> --arg value
```

## Example:

```
album docker --solution mySolutionFolder --output /your/output/path --install-flags="--allow-recursive" --install-deps="apt-get update && apt-get install -y g++ cmake"
```

This will create a docker image with the tag `<group>_<name>_<version>` of the solution and save it as `/your/output/path/<group>_<name>_<version>_image.tar`.
Inside the image, the solution is installed together with the dependencies g++ and cmake.
