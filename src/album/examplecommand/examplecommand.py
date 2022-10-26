from album.api import Album
from album.runner.album_logging import get_active_logger


def run(album_instance: Album, args):
    get_active_logger().info("Running a special command called examplecommand.")
    get_active_logger().info("--example-arg: %s" % args.example_arg)
    resolved_solution = album_instance.resolve(args.solution)
    get_active_logger().info("Resolved solution: %s" % resolved_solution.coordinates())


def create_parser(parser):
    p = parser.create_command_parser('examplecommand', run, 'Launch the examplecommand.')
    p.add_argument('solution', type=str, help='path for the solution file or coordinates of the solution (group:name:version)')
    p.add_argument('--example_arg', type=str, required=False, default="default value", help='An example argument')
