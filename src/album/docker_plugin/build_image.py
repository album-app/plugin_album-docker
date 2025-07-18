"""Module to build a Docker image for an Album solution."""
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import docker

import album.core.model.default_values
from album.api import Album
from album.runner.album_logging import get_active_logger

CUR_DIR = Path(__file__).parent


def create_dockerfile(output_path, install_deps=None, install_flags=None):
    """Create a Dockerfile for the Album solution."""
    if install_flags is None:
        install_flags = ""
    if install_deps is not None and install_deps != "":
        install_deps = "RUN %s" % install_deps
    dockerfile_str = f"""FROM albumsolutions/album:{album.core.__version__}
COPY . /solution
SHELL ["/bin/bash", "-l", "-c"]
RUN chmod +x /solution/solution_entrypoint.sh
RUN apt update
RUN apt install -y dos2unix
RUN dos2unix /solution/solution_entrypoint.sh
{install_deps}
RUN album install {install_flags} /solution
ENTRYPOINT ["./solution/solution_entrypoint.sh"]
"""
    dockerfile_path = Path(output_path).joinpath("Dockerfile")
    with open(dockerfile_path, "w") as file:
        file.write(dockerfile_str)
    return dockerfile_path


def build_image(coordinates, context, output):
    """Build a Docker image from the given context and save it to the output directory."""
    coordinates = str(coordinates).replace(":", "_").lower()
    image_tar_name = "%s_image.tar" % coordinates
    client = docker.from_env(timeout=1200)
    image, build_output = client.images.build(path=context, tag=coordinates, rm=True)

    for chunk in build_output:
        if "stream" in chunk:
            get_active_logger().info(chunk["stream"].strip())
        elif "error" in chunk:
            get_active_logger().error(chunk["error"].strip())

    with open(Path(output).joinpath(image_tar_name), "wb") as file:
        for chunk in image.save():
            file.write(chunk)


def get_solution_info(album_instance: Album, solution):
    """Get the solution path and coordinates from the Album instance."""
    if not Path(solution).exists():
        path = album_instance.resolve(str(solution)).path()
    else:
        path = solution
    coordinates = album_instance.resolve(str(solution)).coordinates()
    return path, coordinates


def copy_to_context(src, target):
    """Copy the solution files to the Docker build context."""
    if Path(src).is_dir():
        for file in Path(src).glob("*"):
            if Path(file).is_file():
                shutil.copy(Path(file), target)
            else:
                shutil.copytree(Path(file), Path(target).joinpath(Path(file).name))
    else:
        shutil.copy(src, target)

    # copy solution_entrypoint.sh to target
    entrypoint_script = CUR_DIR.joinpath("solution_entrypoint.sh")
    if entrypoint_script.exists():
        shutil.copy(entrypoint_script, target)
    else:
        get_active_logger().error("solution_entrypoint.sh not found in %s" % CUR_DIR)
        raise FileNotFoundError("solution_entrypoint.sh not found in %s" % CUR_DIR)


def run(album_instance: Album, args):
    """Run the Docker image build process for the given Album solution."""
    if not (Path(args.output).exists()):
        Path(args.output).mkdir()

    solution_path, coordinates = get_solution_info(album_instance, args.solution)

    get_active_logger().info("Building an docker image which runs the solution.")
    get_active_logger().info(f"solution: {coordinates} at {solution_path}")
    get_active_logger().info("output directory: %s" % args.output)
    get_active_logger().info("Using install flags: %s" % args.install_flags)
    get_active_logger().info("Using install dependencies: %s" % args.install_deps)
    get_active_logger().info(
        "This may take a while. Logs will be printed after the build is finished. Please be patient."
    )

    with TemporaryDirectory() as tmpdir:
        get_active_logger().debug("Temporary directory for docker build: %s" % tmpdir)
        copy_to_context(solution_path, Path(tmpdir))
        get_active_logger().debug(
            "Copied solution %s to temporary directory." % solution_path
        )
        create_dockerfile(Path(tmpdir), args.install_deps, args.install_flags)
        get_active_logger().debug("Created Dockerfile in temporary directory.")
        build_image(coordinates, tmpdir, args.output)
        get_active_logger().info("Docker image built successfully.")
