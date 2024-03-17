from inspect import getdoc, signature, Signature
import logging
import re
from ast import literal_eval
from docstring_parser import parse, DocstringStyle, ParseError

MIN_DESCRIPTION_LEN = 10
LITERAL_BLOCKS_REGEX = r"::\s+(\{(?:(?!::).)*\}|\[(?:(?!::).)*\]|\((?:(?!::).)*\))"
WHITE_SPACES_REGEX = r"(\s{2,}|\t+)"
CUSTOM_TAG = "custom"


class CleepDoc:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_command_doc(self, command):
        """
        Get command documentation

        Args:
            command (method): command as return by getattr function

        Returns:
            dict: documentation ::

                {
                    descriptions: {
                        short (str): short description
                        long (str): long description
                    },
                    args: [
                        {
                            description (str): argument description
                            name (str): argument name
                            type (str): argument type
                            optional (bool): True if parameter is optional, False otherwise
                            default (any): default argument value
                            formats (list): list of data formats
                        },
                        ...
                    ],
                    returns: [
                        {
                            description (str): return description,
                            type (str): return type
                            formats (list): list of data formats
                        },
                        ...
                    ],
                    raises: [
                        {
                            description (str): exception description
                            type (str): exception type
                        },
                        ...
                    ],
                    deprecated (str): Deprecation description if command is deprecated, None otherwise
                }

        Raises:
            Exception: if error occured during command documentation parsing
        """
        parsed_doc = self.__parse_doc(command)

        return {
            "descriptions": {
                "short": parsed_doc.short_description,
                "long": parsed_doc.long_description,
            },
            "args": self.__docstring_params_to_dict(parsed_doc.params),
            "returns": self.__docstring_returns_to_dict(
                parsed_doc.many_returns or parsed_doc.returns
            ),
            "raises": self.__docstring_raises_to_dict(parsed_doc.raises),
            "deprecated": self.__docstring_deprecation_to_dict(parsed_doc.deprecation),
        }

    def is_command_doc_valid(self, command, with_details=False):
        """
        Return command doc validation status

        Args:
            command (function): command as return by getattr function
            with_details (bool): True to return detailed checks (by field). Defaults to False.

        Returns:
            dict: command validation status::

                {
                    valid (bool): True if documentation is valid
                    errors (list): list of found errors
                    warnings (list): list of found warnings
                }

        """
        details = {
            "global": {
                "errors": [],
                "warnings": [],
            },
            "args": {},
            "returns": {},
            "raises": {},
        }
        has_error = False
        errors = []
        warnings = []

        try:
            doc = self.get_command_doc(command)

            self.logger.debug("Found doc: %s", doc)
            command_signature = signature(command)
            command_args = command_signature.parameters

            # descriptions
            if (
                len(doc["descriptions"]["short"] or "") <= MIN_DESCRIPTION_LEN
                and len(doc["descriptions"]["long"] or "") <= MIN_DESCRIPTION_LEN
            ):
                has_error = True
                msg = f"At least one description must be longer than {MIN_DESCRIPTION_LEN} chars"
                details["global"]["errors"].append(msg)
                errors.append(f"[global descriptions] {msg}")

            # args
            if len(doc["args"]) != len(command_args):
                has_error = True
                doc_args = [arg["name"] for arg in doc["args"]]
                msg = f"Command arguments differs from doc {doc_args} and from command declaration {list(command_args.keys())}"
                details["global"]["errors"].append(msg)
                errors.append(f"[global args] {msg}")
            else:
                for arg in doc["args"]:
                    check = self.__check_arg(arg, command_args)
                    arg_name = arg.get("name", "None")
                    details["args"][arg_name] = check
                    if self.__fill_errors_and_warnings(check, f"arg {arg_name}", errors, warnings):
                        has_error = True

            # returns
            for return_ in doc["returns"]:
                check = self.__check_return(return_)
                return_type = return_.get("type", "None")
                details["returns"][return_type] = check
                if self.__fill_errors_and_warnings(check, f"return {return_type}", errors, warnings):
                    has_error = True

            # raises
            for raise_ in doc["raises"]:
                check = self.__check_raise(raise_)
                raise_type = raise_.get("type", "None")
                details["raises"][raise_type] = check
                if self.__fill_errors_and_warnings(check, f"raise {raise_type}", errors, warnings):
                    has_error = True

        except Exception as error:
            self.logger.exception("Error occured during doc parsing")
            has_error = True
            msg = f"Error parsing documentation: {str(error)}"
            details["global"]["errors"].append(msg)
            errors.append(f"[global] {msg}")

        out = {
            "valid": not has_error,
            "errors": errors,
            "warnings": warnings,
        }
        if with_details:
            out["details"] = details
        return out

    def __fill_errors_and_warnings(self, check_result, check_type, errors, warnings):
        """
        Fill errors and warnings list with check results

        Args:
            check_result (dict): result of check function
            check_type (str): must be one of 'arg', 'return', 'raise'
            errors (list): list of errors to fill
            warnings (list): list of warnings to fill

        Returns:
            bool: True if errors found in check results
        """
        has_error = False

        for error in check_result.get("errors", []):
            has_error = True
            errors.append(f"[{check_type}] {error}")

        for warning in check_result.get("warnings", []):
            warnings.append(f"[{check_type}] {warning}")

        return has_error

    def __check_arg(self, doc_arg, command_args):
        """
        Check documentation argument

        Args:
            doc_arg (dict): argument data from parsed doc
            command_args (list): list of arguments from command signature

        Returns:
            dict: dict of arg with errors or warnings::

                {
                    errors: [],
                    warnings: [],
                }

        """
        self.logger.debug("Check arg: %s", doc_arg)
        errors = []
        warnings = []

        # check arg exist in signature
        if doc_arg["name"] not in command_args:
            errors.append("This argument does not exist in command signature")

        # check type
        if CUSTOM_TAG in doc_arg["type"]:
            warnings.append(
                "It is not adviced to use custom types. Prefer using built-in ones (int, float, bool, str, tuple, dict, list)"
            )
        if doc_arg["type"] == "None":
            errors.append("Argument type is missing")

        # check description
        if len(doc_arg["description"]) == 0:
            errors.append("Argument description is missing")

        # check default value
        doc_def = doc_arg["default"]
        func_def = (
            command_args.get(doc_arg["name"]) and command_args[doc_arg["name"]].default
        )
        self.logger.debug(
            "Default value from doc=%s[%s], from function=%s[%s]",
            doc_def,
            type(doc_def),
            func_def,
            type(func_def),
        )
        if (
            doc_arg["name"] in command_args
            and func_def != Signature.empty
            and func_def != doc_def
        ):
            errors.append(
                f"Default value differs: from doc {doc_def}, from function {func_def}. See https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html"
            )

        # check optional flag
        if (
            doc_arg["name"] in command_args
            and func_def != Signature.empty
            and doc_arg["optional"] in (None, False)
        ):
            errors.append(
                "Optional flag is missing in arg documentation. See https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html"
            )

        # check formats
        if len(doc_arg["formats"]) > 1:
            warnings.append(
                "It's not adviced to publish more than one format for an argument"
            )
        if (
            doc_arg["type"] in ("tuple", "dict", "list")
            and len(doc_arg["formats"]) == 0
        ):
            errors.append(
                f"It's mandatory to explain {doc_arg['type']} content for complex argument"
            )
        if (
            doc_arg["type"] in ("int", "float", "bool", "str")
            and len(doc_arg["formats"]) != 0
        ):
            errors.append(
                f"Simple argument of type {doc_arg['type']} should not be explained"
            )

        return {
            "errors": errors,
            "warnings": warnings,
        }


    def __check_return(self, doc_return):
        """
        Check documentation return

        Args:
            doc_return (dict): return data from parsed doc

        Returns:
            dict: dict of arg with errors or warnings::

                {
                    errors: [],
                    warnings: [],
                }

        """
        self.logger.debug("Check return: %s", doc_return)
        errors = []
        warnings = []

        # check type
        if doc_return["type"] in ("None", None):
            errors.append(
                "Return type is mandatory. Please specify one"
            )
        if CUSTOM_TAG in doc_return["type"]:
            warnings.append(
                "It is not adviced to use custom type. Prefer using built-in ones (int, float, bool, str, tuple, dict, list)"
            )

        # check description
        if len(doc_return["description"]) == 0:
            errors.append(
                "Return description is missing"
            )

        # check formats
        if len(doc_return["formats"]) > 1:
            warnings.append(
                "It's not adviced to publish more than one format for a returned value"
            )
        if (
            doc_return["type"] in ("tuple", "dict", "list")
            and len(doc_return["formats"]) == 0
        ):
            errors.append(
                f"It's mandatory to explain {doc_return['type']} content for complex returned data"
            )
        if (
            doc_return["type"] in ("int", "float", "bool", "str")
            and len(doc_return["formats"]) != 0
        ):
            errors.append(
                f"Simple returned data of type {doc_return['type']} should not be explained"
            )

        return {
            "errors": errors,
            "warnings": warnings,
        }

    def __check_raise(self, doc_raise):
        """
        Check documentation raises

        Args:
            doc_raise (dict): raise data from parsed doc

        Returns:
            dict: dict of arg with errors or warnings::

                {
                    errors: [],
                    warnings: [],
                }

        """
        self.logger.debug("Check raise: %s", doc_raise)
        errors = []
        warnings = []

        # check description
        if len(doc_raise["description"]) == 0:
            errors.append("Raise description is missing")

        return {
            "errors": errors,
            "warnings": warnings,
        }

    def __parse_doc(self, command):
        """
        Parse documentation from specified command

        Args:
            command (method): command as return by getattr function

        Returns:
            Docstring: command docstring
        """
        raw_doc = getdoc(command)
        if raw_doc is None or len(raw_doc.strip()) == 0:
            raise Exception("There is no documentation for command '%s'" % command.__name__)

        try:
            parsed_doc = parse(raw_doc, style=DocstringStyle.GOOGLE)
            self.logger.debug("Docstring style: %s", parsed_doc.style)
            if parsed_doc.style != DocstringStyle.GOOGLE:  # pragma: no cover
                raise Exception("Only Google style docstring is supported")
        except ParseError as error:
            raise Exception(
                f"Invalid '{command.__name__}' documentation content"
            ) from error

        return parsed_doc

    def __docstring_returns_to_dict(self, docstring_returns):
        """
        Transform returns docstring to dict

        Args:
            docstring_returns (list): docstring

        Returns:
            list: dosctring under list of dict::

                [
                    {
                        description (str): return description
                        formats (list): list of literals under str
                        type (type): type of return
                    },
                    ...
                ]

        """
        returns = []
        for docstring_return in docstring_returns or []:
            (literals, description) = self.__get_literal_blocks(docstring_return.description)

            returns.append(
                {
                    "description": CleepDoc.clean_description(description),
                    "formats": literals,
                    "type": CleepDoc.str_to_type(docstring_return.type_name),
                }
            )

        return returns

    def __docstring_params_to_dict(self, docstring_params):
        """
        Transform params docstring to dict

        Args:
            docstring_params (list): docstring

        Returns:
            list: dosctring under list of dict::

                [
                    {
                        description (str): param description
                        name (str): param name
                        formats (list): list of literals under str
                        type (type): type of return
                        optional (bool): True if param is optional
                        default (any): default param value
                    },
                    ...
                ]

        """
        params = []
        for docstring_param in docstring_params or []:
            (literals, description) = self.__get_literal_blocks(docstring_param.description)

            params.append(
                {
                    "description": CleepDoc.clean_description(description),
                    "name": docstring_param.arg_name.strip(),
                    "type": CleepDoc.str_to_type(docstring_param.type_name),
                    "optional": docstring_param.is_optional,
                    "default": self.__eval_string(docstring_param.default),
                    "formats": literals,
                }
            )

        return params

    def __docstring_raises_to_dict(self, docstring_raises):
        """
        Transform raises docstring to dict

        Args:
            docstring_raises (list): docstring

        Returns:
            list: dosctring under list of dict::

                [
                    {
                        description (str): raise description
                        type (type): type of raise
                    },
                    ...
                ]

        """
        raises = []
        for docstring_raise in docstring_raises or []:
            raises.append(
                {
                    "description": CleepDoc.clean_description(docstring_raise.description),
                    "type": CleepDoc.str_to_type(docstring_raise.type_name),
                }
            )

        return raises

    def __docstring_deprecation_to_dict(self, docstring_deprecation):
        """
        Transform deprecation docstring to dict

        Args:
            docstring_deprecation (str): docstring

        Returns:
            str: dosctring under str or None if no deprecation
        """
        if docstring_deprecation is None:
            return None

        return docstring_deprecation.description.strip()

    @staticmethod
    def str_to_type(type_str):
        """
        Get real type from string

        Args:
            type_str (str): type under string format

        Returns:
            any: real type according to input string
        """
        def is_builtin_class(exp):
            try:
                eval(exp)
                return True
            except Exception:
                return False

        if type_str is None:
            return "None"
        type_lower = type_str.lower()
        if type_lower in ("str", "string"):
            return str.__name__
        if type_lower in ("bool", "boolean"):
            return bool.__name__
        if type_lower == "float":
            return float.__name__
        if type_lower in ("number", "int"):
            return int.__name__
        if type_lower == "dict":
            return dict.__name__
        if type_lower in ("list", "array"):
            return list.__name__
        if type_lower == "tuple":
            return tuple.__name__
        if type_str == "Exception":
            return Exception.__name__
        if is_builtin_class(type_str):
            return type_str

        return f"{CUSTOM_TAG}<{type_str}>"

    def __eval_string(self, value):
        """
        Eval specified value and returned evaluated value if possible.
        Return specified value if error occured

        Args:
            value (any): value to evaluate

        Returns:
            any: value of evaluated type
        """
        try:
            return literal_eval(value)
        except Exception:
            return value

    def __get_literal_blocks(self, string):
        """
        Get literal blocks from specified string and remove them from input string

        Args:
            string (str): string to search literals on

        Returns:
            tuple: found literals and string without literals::

                (str, str)

        """
        literal_blocks = []

        matches = re.findall(LITERAL_BLOCKS_REGEX, string, re.DOTALL)
        self.logger.debug("Literal matches for '%s': %s", string, matches)
        for match in matches:
            string = string.replace(match, "")
            literal = match.strip().replace("\n", "")
            literal = re.sub(WHITE_SPACES_REGEX, "", literal)
            literal_blocks.append(literal)

        return (literal_blocks, string)

    @staticmethod
    def clean_description(description):
        """
        Clean description removing consecutive carriage returns, :: dots from literals and
        replacing single carriage return with space

        Args:
            description: string to clean

        Returns:
            str: updated description
        """
        return re.sub(r"\n(?=\n)|::", "", description).replace("\n", " ").strip()
