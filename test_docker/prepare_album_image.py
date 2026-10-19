"""Prepare the album image that the solution images of the integration tests start FROM.

A solution image starts with "FROM albumsolutions/album:<version of the installed album>" (see build_image.py).
Docker builds on a local image with this tag if there is one, so this script provides it:

- Normally the CI installs a released album, and the image is pulled from Docker Hub. This also replaces an image
  that the dev mode built under the same tag before that album version was released.
- In dev mode (CI variable ALBUM_DEV_DOCKER=True) album comes from its dev branch, and Docker Hub has no image for
  its version yet. The image is built the way album's release builds it, from the Dockerfile on album's dev branch,
  with album-solution-api and album-environments from their dev branches as well.

Run it with the Python of the environment that album and album-docker are installed in:

    python test_docker/prepare_album_image.py
"""
import os
import subprocess
import tempfile
from pathlib import Path

import docker
from docker.errors import BuildError

import album.core

IMAGE = "albumsolutions/album"
GITLAB = "https://gitlab.com/album-app/"
DEV_DEPENDENCIES = ["album-solution-api", "album-environments"]
# the platform of the published images, which the release builds on Linux x86_64
PLATFORM = "linux/amd64"


def dev_commit(project):
    """Return the commit that the dev branch of an album-app project points to."""
    result = subprocess.run(
        ["git", "ls-remote", GITLAB + project + ".git", "refs/heads/dev"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.split()[0]


def print_build_log(build_log):
    """Print the output of a docker build."""
    for chunk in build_log:
        print(chunk.get("stream", chunk.get("error", "")), end="")


def build_from_dev(client, tag):
    """Build the album image from album's dev branch, with album's dependencies from their dev branches."""
    # The commits instead of the branch name: Docker reuses a cached image only while these dev branches are unchanged.
    dependencies = " ".join(
        f"git+{GITLAB}{project}.git@{dev_commit(project)}"
        for project in DEV_DEPENDENCIES
    )
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        context = Path(tmp_dir).joinpath("album")
        # core.autocrlf=false: git on Windows may check out the scripts with CRLF, which bash in the image cannot run
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--depth",
                "1",
                "--branch",
                "dev",
                "-c",
                "core.autocrlf=false",
                GITLAB + "album.git",
                str(context),
            ],
            check=True,
        )
        # .git differs between two clones of the same commit and would keep Docker from reusing a cached image
        with open(context.joinpath(".dockerignore"), "a") as dockerignore:
            dockerignore.write("\n.git\n")
        print(
            f"Building {tag} from album's dev branch with {dependencies}",
            flush=True,
        )
        try:
            _, build_log = client.images.build(
                path=str(context),
                tag=tag,
                buildargs={"ALBUM_DEV_DEPENDENCIES": dependencies},
                platform=PLATFORM,
                pull=True,
                rm=True,
            )
        except BuildError as e:
            print_build_log(e.build_log)
            raise
        print_build_log(build_log)


def main():
    """Build the album image of the installed album version in dev mode, pull it otherwise."""
    tag = f"{IMAGE}:{album.core.__version__}"
    client = docker.from_env(timeout=1200)
    if os.environ.get("ALBUM_DEV_DOCKER") == "True":
        build_from_dev(client, tag)
    else:
        print(f"Pulling {tag}", flush=True)
        client.images.pull(IMAGE, tag=album.core.__version__, platform=PLATFORM)


if __name__ == "__main__":
    main()
