#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace("tests/", ""))
from cleepdoc import CleepDoc
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from unittest.mock import Mock
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


class DummyApp:
    def command_without_doc(self):
        pass

    def command_with_arg(self, arg1):
        """
        Command with argument

        Args:
            arg1 (str): first arg
        """
        pass

    def command_with_returns(self):
        """
        Command with returns

        Returns:
            bool: True if ok, False otherwise
        """
        pass

    def command_with_raises(self):
        """
        Command with raises

        Raises:
            Exception: if error occured
        """
        pass

    def command_with_deprecation(self):
        """
        Command with deprecation

        Deprecated:
            deprecated function in favor of another one
        """
        pass

    def command_with_everything(self, arg1, arg2):
        """
        Command with everything

        Args:
            arg1 (str): first arg. Default to "a value".
            arg2 (bool): second arg

        Returns:
            str: a string is returned

        Deprecated:
            This function is deprecated

        Raises:
            CustomException: if error occured
        """
        pass

    def command_with_descriptions(self):
        """
        This is a short description

        And this is the long description
        on multiple lines
        """
        pass

    def command_without_descriptions(self, param):
        """
        Args:
            param (int) param
        """

    def command_with_too_short_description(self):
        """Too short"""
        pass

    def command_google(self):
        """This is an example of a module level function.

        Function parameters should be documented in the ``Args`` section. The name
        of each parameter is required. The type and description of each parameter
        is optional, but should be included if not obvious.

        If ``*args`` or ``**kwargs`` are accepted,
        they should be listed as ``*args`` and ``**kwargs``.

        The format for a parameter is::

            name (type): description
                The description may span multiple lines. Following
                lines should be indented. The "(type)" is optional.

                Multiple paragraphs are supported in parameter
                descriptions.

        Args:
            param1 (int): The first parameter.
            param2 (str, optional): The second parameter. Defaults to None.
                Second line of description should be indented.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            bool: True if successful, False otherwise.

            The return type is optional and may be specified at the beginning of
            the ``Returns`` section followed by a colon.

            The ``Returns`` section may span multiple lines and paragraphs.
            Following lines should be indented to match the first line.

            The ``Returns`` section supports any reStructuredText formatting,
            including literal blocks::

                {
                    'param1': param1,
                    'param2': param2,
                    "param3": param3
                }

        Raises:
            AttributeError: The ``Raises`` section is a list of all exceptions
                that are relevant to the interface.
            ValueError: If `param2` is equal to `param1`.
        """
        pass

    def command_args_differ(self):
        """
        Short description

        Args:
            param1 (str): missing param
        """
        pass

    def command_arg_unknown(self, param2):
        """
        Short description

        Args:
            param1 (str): missing param
        """
        pass

    def command_arg_custom_type(self, param):
        """
        Short description

        Args:
            param (MyType): custom type param
        """
        pass

    def command_arg_no_description(self, param):
        """
        Short description

        Args:
            param (str):
        """
        pass

    def command_arg_default_value(self, param=123):
        """
        Short description

        Args:
            param (int, optional): param with default value. Defaults to hello.
        """
        pass

    def command_arg_optional(self, param=123):
        """
        Short description

        Args:
            param (int): param with default value. Defaults to 123.
        """
        pass

    def command_arg_multiple_formats(self, param):
        """
        Short description

        Args:
            param (dict): param with specific format::

                {
                    value (str): a value
                }

                or another specific format::

                {
                    another (int): another value
                }

        """
        pass

    def command_arg_missing_formats(self, param1, param2, param3, param4):
        """
        Short description

        Args:
            param1 (dict): complex param
            param2 (list): complex param
            param3 (int): simple param
            param4 (tuple): complex param
        """
        pass

    def command_arg_unnecessary_formats(
        self, param1, param2, param3, param4, param5, param6
    ):
        """
        Short description

        Args:
            param1 (str): simple param::

                {
                    value (str): a value
                }

            param2 (int): simple param::

                {
                    value (str): a value
                }

            param3 (float): simple param::

                {
                    value (str): a value
                }

            param4 (string): simple param::

                {
                    value (str): a value
                }

            param5 (str): simple param::

                {
                    value (str): a value
                }

            param6 (bool): simple param::

                {
                    value (str): a value
                }

        """
        pass

    def command_return_custom_type(self):
        """
        Short description

        Returns:
            MyType: my custom return type
        """
        pass

    def command_return_missing_type(self):
        """
        Short description

        Returns:
            Missing return type
        """
        pass

    def command_return_no_description(self):
        """
        Short description

        Returns:
            int:
        """
        pass

    def command_return_multiple_formats(self):
        """
        Short description

        Returns:
            tuple: first output::

                (str, str)

                second output::

                (str, str, str)

        """
        pass

    def command_return_no_format_for_tuple(self):
        """
        Short description

        Returns:
            tuple: first output
        """
        pass

    def command_return_no_format_for_dict(self):
        """
        Short description

        Returns:
            dict: first output
        """
        pass

    def command_return_no_format_for_list(self):
        """
        Short description

        Returns:
            list: first output
        """
        pass

    def command_return_no_format_for_int(self):
        """
        Short description

        Returns:
            int: first output
        """
        pass

    def command_return_no_format_for_str(self):
        """
        Short description

        Returns:
            int: first output
        """
        pass

    def command_return_no_format_for_bool(self):
        """
        Short description

        Returns:
            bool: first output
        """
        pass

    def command_return_format_for_bool(self):
        """
        Short description

        Returns:
            bool: first output::

                {
                    data (str): some data
                }

        """
        pass

    def command_raises(self):
        """
        Short description

        Raises:
            Exception: an exception
        """
        pass

    def command_raises_custom_type(self):
        """
        Short description

        Raises:
            CustomException: a custom exception
        """
        pass

    def command_raises_no_description(self):
        """
        Short description

        Raises:
            Exception: 
        """
        pass


class CleepDocTests(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(
            level=LOG_LEVEL,
            format=u"%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
        )

        self.cd = CleepDoc()
        self.dummy = DummyApp()

        self.maxDiff = None

    def test_get_command_doc_without_arg(self):
        cmd = getattr(self.dummy, "command_without_doc")

        with self.assertRaises(Exception) as cm:
            self.cd.get_command_doc(cmd)

        self.assertEqual(str(cm.exception), "Documentation must be provided")

    def test_get_command_doc_with_arg(self):
        cmd = getattr(self.dummy, "command_with_arg")

        doc = self.cd.get_command_doc(cmd)
        logging.debug("Doc: %s", doc)

        self.assertDictEqual(
            doc,
            {
                "descriptions": {"long": None, "short": "Command with argument"},
                "args": [
                    {
                        "description": "first arg",
                        "name": "arg1",
                        "type": "str",
                        "optional": False,
                        "default": None,
                        "formats": [],
                    }
                ],
                "returns": [],
                "raises": [],
                "deprecated": None,
            },
        )

    def test_get_command_doc_with_returns(self):
        cmd = getattr(self.dummy, "command_with_returns")

        doc = self.cd.get_command_doc(cmd)
        logging.debug("Doc: %s", doc)

        self.assertDictEqual(
            doc,
            {
                "descriptions": {"long": None, "short": "Command with returns"},
                "args": [],
                "returns": [
                    {
                        "description": "True if ok, False otherwise",
                        "type": "bool",
                        "formats": [],
                    }
                ],
                "raises": [],
                "deprecated": None,
            },
        )

    def test_get_command_doc_with_raises(self):
        cmd = getattr(self.dummy, "command_with_raises")

        doc = self.cd.get_command_doc(cmd)
        logging.debug("Doc: %s", doc)

        self.assertDictEqual(
            doc,
            {
                "descriptions": {"long": None, "short": "Command with raises"},
                "args": [],
                "deprecated": None,
                "raises": [{"description": "if error occured", "type": "Exception"}],
                "returns": [],
            },
        )

    def test_get_command_doc_with_deprecation(self):
        cmd = getattr(self.dummy, "command_with_deprecation")

        doc = self.cd.get_command_doc(cmd)
        logging.debug("Doc: %s", doc)

        self.assertDictEqual(
            doc,
            {
                "descriptions": {"long": None, "short": "Command with deprecation"},
                "args": [],
                "returns": [],
                "raises": [],
                "deprecated": "deprecated function in favor of another one",
            },
        )

    def test_get_command_doc_with_everything(self):
        cmd = getattr(self.dummy, "command_with_everything")

        doc = self.cd.get_command_doc(cmd)
        logging.debug("Doc: %s", doc)

        self.assertDictEqual(
            doc,
            {
                "descriptions": {"long": None, "short": "Command with everything"},
                "args": [
                    {
                        "name": "arg1",
                        "default": None,
                        "description": 'first arg. Default to "a value".',
                        "optional": False,
                        "type": "str",
                        "formats": [],
                    },
                    {
                        "name": "arg2",
                        "default": None,
                        "description": "second arg",
                        "optional": False,
                        "type": "bool",
                        "formats": [],
                    },
                ],
                "deprecated": "This function is deprecated",
                "raises": [
                    {
                        "description": "if error occured",
                        "type": "custom<CustomException>",
                    }
                ],
                "returns": [
                    {
                        "description": "a string is returned",
                        "type": "str",
                        "formats": [],
                    }
                ],
            },
        )

    def test_get_command_doc_with_descriptions(self):
        cmd = getattr(self.dummy, "command_with_descriptions")

        doc = self.cd.get_command_doc(cmd)
        logging.debug("Doc: %s", doc)

        self.assertDictEqual(
            doc,
            {
                "args": [],
                "deprecated": None,
                "descriptions": {
                    "long": "And this is the long description\non multiple lines",
                    "short": "This is a short description",
                },
                "raises": [],
                "returns": [],
            },
        )

    def test_get_command_doc_google(self):
        cmd = getattr(self.dummy, "command_google")

        doc = self.cd.get_command_doc(cmd)
        logging.debug("Doc: %s", doc)

        self.assertDictEqual(
            doc,
            {
                "descriptions": {
                    "short": "This is an example of a module level function.",
                    "long": 'Function parameters should be documented in the ``Args`` section. The name\nof each parameter is required. The type and description of each parameter\nis optional, but should be included if not obvious.\n\nIf ``*args`` or ``**kwargs`` are accepted,\nthey should be listed as ``*args`` and ``**kwargs``.\n\nThe format for a parameter is::\n\n    name (type): description\n        The description may span multiple lines. Following\n        lines should be indented. The "(type)" is optional.\n\n        Multiple paragraphs are supported in parameter\n        descriptions.',
                },
                "args": [
                    {
                        "description": "The first parameter.",
                        "name": "param1",
                        "type": "int",
                        "optional": False,
                        "default": None,
                        "formats": [],
                    },
                    {
                        "description": "The second parameter. Defaults to None.\nSecond line of description should be indented.",
                        "name": "param2",
                        "type": "str",
                        "optional": True,
                        "default": None,
                        "formats": [],
                    },
                    {
                        "description": "Variable length argument list.",
                        "name": "*args",
                        "type": "None",
                        "optional": None,
                        "default": None,
                        "formats": [],
                    },
                    {
                        "description": "Arbitrary keyword arguments.",
                        "name": "**kwargs",
                        "type": "None",
                        "optional": None,
                        "default": None,
                        "formats": [],
                    },
                ],
                "returns": [
                    {
                        "description": "True if successful, False otherwise.\nThe return type is optional and may be specified at the beginning of\nthe ``Returns`` section followed by a colon.\n\nThe ``Returns`` section may span multiple lines and paragraphs.\nFollowing lines should be indented to match the first line.\n\nThe ``Returns`` section supports any reStructuredText formatting,\nincluding literal blocks::\n\n    {\n        'param1': param1,\n        'param2': param2,\n        \"param3\": param3\n    }",
                        "formats": [
                            "{'param1': param1,'param2': param2,\"param3\": param3}"
                        ],
                        "type": "bool",
                    }
                ],
                "raises": [
                    {
                        "description": "The ``Raises`` section is a list of all exceptions\nthat are relevant to the interface.",
                        "type": "AttributeError",
                    },
                    {
                        "description": "If `param2` is equal to `param1`.",
                        "type": "ValueError",
                    },
                ],
                "deprecated": None,
            },
        )

    def test_is_command_doc_valid_with_too_short_description(self):
        cmd = getattr(self.dummy, "command_with_too_short_description")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "valid": False,
                "errors": [
                    "[descriptions] At least one description must be longer than 10 chars",
                ],
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_without_descriptions(self):
        cmd = getattr(self.dummy, "command_without_descriptions")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "valid": False,
                "errors": [
                    "[doc] Error parsing documentation: Invalid 'command_without_descriptions' documentation content",
                ],
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_with_arg(self):
        cmd = getattr(self.dummy, "command_with_arg")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(valid, {"valid": True, "errors": [], "warnings": []})

    def test_is_command_doc_valid_with_returns(self):
        cmd = getattr(self.dummy, "command_with_returns")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(valid, {"valid": True, "errors": [], "warnings": []})

    def test_is_command_doc_valid_with_raises(self):
        cmd = getattr(self.dummy, "command_with_raises")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(valid, {"valid": True, "errors": [], "warnings": []})

    def test_is_command_doc_valid_with_deprecation(self):
        cmd = getattr(self.dummy, "command_with_deprecation")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(valid, {"valid": True, "errors": [], "warnings": []})

    def test_is_command_doc_valid_with_everything(self):
        cmd = getattr(self.dummy, "command_with_everything")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "valid": True,
                "errors": [],
                "warnings": [
                    "[raise custom<CustomException>] It is not adviced to use custom type. Prefer using built-in ones (int, float, bool, str, tuple, dict, list)"
                ],
            },
        )

    def test_is_command_doc_valid_google(self):
        cmd = getattr(self.dummy, "command_google")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [
                    "[args] Command arguments differ from declaration (from doc ['param1', 'param2', '*args', '**kwargs'], from command [])",
                    "[return bool] Simple returned data of type bool should not be explained",
                ],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_args_differ(self):
        cmd = getattr(self.dummy, "command_args_differ")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [
                    "[args] Command arguments differ from declaration (from doc ['param1'], from command [])"
                ],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_arg_unknown(self):
        cmd = getattr(self.dummy, "command_arg_unknown")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [
                    "[arg param1] This argument does not exist in command signature"
                ],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_arg_custom_type(self):
        cmd = getattr(self.dummy, "command_arg_custom_type")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [],
                "valid": True,
                "warnings": [
                    "[arg param] It is not adviced to use custom types. Prefer using built-in ones (int, float, bool, str, tuple, dict, list)"
                ],
            },
        )

    def test_is_command_doc_valid_arg_no_description(self):
        cmd = getattr(self.dummy, "command_arg_no_description")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": ["[arg param] Argument description is missing"],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_arg_default_value(self):
        cmd = getattr(self.dummy, "command_arg_default_value")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [
                    "[arg param] Default value differs (from doc hello, from function 123)",
                ],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_arg_optional(self):
        cmd = getattr(self.dummy, "command_arg_optional")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [
                    "[arg param] Optional flag is missing in arg documentation",
                ],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_arg_multiple_formats(self):
        cmd = getattr(self.dummy, "command_arg_multiple_formats")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [],
                "valid": True,
                "warnings": [
                    "[arg param] It's not adviced to publish more than one format for an argument"
                ],
            },
        )

    def test_is_command_doc_valid_arg_missing_formats(self):
        cmd = getattr(self.dummy, "command_arg_missing_formats")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [
                    "[arg param1] It's mandatory to explain dict content for complex argument",
                    "[arg param2] It's mandatory to explain list content for complex argument",
                    "[arg param4] It's mandatory to explain tuple content for complex argument",
                ],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_arg_unnecessary_formats(self):
        cmd = getattr(self.dummy, "command_arg_unnecessary_formats")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [
                    "[arg param1] Simple argument of type str should not be explained",
                    "[arg param2] Simple argument of type int should not be explained",
                    "[arg param3] Simple argument of type float should not be explained",
                    "[arg param4] Simple argument of type str should not be explained",
                    "[arg param5] Simple argument of type str should not be explained",
                    "[arg param6] Simple argument of type bool should not be explained",
                ],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_return_custom_type(self):
        cmd = getattr(self.dummy, "command_return_custom_type")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [],
                "valid": True,
                "warnings": [
                    "[return custom<MyType>] It is not adviced to use custom type. Prefer using built-in ones (int, float, bool, str, tuple, dict, list)"
                ],
            },
        )

    def test_is_command_doc_valid_return_missing_type(self):
        cmd = getattr(self.dummy, "command_return_missing_type")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [
                    "[return None] Return type is mandatory. Please specify one"
                ],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_return_no_description(self):
        cmd = getattr(self.dummy, "command_return_no_description")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [
                    "[return int] Return description is missing",
                ],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_return_multiple_formats(self):
        cmd = getattr(self.dummy, "command_return_multiple_formats")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [],
                "valid": True,
                "warnings": [
                    "[arg tuple] It's not adviced to publish more than one format for a returned value",
                ],
            },
        )

    def test_is_command_doc_valid_return_no_format_for_tuple(self):
        cmd = getattr(self.dummy, "command_return_no_format_for_tuple")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [
                    "[return tuple] It's mandatory to explain tuple content for complex returned data",
                ],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_return_no_format_for_dict(self):
        cmd = getattr(self.dummy, "command_return_no_format_for_dict")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [
                    "[return dict] It's mandatory to explain dict content for complex returned data",
                ],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_return_no_format_for_list(self):
        cmd = getattr(self.dummy, "command_return_no_format_for_list")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [
                    "[return list] It's mandatory to explain list content for complex returned data",
                ],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_return_no_format_for_int(self):
        cmd = getattr(self.dummy, "command_return_no_format_for_int")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [],
                "valid": True,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_return_no_format_for_str(self):
        cmd = getattr(self.dummy, "command_return_no_format_for_str")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [],
                "valid": True,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_return_no_format_for_bool(self):
        cmd = getattr(self.dummy, "command_return_no_format_for_bool")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [],
                "valid": True,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_return_format_for_bool(self):
        cmd = getattr(self.dummy, "command_return_format_for_bool")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "errors": [
                    "[return bool] Simple returned data of type bool should not be explained",
                ],
                "valid": False,
                "warnings": [],
            },
        )

    def test_is_command_doc_valid_raises(self):
        cmd = getattr(self.dummy, "command_raises")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(valid, {"valid": True, "errors": [], "warnings": []})

    def test_is_command_doc_valid_raises_custom_type(self):
        cmd = getattr(self.dummy, "command_raises_custom_type")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(
            valid,
            {
                "valid": True,
                "errors": [],
                "warnings": [
                    "[raise custom<CustomException>] It is not adviced to use custom type. Prefer using built-in ones (int, float, bool, str, tuple, dict, list)"
                ],
            },
        )

    def test_is_command_doc_valid_raises_no_description(self):
        cmd = getattr(self.dummy, "command_raises_no_description")

        valid = self.cd.is_command_doc_valid(cmd)
        logging.debug("Result: %s", valid)

        self.assertDictEqual(valid, {
            "valid": False,
            "errors": ["[raise Exception] Raise description is missing"],
            "warnings": []
        })


if __name__ == "__main__":
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_cleepdoc.py; coverage report -m -i
    unittest.main()
