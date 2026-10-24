# -*- coding: utf-8 -*-
"""
Pytest fixtures for Cleep module tests.

Register in an app (or core) conftest.py::

    pytest_plugins = ("cleep.libs.tests.fixtures",)

Or import the fixture module from a local conftest.
"""
import pytest

from cleep.libs.tests.session import TestSession


@pytest.fixture
def cleep_session():
    """
    Yield a TestSession that does not require unittest.TestCase.

    Usage::

        def test_something(cleep_session):
            module = cleep_session.setup(MyApp)
            cleep_session.start_module(module)
            ...
    """
    session = TestSession()
    yield session
    session.clean()
