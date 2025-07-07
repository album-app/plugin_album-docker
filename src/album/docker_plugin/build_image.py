import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import docker

import album.core.model.default_values
from album.api import Album
from album.runner.album_logging import get_active_logger


def create_dockerfile(output_path, install_flags=None):
    if install_flags is None:
        install_flags = ""
    dockerfile_str = '''FROM albumsolutions/album:%s\n\nCOPY . /solution\n\nRUN album install %s /solution \n
ENTRYPOINT ["album", "run", "/solution/solution.py"]''' % (album.core.__version__, install_flags)
    dockerfile_path = Path(output_path).joinpath('Dockerfile')
    with open(dockerfile_path, 'w') as file:
        file.write(dockerfile_str)
    return dockerfile_path


def build_image(coordinates, context, output):
    coordinates = str(coordinates).replace(':', '_').lower()
    image_tar_name = "%s_image.tar" % coordinates
    client = docker.from_env()
    image = client.images.build(path=context, tag=coordinates, rm=True)[0]
    with open(Path(output).joinpath(image_tar_name), 'wb') as file:
        for chunk in image.save():
            file.write(chunk)


def get_solution_info(album_instance: Album, solution):
    if not Path(solution).exists():
        path = album_instance.resolve(str(solution)).path()
    else:
        path = solution
    coordinates = album_instance.resolve(str(solution)).coordinates()
    return path, coordinates


def copy_to_context(src, target):
    if Path(src).is_dir():
        for file in Path(src).glob('*'):
            if Path(file).is_file():
                shutil.copy(Path(file), target)
            else:
                shutil.copytree(Path(file), Path(target).joinpath(Path(file).name))
    else:
        shutil.copy(src, target)


def run(album_instance: Album, args):
    if not (Path(args.output).exists()):
        Path(args.output).mkdir()

    solution_path, coordinates = get_solution_info(album_instance, args.solution)

    get_active_logger().info("Build an docker image which runs the solution.")
    get_active_logger().info("solution: %s at %s" % (coordinates, solution_path))
    get_active_logger().info("output directory: %s" % args.output)
    get_active_logger().info("Using install flags: %s" % args.install_flags)

    with TemporaryDirectory() as tmpdir:
        get_active_logger().debug("Temporary directory for docker build: %s" % tmpdir)
        copy_to_context(solution_path, Path(tmpdir))
        get_active_logger().debug("Copied solution %s to temporary directory." % solution_path)
        create_dockerfile(Path(tmpdir), args.install_flags)
        get_active_logger().debug("Created Dockerfile in temporary directory.")
        build_image(coordinates, tmpdir, args.output)
        get_active_logger().info("Docker image built successfully.")
