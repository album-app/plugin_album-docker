"""Album Docker Plugin Argument Parsing Module."""
from album.api import Album


def album_docker(album_instance: Album, args):
    """Launch the building of a Docker image from the input solution."""
    from album.docker_plugin.build_image import run

    run(album_instance, args)


def create_docker_parser(parser):
    """Create the argument parser for the Docker plugin."""
    p = parser.create_command_parser(
        "docker",
        album_docker,
        "Launch the building of a docker image from the input solution.",
    )
    p.add_argument(
        "--solution",
        type=str,
        required=True,
        help="Path to the solution folder or solution file, or coordinates of the solution (group:name:version)",
    )
    p.add_argument(
        "--output",
        type=str,
        required=True,
        help="The directory where the image archive (<group>_<name>_<version>_image.tar) is saved",
    )
    p.add_argument(
        "--install-flags",
        type=str,
        default="",
        required=False,
        help="Flags to pass to the solution install command",
    )
    p.add_argument(
        "--install-deps",
        type=str,
        default="",
        required=False,
        help="Command which is added verbatim as a RUN line to the Dockerfile before the solution is installed, "
        "e.g. 'apt-get update && apt-get install -y g++ cmake'",
    )
