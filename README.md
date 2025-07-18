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
conda activate album
```

3. Install the album docker plugin:

```
pip install album-docker
```

## Usage:

To create a docker image which contains Album with the passed solution installed run following command:

If your solution is in a directory, you can copy the solution.py file into a new folder, e.g. `mySolutionFolder`, and then run the command from that folder.

```
mkdir mySolutionFolder
cp /path/to/your/solution.py mySolutionFolder/
```

Then run the following command to create the docker image:

```

album docker --solution mySolutionFolder --output_path /your/output/path
```

The outcome will be a docker image with the tag `<group>:<name>:<version>` of the solution, where `<group>`, `<name>`, and `<version>` are defined in the solution.py file.

### Input parameter:

- solution: The album solution which should be packed into an executable.
- output_path: The path where the executable should be saved
- install-flags: Flags to pass to the album install command, e.g. '--allow-recursive'.
- install-deps: Dependencies to install in the docker image, e.g. 'gxx' or 'gxx cmake'. This line will be added to the Dockerfile as a RUN command, so you can use any command that is valid in a Dockerfile.

## Example:

```
album docker --solution mySolutionFolder --output_path /your/output/path --install-flags="--allow-recursive" --install-deps="apt update && apt install -y gxx cmake"
```

This will create a docker image with the tag <group:name:version> of the solution.
Inside the image, the solution is installed together with the dependencies gxx and cmake.
