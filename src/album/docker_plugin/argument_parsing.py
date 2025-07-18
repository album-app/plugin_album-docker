from pathlib import Path

from album.api import Album


def album_docker(album_instance: Album, args):
    from album.docker_plugin.build_image import run
    run(album_instance, args)


def create_docker_parser(parser):
    p = parser.create_command_parser('docker', album_docker,
                                     'Launch the building of a docker image from the input solution.')
    p.add_argument('--solution', type=str,
                   help='Path for the solution file or coordinates of the solution (group:name:version)')
    p.add_argument('--output', type=str, required=True, default=str(Path.home()),
                   help='The path where the build image should be saved')
    p.add_argument('--install-flags', type=str, default='', required=False,
                   help="Flags to pass to the solution install command")
    p.add_argument('--install-deps', type=str, default='', required=False,
                     help="Dependencies to install in the docker image, e.g. 'gxx' or 'gxx cmake'")
