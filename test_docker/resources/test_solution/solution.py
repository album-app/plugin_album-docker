from album.runner.api import setup

env_file = """name: import_unittest
channels:
  - conda-forge
dependencies:
  - python=3.9
  - pip
"""


def install():
    pass


def run():
    pass

    print("Success!")


def test():
    pass

    print("Hello")


def close():
    pass

    print("closing")


setup(
    group="album",
    name="import_unittest",
    version="0.1.0",
    title="A Solution the unittest of the album package plugin",
    description="A Solution to run the Vascuec App.",
    authors=["Lucas Rieckert", "Jan Philipp Albrecht"],
    cite=[{"text": "Your first citation text", "doi": "your first citation doi"}],
    tags=["unittest"],
    license="UNLICENSE",
    documentation="",
    covers=[{"description": "Dummy cover image.", "source": "cover.png"}],
    album_api_version="0.4.2",
    install=install,
    run=run,
    close=close,
    test=test,
    dependencies={"environment_file": env_file},
)
