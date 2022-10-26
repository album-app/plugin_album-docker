import logging
import os
import re
from pathlib import Path

import pkg_resources

from album.api import Album
from album.runner.album_logging import get_active_logger


def run():
    print("I AM RUNNING")
