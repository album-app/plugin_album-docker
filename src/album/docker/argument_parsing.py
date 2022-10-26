from pathlib import Path

from album.api import Album
from album.runner.album_logging import get_active_logger


#def run(album_instance: Album, args):
#    get_active_logger().info("Running a special command called examplecommand.")
#    get_active_logger().info("--solution: %s" % args.example_arg)
#    resolved_solution = album_instance.resolve(args.solution)
#    get_active_logger().info("Resolved solution: %s" % resolved_solution.coordinates())


def album_docker(album_instance: Album, args):
    from album.docker.build_image import run
    run(album_instance, args)


def create_docker_parser(parser):
    p = parser.create_command_parser('docker', album_docker, 'Launch the building of a docker image from the input solution.')
    p.add_argument('--solution', type=str, help='Path for the solution file or coordinates of the solution (group:name:version)')
    p.add_argument('--output', type=str, required=True, default=str(Path.home()), help='The path where the build image should be saved')
