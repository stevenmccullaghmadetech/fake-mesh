from __future__ import absolute_import
import warnings
from .wsgi_app import FakeMeshApplication


_message = """
This package is no longer actively maintained and no longer fully represents the current state of the MESH api
It's recommended to migrate local MESH testing workloads to https://github.com/NHSDigital/mesh-sandbox
"""

warnings.warn(_message, category=DeprecationWarning, stacklevel=2)
