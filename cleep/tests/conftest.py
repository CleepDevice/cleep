# -*- coding: utf-8 -*-
"""Core test fixtures (TestSession available as ``cleep_session``)."""
import warnings

import pytest

pytest_plugins = ("cleep.libs.tests.fixtures",)


def pytest_configure(config):
    # Register here so functional marks work even if repo-root pytest.ini is stale
    # (coresync does not update pytest.ini; it only syncs the cleep/ package).
    config.addinivalue_line(
        "markers",
        "functional: real OS binary tests (CLEEP_FUNCTIONAL_TESTS / coretests --functional)",
    )
    # Third-party: passlib still imports its deprecated pbkdf2 shim
    warnings.filterwarnings(
        "ignore",
        message=r"the module 'passlib\.utils\.pbkdf2' is deprecated",
        category=DeprecationWarning,
    )
