# coding=utf-8
"""OctoPrint Uptime plugin setup module.

Provides packaging metadata for the OctoPrint-Uptime plugin.
"""

import copy
import os
import re
from typing import List, Optional

from setuptools import setup

#######################################################################
# Do not forget to adjust the following variables to your own plugin.
#
# The plugin's identifier, has to be unique
PLUGIN_IDENTIFIER = "uptime"

# The plugin's python package. Should be "octoprint_<plugin identifier>"
# and must be unique.
PLUGIN_PACKAGE = "octoprint_uptime"

# The plugin's human readable name. Can be overridden within OctoPrint's
# internal data via __plugin_name__ in the plugin module.
PLUGIN_NAME = "OctoPrint-Uptime"

# The plugin's version. This reads the single source-of-truth from
# octoprint_uptime/_version.py so packaging and runtime use the same value.


def _read_version():
    """
    Reads the version string from the _version.py file located in the plugin package directory.

    Returns:
        str: The version string if found, otherwise "0.0.0".
    """
    here = os.path.abspath(os.path.dirname(__file__))
    ver_path = os.path.join(here, PLUGIN_PACKAGE, "_version.py")
    version = "0.0.0"
    version_pattern = re.compile(r'^VERSION\s*=\s*[\'"]([^\'"]+)[\'"]')
    try:
        with open(ver_path, "r", encoding="utf-8") as f:
            for line in f:
                match = version_pattern.match(line)
                if match:
                    version = match.group(1)
                    break
    except (FileNotFoundError, OSError):
        pass
    return version


# The plugin's version. Can be overridden within OctoPrint's internal data
# via __plugin_version__ in the plugin module.
PLUGIN_VERSION = _read_version()

# The plugin's description. Can be overridden within OctoPrint's internal
# data via __plugin_description__ in the plugin module.
PLUGIN_DESCRIPTION = "Adds system uptime to the navbar and exposes a small uptime API."

# The plugin's author. Can be overridden within OctoPrint's internal data
# via __plugin_author__ in the plugin module.
PLUGIN_AUTHOR = "Ajimaru"

# The plugin author's email address.
PLUGIN_AUTHOR_EMAIL = "ajimaru_gdr@pm.me"

# The plugin's homepage URL. Can be overridden within OctoPrint's internal
# data via __plugin_url__ in the plugin module.
PLUGIN_URL = "https://github.com/Ajimaru/OctoPrint-Uptime"


# --------------------------------------------------------------------
# More advanced options that you usually shouldn't have to touch follow
# after this point
# --------------------------------------------------------------------

# Additional package data to install for this plugin. The subfolders
# "templates", "static" and "translations" will already be installed
# automatically if they exist. If you add items here, update MANIFEST.in
# so python setup.py sdist produces a source distribution that contains
# all your files (see http://stackoverflow.com/a/14159430/2028598).

PLUGIN_ADDITIONAL_DATA: List[str] = []

# Any additional python packages you need to install with your plugin that
# are not contained in <plugin_package>.*.
PLUGIN_ADDITIONAL_PACKAGES: List[str] = []

# Any python packages within <plugin_package>.* you do NOT want to install
# with your plugin.
PLUGIN_IGNORED_PACKAGES: List[str] = []

# Additional parameters for the call to setuptools.setup.
# If your plugin wants to register additional entry points,
# define dependency links or other things like that; this is
# the place to go. Will be merged recursively with the
# default setup parameters as provided by
# octoprint_setuptools.create_plugin_setup_parameters using
# octoprint.util.dict_merge.
#
# Example:
#     plugin_requires = ["someDependency==dev"]
#     additional_setup_parameters = {
#         "dependency_links": [
#             "https://github.com/someUser/someRepo/archive/master.zip#egg="
#             "someDependency-dev"
#         ]
#     }
# "python_requires": ">=3,<4" blocks installation on Python 2 systems,
# to prevent confused users and provide a helpful error.
# Remove it if you would like to support Python 2 as well as 3
# (not recommended).
additional_setup_parameters = {"python_requires": ">=3.8,<3.14"}

####################################################################

try:
    import importlib

    octoprint_setuptools = importlib.import_module("octoprint_setuptools")
except ImportError as e:
    import sys

    print(
        f"Could not import OctoPrint's setuptools, are you sure you are running that under "
        f"the same python installation that OctoPrint is installed under? Original error: {e}"
    )
    sys.exit(1)

setup_parameters = octoprint_setuptools.create_plugin_setup_parameters(
    identifier=PLUGIN_IDENTIFIER,
    package=PLUGIN_PACKAGE,
    name=PLUGIN_NAME,
    version=PLUGIN_VERSION,
    description=PLUGIN_DESCRIPTION,
    author=PLUGIN_AUTHOR,
    mail=PLUGIN_AUTHOR_EMAIL,
    url=PLUGIN_URL,
    additional_packages=PLUGIN_ADDITIONAL_PACKAGES,
    ignored_packages=PLUGIN_IGNORED_PACKAGES,
    additional_data=PLUGIN_ADDITIONAL_DATA,
)
if len(additional_setup_parameters):
    import types

    try:
        OCTOPRINT_UTIL: Optional[types.ModuleType] = importlib.import_module("octoprint.util")
    except ImportError:
        OCTOPRINT_UTIL = None

    if OCTOPRINT_UTIL and hasattr(OCTOPRINT_UTIL, "dict_merge"):
        dict_merge = getattr(OCTOPRINT_UTIL, "dict_merge")
    else:

        def dict_merge(a, b):
            """Recursively merge two dicts without mutating inputs."""
            result = copy.deepcopy(a)
            for key, value in b.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = dict_merge(result[key], value)
                else:
                    result[key] = copy.deepcopy(value)
            return result

    setup_parameters = dict_merge(setup_parameters, additional_setup_parameters)

setup(**setup_parameters)
