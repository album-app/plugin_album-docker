# Album plugin for creating Docker images from solutions
This Album plugin creates a docker image, which contains a working Album environment and the passed solution installed.
The docker container can receive arguments which will be passed to the solution inside the container. 
The format of the arguments must follow the same format as the input arguments of the installed solution.


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

```
album docker --solution /path/to/your/solution.py --output_path /your/output/path  
```


### Input parameter:

- solution: The album solution.py file which should be packed into an executable.
  If you provide the path to a directory containing a solution.py all files in the directory will be packaged into the
  docker image. If you provide the direct path to a solution.py only the solution will be added to the image. If your solution
  contains local imports, make sure all imported files lie in the same directory as the solution and you provide the
  path containing the solution.py.
- output_path: The path where the executable should be saved
- install-flags: Flags to pass to the album isntall command, e.g. '--allow-recursive'
- install-deps: Dependencies to install in the docker image, e.g. 'gxx' or 'gxx cmake'

## Example:

```
album docker --solution /path/to/your/solution.py --output_path /your/output/path --install-flags '--allow-recursive' --install-deps 'apt update && apt install -y gxx cmake'
```

This will create a docker image with the tag <group:name:version> of the solution. 
Inside the image, the solution is installed together with the dependencies gxx and cmake.
