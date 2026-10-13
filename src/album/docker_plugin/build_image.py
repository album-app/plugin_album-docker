"""Module to build a Docker image for an Album solution."""
import shutil
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import docker
from docker.errors import BuildError

import album.core.model.default_values
from album.api import Album
from album.runner.album_logging import get_active_logger

CUR_DIR = Path(__file__).parent
# name of the solution file inside a solution folder, "album install /solution" expects it
SOLUTION_FILE_NAME = (
    album.core.model.default_values.DefaultValues.solution_default_name.value
)
# the image archive is saved as <group>_<name>_<version>_image.tar
IMAGE_ARCHIVE_SUFFIX = "_image.tar"


def create_dockerfile(output_path, install_deps=None, install_flags=None):
    """Create a Dockerfile for the Album solution."""
    if install_flags is None:
        install_flags = ""
    if install_deps is not None and install_deps != "":
        install_deps = "RUN %s" % install_deps
    else:
        install_deps = ""
    dockerfile_str = f"""FROM albumsolutions/album:{album.core.__version__}
WORKDIR /
COPY . /solution
SHELL ["/bin/bash", "-l", "-c"]
RUN chmod +x /solution/solution_entrypoint.sh
RUN sed -i 's/\\r$//' /solution/solution_entrypoint.sh
# Convert Windows CRLF line endings to Unix LF — bash cannot execute scripts with \\r.
# Uses sed instead of dos2unix to avoid apt-get install inside the container.
{install_deps}
RUN album install {install_flags} /solution
ENTRYPOINT ["/solution/solution_entrypoint.sh"]
"""
    dockerfile_path = Path(output_path).joinpath("Dockerfile")
    with open(dockerfile_path, "w") as file:
        file.write(dockerfile_str)
    return dockerfile_path


def build_image(coordinates, context, output):
    """Build a Docker image from the given context and save it to the output directory."""
    coordinates = str(coordinates).replace(":", "_").lower()
    image_tar_name = coordinates + IMAGE_ARCHIVE_SUFFIX
    client = docker.from_env(timeout=1200)
    try:
        image, build_output = client.images.build(
            path=context, tag=coordinates, rm=True
        )
    except BuildError as e:
        # docker raises as soon as the build fails: log the build output up to the error and repeat its tail in
        # the error message, so the cause is visible even where album's log output is not shown (e.g. CI jobs)
        build_log = list(e.build_log)
        _log_build_output(iter(build_log))
        raise BuildError(_describe_build_error(e.msg, build_log), iter(build_log)) from e
    _log_build_output(build_output)

    image_tar_path = Path(output).joinpath(image_tar_name)
    with open(image_tar_path, "wb") as file:
        # naming the tag keeps it in the archive, otherwise the image is untagged after "docker load"
        for chunk in image.save(named="%s:latest" % coordinates):
            file.write(chunk)

    get_active_logger().info("Docker image tag: %s" % coordinates)
    get_active_logger().info("Docker image archive: %s" % image_tar_path)
    get_active_logger().info(
        'Load and run it with: docker load -i "%s" && docker run --rm %s <album run arguments>'
        % (image_tar_path, coordinates)
    )
    return image_tar_path


def _describe_build_error(reason, build_log, max_lines=40):
    """Return the build error reason followed by the last lines of the docker build output."""
    lines = []
    for chunk in build_log:
        text = (chunk.get("stream") or chunk.get("error") or "").strip()
        if text:
            lines.append(text)
    tail = lines[-max_lines:]
    return "%s\n--- docker build output (last %d lines) ---\n%s" % (reason, len(tail), "\n".join(tail))


def _log_build_output(build_output):
    """Log the output stream of a docker build."""
    for chunk in build_output:
        if "stream" in chunk:
            get_active_logger().info(chunk["stream"].strip())
        elif "error" in chunk:
            get_active_logger().error(chunk["error"].strip())


def get_solution_info(album_instance: Album, solution):
    """Get the solution path and coordinates from the Album instance.

    A solution which is not given as an existing folder or file (e.g. coordinates, a DOI or a URL) or which is given
    as a zip archive is resolved by Album. The resolved solution file lives in the solution folder together with all
    other files of the solution (for a zip archive: in the folder Album extracted it to), therefore the folder is
    returned in this case.
    """
    resolve_result = album_instance.resolve(str(solution))
    if not Path(solution).exists() or _is_zip_file(solution):
        path = Path(resolve_result.path())
        if path.is_file() and path.name == SOLUTION_FILE_NAME:
            path = path.parent
    else:
        path = solution
        if Path(solution).is_file():
            get_active_logger().warning(
                "Only the solution file %s is copied into the image, sibling files in its folder are not included. "
                "Pass the folder instead if the solution needs them." % solution
            )
    return path, resolve_result.coordinates()


def _is_zip_file(path):
    """Check whether the given path is a zip archive (Album extracts those when resolving them)."""
    return Path(path).is_file() and zipfile.is_zipfile(path)


def _ignore_image_archives(output):
    """Return a shutil.copytree ignore function which skips image archives inside the output directory.

    Otherwise, archives of earlier runs end up in the image if the output directory lies inside the solution folder.
    """
    output_dir = Path(output).resolve() if output is not None else None

    def ignore(directory, names):
        if output_dir is None or Path(directory).resolve() != output_dir:
            return []
        return [name for name in names if name.endswith(IMAGE_ARCHIVE_SUFFIX)]

    return ignore


def copy_to_context(src, target, output=None):
    """Copy the solution files to the Docker build context.

    A folder is copied with all its content except for image archives inside the output directory. A single solution
    file is copied as solution.py.
    """
    if Path(src).is_dir():
        shutil.copytree(
            src, target, ignore=_ignore_image_archives(output), dirs_exist_ok=True
        )
    else:
        get_active_logger().info(
            "Copying the solution file %s into the image as %s."
            % (src, SOLUTION_FILE_NAME)
        )
        # the image installs the folder /solution, which requires the solution file to be named solution.py
        shutil.copy(src, Path(target).joinpath(SOLUTION_FILE_NAME))

    # copy solution_entrypoint.sh to target
    entrypoint_script = CUR_DIR.joinpath("solution_entrypoint.sh")
    if entrypoint_script.exists():
        shutil.copy(entrypoint_script, target)
    else:
        get_active_logger().error("solution_entrypoint.sh not found in %s" % CUR_DIR)
        raise FileNotFoundError("solution_entrypoint.sh not found in %s" % CUR_DIR)


def run(album_instance: Album, args):
    """Run the Docker image build process for the given Album solution."""
    solution_path, coordinates = get_solution_info(album_instance, args.solution)

    if not (Path(args.output).exists()):
        Path(args.output).mkdir(parents=True)

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
        copy_to_context(solution_path, Path(tmpdir), args.output)
        get_active_logger().debug(
            "Copied solution %s to temporary directory." % solution_path
        )
        create_dockerfile(Path(tmpdir), args.install_deps, args.install_flags)
        get_active_logger().debug("Created Dockerfile in temporary directory.")
        build_image(coordinates, tmpdir, args.output)
        get_active_logger().info("Docker image built successfully.")
