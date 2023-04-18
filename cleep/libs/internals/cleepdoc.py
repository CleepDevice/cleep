from inspect import getdoc, signature, Signature
import logging
import re
from ast import literal_eval
from docstring_parser import parse, DocstringStyle, ParseError

MIN_DESCRIPTION_LEN = 10
LITERAL_BLOCKS_REGEX = r"::\s+(\{[^\}\{]*\}|\([^\)\(]*\))|(\[[^\]\[]*\])"
WHITE_SPACES_REGEX = r"(\s{2,}|\t+)"
CUSTOM_TAG = "custom"


class CleepDoc:
    def __init__(self):
        # set logger
        self.logger = logging.getLogger(self.__class__.__name__)

        # patterns

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

    def is_command_doc_valid(self, command):
        """
        Return command doc validation status

        Args:
            command (method): command as return by getattr function

        Returns:
            dict: command validation status::

                {
                    valid (bool): True if documentation is valid
                    errors (list): list of found errors
                    warnings (list): list of found warnings
                }

        """
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
                errors.append(
                    f"[descriptions] At least one description must be longer than {MIN_DESCRIPTION_LEN} chars"
                )

            # args
            if len(doc["args"]) != len(command_args):
                doc_args = [arg["name"] for arg in doc["args"]]
                errors.append(
                    f"[args] Command arguments differ from declaration (from doc {doc_args}, from command {list(command_args.keys())})"
                )
            else:
                for arg in doc["args"]:
                    self.__check_arg(arg, command_args, errors, warnings)

            # returns
            for return_ in doc["returns"]:
                self.__check_return(return_, errors, warnings)

            # raises
            for raise_ in doc["raises"]:
                self.__check_raise(raise_, errors, warnings)

        except Exception as error:
            errors.append(f"[doc] Error parsing documentation: {str(error)}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def __check_arg(self, doc_arg, command_args, errors, warnings):
        """
        Check documentation argument

        Args:
            doc_arg (dict): argument data from parsed doc
            command_args (list): list of arguments from command signature
            errors (list): list of analyze errors
            warnings (list): list of analyze warnings
        """
        self.logger.debug("Check arg: %s", doc_arg)
        # check arg exist in signature
        if doc_arg["name"] not in command_args:
            errors.append(
                f"[arg {doc_arg['name']}] This argument does not exist in command signature"
            )

        # check type
        if CUSTOM_TAG in doc_arg["type"]:
            warnings.append(
                f"[arg {doc_arg['name']}] It is not adviced to use custom types. Prefer using built-in ones (int, float, bool, str, tuple, dict, list)"
            )

        # check description
        if len(doc_arg["description"]) == 0:
            errors.append(f"[arg {doc_arg['name']}] Argument description is missing")

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
                f"[arg {doc_arg['name']}] Default value differs (from doc {doc_def}, from function {func_def})"
            )

        # check is optional flag
        if (
            doc_arg["name"] in command_args
            and func_def != Signature.empty
            and doc_arg["optional"] in (None, False)
        ):
            errors.append(
                f"[arg {doc_arg['name']}] Optional flag is missing in arg documentation"
            )

        # check formats
        if len(doc_arg["formats"]) > 1:
            warnings.append(
                f"[arg {doc_arg['name']}] It's not adviced to publish more than one format for an argument"
            )
        if (
            doc_arg["type"] in ("tuple", "dict", "list")
            and len(doc_arg["formats"]) == 0
        ):
            errors.append(
                f"[arg {doc_arg['name']}] It's mandatory to explain {doc_arg['type']} content for complex argument"
            )
        if (
            doc_arg["type"] in ("int", "float", "bool", "str")
            and len(doc_arg["formats"]) != 0
        ):
            errors.append(
                f"[arg {doc_arg['name']}] Simple argument of type {doc_arg['type']} should not be explained"
            )

    def __check_return(self, doc_return, errors, warnings):
        """
        Check documentation return

        Args:
            doc_return (dict): return data from parsed doc
            errors (list): list of analyze errors
            warnings (list): list of analyze warnings
        """
        self.logger.debug("Check return: %s", doc_return)
        # check type
        if doc_return["type"] in ("None", None):
            errors.append(
                f"[return {doc_return['type']}] Return type is mandatory. Please specify one"
            )
        if CUSTOM_TAG in doc_return["type"]:
            warnings.append(
                f"[return {doc_return['type']}] It is not adviced to use custom type. Prefer using built-in ones (int, float, bool, str, tuple, dict, list)"
            )

        # check description
        if len(doc_return["description"]) == 0:
            errors.append(
                f"[return {doc_return['type']}] Return description is missing"
            )

        # check formats
        if len(doc_return["formats"]) > 1:
            warnings.append(
                f"[arg {doc_return['type']}] It's not adviced to publish more than one format for a returned value"
            )
        if (
            doc_return["type"] in ("tuple", "dict", "list")
            and len(doc_return["formats"]) == 0
        ):
            errors.append(
                f"[return {doc_return['type']}] It's mandatory to explain {doc_return['type']} content for complex returned data"
            )
        if (
            doc_return["type"] in ("int", "float", "bool", "str")
            and len(doc_return["formats"]) != 0
        ):
            errors.append(
                f"[return {doc_return['type']}] Simple returned data of type {doc_return['type']} should not be explained"
            )

    def __check_raise(self, doc_raise, errors, warnings):
        """
        Check documentation raises

        Args:
            doc_raise (dict): raise data from parsed doc
            errors (list): list of analyze errors
            warnings (list): list of analyze warnings
        """
        self.logger.debug("Check raise: %s", doc_raise)
        # check type
        if CUSTOM_TAG in doc_raise["type"]:
            warnings.append(
                f"[raise {doc_raise['type']}] It is not adviced to use custom type. Prefer using built-in ones (int, float, bool, str, tuple, dict, list)"
            )

        # check description
        if len(doc_raise["description"]) == 0:
            errors.append(f"[raise {doc_raise['type']}] Raise description is missing")

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
            raise Exception("Documentation must be provided")

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
            literals = self.__get_literal_blocks(docstring_return.description)

            returns.append(
                {
                    # "args": docstring_return.args,
                    "description": docstring_return.description.strip(),
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
            literals = self.__get_literal_blocks(docstring_param.description)

            params.append(
                {
                    # "args": docstring_param.args,
                    "description": docstring_param.description.strip(),
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
                    # "args": docstring_raise.args,
                    "description": docstring_raise.description.strip(),
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
            except Exception as e:
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
        Get literal blocks from specified string

        Args:
            string (str): string to search literals on
        """
        literal_blocks = []

        matches = re.findall(LITERAL_BLOCKS_REGEX, string)  # , re.DOTALL)
        self.logger.debug("Literal matches for '%s': %s", string, matches)
        for match in matches:
            match = list(filter(None, match))[0]
            literal = match.strip().replace("\n", "")
            literal = re.sub(WHITE_SPACES_REGEX, "", literal)
            literal_blocks.append(literal)

        return literal_blocks
