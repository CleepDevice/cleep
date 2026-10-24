#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Core implements all kind of cleep modules/apps
"""

import logging
import os
import copy
import uuid
import time
from threading import Lock
from unittest.mock import Mock
from cleep.bus import BusClient
from cleep.exception import InvalidParameter, MissingParameter
from cleep.common import ExecutionStep, CORE_MODULES, MessageResponse, RENDERERS
from cleep.libs.internals.crashreport import CrashReport
from cleep.libs.drivers.driver import Driver
from cleep.libs.internals.cleepdoc import CleepDoc

__all__ = [
    "Cleep",
    "CleepRpcWrapper",
    "CleepModule",
    "CleepRemoteAccessModule",
    "CleepResources",
    "CleepRenderer",
    "CleepExternalBus",
]


class Cleep(BusClient):
    """
    Base Cleep class

    It Implements:

        * configuration helpers
        * message bus access
        * logger with log level configured
        * custom crash report
        * driver registration
    """

    CONFIG_DIR = "/etc/cleep/"
    MODULE_DEPS = []
    DEFAULT_CONFIG = None
    MODULE_CONFIG_FILE = None
    MODULE_SENTRY_DSN = None

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor.

        Args:
            bootstrap (dict): bootstrap objects.
            debug_enabled (bool): flag to set debug level to logger.
        """
        # init bus
        BusClient.__init__(self, self.MODULE_NAME, bootstrap)

        # init logger
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)
        self.debug_enabled = debug_enabled

        # members
        self.__execution_step = bootstrap["execution_step"]
        self.events_broker = bootstrap["events_broker"]
        self.cleep_filesystem = bootstrap["cleep_filesystem"]
        self.task_factory = bootstrap["task_factory"]
        self.drivers = bootstrap["drivers"]
        self._external_bus_name = bootstrap["external_bus"]
        self.app_stop_event = bootstrap["app_stop_event"]

        # load and check configuration
        self.__config_lock = Lock()
        self.__config = self.__load_config()
        if getattr(self, "DEFAULT_CONFIG", None) is not None:
            self.__check_config(self.DEFAULT_CONFIG)

        # crash report
        if (
            getattr(self, "MODULE_SENTRY_DSN", None) is not None
            and self.MODULE_SENTRY_DSN
        ):
            # create custom crash report instance for this module with specified DSN
            self.logger.debug(
                "Sentry DSN found in module, create dedicated crash report for this module."
            )

            # get libs from main crash report instance and append current module version
            infos = bootstrap["crash_report"].get_infos()
            infos["libsversion"][self._get_module_name()] = (
                self.MODULE_VERSION if hasattr(self, "MODULE_VERSION") else "0.0.0"
            )

            self.crash_report = CrashReport(
                self.MODULE_SENTRY_DSN,
                infos["product"],
                infos["productversion"],
                infos["libsversion"],
                disabled_by_core=bootstrap["crash_report"].is_enabled(),
            )

        elif (
            self._get_module_name() in CORE_MODULES
            or self._get_module_name() == "inventory"
        ):
            # set default crash report for core module
            self.logger.debug("Default crash report used for mandatory apps")
            self.crash_report = bootstrap["crash_report"]

            # add core module version to libs version
            module_version = getattr(self, "MODULE_VERSION", "0.0.0")
            self.crash_report.add_module_version(
                self.__class__.__name__, module_version
            )

        elif bootstrap["test_mode"]:  # pragma: no cover
            self.logger.debug("Test mode: do not set crash report to module")

        else:
            # no crash report specified, set dummy one (no dsn provided)
            self.logger.debug("Initialize empty crashreport")
            self.crash_report = CrashReport(
                None, "CleepDevice", "0.0.0", {}, False, True
            )

    @staticmethod
    def _file_is_empty(path):
        """
        Return True if file is empty.

        Args:
            path (string): path to check.

        Returns:
            bool: True if file is empty.
        """
        return os.path.isfile(path) and not os.path.getsize(path) > 0

    def _has_config_file(self):
        """
        Check if module has configuration file.

        Returns:
            bool: True if module has config file, False otherwise.
        """
        if getattr(self, "MODULE_CONFIG_FILE", None) is None:
            return False

        return True

    def __load_config(self):
        """
        Load config file.

        Returns:
            dict: configuration file content
        """
        # check if module have config file
        if not self._has_config_file():
            self.logger.debug(
                'Module "%s" has no configuration file configured',
                self.__class__.__name__,
            )
            return None

        out = {}
        self.__config_lock.acquire(True)
        try:
            path = os.path.join(self.CONFIG_DIR, self.MODULE_CONFIG_FILE)
            self.logger.debug('Loading conf file from path "%s"', os.path.abspath(path))
            if os.path.exists(path) and not self._file_is_empty(path):
                out = self.cleep_filesystem.read_json(path)
                if out is None:  # pragma: no cover
                    # should not happen but handle it
                    out = {}
            else:
                # no conf file yet. Create default one
                self.logger.debug("No config file found, create default one")
                out = {}
                self.cleep_filesystem.write_json(path, out)

        except:
            self.logger.exception("Unable to load config file %s:", path)
        self.__config_lock.release()

        return out

    def __save_config(self, config):
        """
        Save config file.

        Args:
            config (dict): config to save

        Returns:
            bool: False if error occured, True otherwise
        """
        out = False

        # get lock
        self.__config_lock.acquire(True)

        try:
            path = os.path.join(self.CONFIG_DIR, self.MODULE_CONFIG_FILE)
            self.cleep_filesystem.write_json(path, config)
            self.__config = config
            out = True

        except:
            self.logger.exception("Unable to write config file %s:", path)

        # release lock
        self.__config_lock.release()

        return out

    def _update_config(self, config):
        """
        Secured config update: update specified fields, do not completely overwrite content

        Args:
            config (dict): new config to update

        Returns:
            bool: False if update failed, True otherwise

        Raises:
            InvalidParameter if input params are invalid
        """
        # check params
        if not isinstance(config, dict):
            raise InvalidParameter('Parameter "config" must be a dict')
        if not self._has_config_file():
            raise Exception(
                "Module %s has no configuration file configured"
                % self.__class__.__name__
            )

        # get lock
        self.__config_lock.acquire(True)

        # keep copy of old config
        old_config = copy.deepcopy(self.__config)

        # update config
        self.__config.update(config)

        # release lock
        self.__config_lock.release()

        # save new config
        if not self.__save_config(self.__config):
            # revert changes
            self.__config_lock.acquire(True)
            self.__config = old_config
            self.__config_lock.release()

            return False

        return True

    def _get_config(self):
        """
        Return deep copy of config dict.

        Returns:
            dict: config file content
        """
        # check if module have config file
        if not self._has_config_file():
            self.logger.debug(
                'Module "%s" has no configuration file configured',
                self.__class__.__name__,
            )
            return {}

        # get lock
        self.__config_lock.acquire(True)

        # make deep copy of structure
        copy_ = copy.deepcopy(self.__config)

        # release lock
        self.__config_lock.release()

        return copy_

    def _get_config_field(self, field, default=None):
        """
        Return specified config field value

        Args:
            field (string): field name

        Returns:
            any: returns field value

        Raises:
            Exception if field is unknown
        """
        try:
            return copy.deepcopy(self.__config[field])

        except KeyError:
            raise Exception('Unknown config field "%s"' % field)

    def _has_config_field(self, field):
        """
        Check if config has specified field

        Args:
            field (string): field to check

        Returns:
            bool: True if field exists
        """
        return field in self.__config if self.__config is not None else False

    def _set_config_field(self, field, value):
        """
        Convenience function to update config field value
        Unlike _update_config function, _set_config_field check parameter existence in config

        Args:
            field (string): field name
            value (any): field value to set

        Returns:
            bool: result of _update_config function
        """
        # check params
        if field not in self.__config:
            raise InvalidParameter('Parameter "%s" doesn\'t exist in config' % field)

        return self._update_config({field: value})

    def __check_config(self, keys):
        """
        Check config files looking for specified keys.
        If key not found, key is added with specified default value.
        Save new configuration file if necessary.

        Args:
            keys (dict): dict of keys-default values {'key1':'default value1', ...}.

        Returns:
            None: nothing, only check configuration file consistency.
        """
        config = self._get_config()

        # check config is a dict, only supported format for config file
        if not isinstance(config, dict):
            self.logger.warning(
                "Invalid configuration file content, only dict content are supported. Reset its content."
            )
            config = {}

        fixed = False
        for key in keys:
            if key not in config:
                # fix missing key
                self.logger.trace('Add missing key "%s" in config file', key)
                config[key] = keys[key]
                fixed = True
        if fixed:
            self.logger.debug("Config file fixed")
            self.__save_config(config)

    def _register_driver(self, driver):
        """
        Register driver

        Args:
            driver (Driver): driver instance

        Raises:
            InvalidParameter: if driver has invalid base class
        """
        if self.__execution_step.step != ExecutionStep.INIT:
            self.logger.warning(
                "Driver registration must be done during INIT step (in application constructor)"
            )
        # check driver
        if not isinstance(driver, Driver):
            raise InvalidParameter("Driver must be instance of base Driver class")

        # set members and register driver
        driver.configure(
            {
                "cleep_filesystem": self.cleep_filesystem,
                "task_factory": self.task_factory,
            }
        )
        self.drivers.register(driver)
        driver._on_registered()

    def _get_drivers(self, driver_type):
        """
        Returns drivers for specified type

        Args:
            driver_type (string): see Driver.DRIVER_XXX for values

        Returns:
            dict: drivers
        """
        return self.drivers.get_drivers(driver_type)

    @staticmethod
    def _get_unique_id():
        """
        Return unique id. Useful to get unique device identifier.

        Returns:
            string: new unique id (uuid4 format).
        """
        return str(uuid.uuid4())

    def is_debug_enabled(self):
        """
        Return True if debug is enabled

        Returns:
            bool: True if debug enabled
        """
        return self.debug_enabled

    def set_debug(self, debug):
        """
        Enable or disable debug level. It changes logger level on the fly.

        Args:
            debug (bool): debug enabled if True, otherwise info level
        """
        # change current logger debug level
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        # update debug flag
        self.debug_enabled = debug

    def _get_module_name(self):
        """
        Return module name

        Returns:
            string: module name
        """
        return self.__class__.__name__.lower()

    def _get_event(self, event_name):
        """
        Get event name

        Args:
            event_name (string): event name

        Returns:
            Event: Event instance
        """
        return self.events_broker.get_event_instance(event_name)

    def get_module_config(self):
        """
        Returns module configuration.

        Returns:
            dict: all config content except 'devices' entry.
        """
        return self._get_config()

    def get_module_commands(self):
        """
        Return available module commands.

        Returns:
            list: list of command names.
        """
        members = dir(self)
        for member in members[:]:
            if not callable(getattr(self, member)):
                # filter module members
                members.remove(member)
            elif member.startswith("_"):
                # filter protected or private commands
                members.remove(member)
            elif member in (
                "send_command",
                "send_event",
                "send_command_to_peer",
                "send_event_to_peer",
                "get_module_commands",
                "get_module_commands",
                "get_module_config",
                "is_debug_enabled",
                "set_debug",
                "is_module_loaded",
                "start",
                "stop",
                "push",
                "on_event",
                "get_env",
                "send_command_from_request",
                "send_event_from_request",
                "send_command_advanced",
                "get_documentation",
                "check_documentation",
                "register_remote_access_url",
                "unregister_remote_access_url",
                "app_paths_for",
            ):
                # filter bus commands / helpers (not RPC commands)
                members.remove(member)
            elif member in (
                "getName",
                "isAlive",
                "isDaemon",
                "is_alive",
                "join",
                "run",
                "setDaemon",
                "setName",
            ):
                # filter Thread functions
                members.remove(member)
            elif isinstance(getattr(self, member, None), Mock):
                # only for unittest
                members.remove(member)

        return members

    def start(self):
        """
        Start module.
        """
        # start bus client (non blocking thread)
        BusClient.start(self)

    def stop(self):
        """
        Stop process.
        """
        BusClient.stop(self)

    def is_module_loaded(self, module):
        """
        Request inventory to check if specified module is loaded or not.

        Args:
            module (string): module name.

        Returns:
            bool: True if module is loaded, False otherwise.
        """
        try:
            resp = self.send_command(
                "is_module_loaded", "inventory", {"module": module}
            )
            if resp.error:
                self.logger.error("Unable to request inventory: %s", resp.message)
                return False

            return resp.data

        except:
            self.logger.exception("Unable to know if module is loaded:")
            self.crash_report.report_exception(
                {"message": "Unable to know if module is loaded", "module": module}
            )
            return False

    def _on_event(self, event):
        """
        Event is received on bus

        Args:
            event (dict): MessageRequest as dict with event values::

                {
                    event (string): event name
                    params (dict): event parameters
                    device_id (string): device that emits event or None
                    sender (string): event sender
                    startup (bool): startup event flag
                }

        """
        self.on_event(event)

    def on_event(self, event):  # pragma: no cover
        """
        Event message received

        Note:
            Implement this function to handle event on your module

        Args:
            event (dict): MessageRequest as dict with event values::

                {
                    event (string): event name
                    params (dict): event parameters
                    device_id (string): device that emits event or None
                    sender (string): event sender
                    startup (bool): startup event flag
                }

        """
        pass

    def _check_parameters(self, parameters):
        """
        Check specified parameters

        Args:
            parameters (list): list of parameters to check::

            [
                {
                    name (string): parameter name (mandatory)
                    value (any): parameter value (mandatory)
                    type (type): parameter primitive type (str, bool...) (default str)
                    none (bool): True if parameter can be None (optional)
                    empty (bool): True if string value can be empty (optional)
                    validator (function): validator function. Take value in parameter and must return bool (optional)
                    message (string): custom message to return instead of generic error (optional)
                    validators (list): list of validators::

                        [
                            {
                                validator (function): parameter validator
                                message (string): message to raise if validator fails
                            },
                            ...
                        ]
                },
                ...
            ]

        Raises:
            MissingParameter if one parameter is None
            InvalidParameter if one parameter has invalid type or value
        """
        for parameter in parameters:
            self.logger.trace("Check parameter %s", parameter)
            # none
            if (
                "none" not in parameter
                or ("none" in parameter and not parameter["none"])
            ) and parameter["value"] is None:
                raise MissingParameter('Parameter "%s" is missing' % parameter["name"])
            if parameter["value"] is None:
                # nothing else to check, parameter value is allowed as None
                continue

            # type
            if not isinstance(parameter["value"], parameter.get("type", str)):
                raise InvalidParameter(
                    'Parameter "%s" must be of type "%s"'
                    % (
                        parameter["name"],
                        parameter.get("type", str).__name__,
                    )
                )

            # empty
            if (
                (
                    "empty" not in parameter
                    or ("empty" in parameter and not parameter["empty"])
                )
                and parameter.get("type", str) is str
                and len(parameter["value"]) == 0
            ):
                raise InvalidParameter(
                    'Parameter "%s" is invalid (specified="%s")'
                    % (
                        parameter["name"],
                        parameter["value"],
                    )
                )

            # validators
            validators = parameter.get("validators", [])
            if "validator" in parameter:
                validators.append(
                    {
                        "validator": parameter["validator"],
                        "message": parameter.get("message", None),
                    }
                )
            for validator in validators:
                if "validator" in validator and not validator["validator"](
                    parameter["value"]
                ):
                    raise InvalidParameter(
                        validator["message"]
                        if validator.get("message")
                        else 'Parameter "%s" is invalid (specified="%s")'
                        % (
                            parameter["name"],
                            parameter["value"],
                        )
                    )

    def send_command_to_peer(self, command, to, peer_uuid, params=None, timeout=5.0):
        """
        Send command to specified peer through external bus.

        Args:
            command (string): command name.
            to (string): command recipient. If None the command is broadcasted but yo'll get no reponse in return.
            peer_uuid (string): peer uuid
            params (dict): command parameters. Default None
            timeout (float): timeout. Default 5 seconds

        Returns:
            MessageResponse: message response instance
        """
        if not self._external_bus_name:
            self.logger.warning(
                "Unable to send message to peer because there is no external bus application installed"
            )
            return MessageResponse(
                error=True, message="No external bus application installed"
            )

        # send command to internal message bus
        return self.send_command(
            "send_command_to_peer",
            self._external_bus_name,
            {
                "command": command,
                "to": to,
                "params": params,
                "peer_uuid": peer_uuid,
                "timeout": timeout,
            },
            timeout,
        )

    def send_event_to_peer(self, event, peer_uuid, params=None):
        """
        Send event to specified peer through external bus

        Args:
            event (string): event name
            peer_uuid (string): peer uuid
            params (dict): event parameters. Default None
        """
        if not self._external_bus_name:
            self.logger.warning(
                "Unable to send message to peer because there is no external bus application installed"
            )
            return MessageResponse(
                error=True, message="No external bus application installed"
            )

        # send command to internal message bus
        return self.send_command(
            "send_event_to_peer",
            self._external_bus_name,
            {
                "event": event,
                "peer_uuid": peer_uuid,
                "params": params,
            },
            3.0,
        )


class CleepRpcWrapper(Cleep):
    """
    Base Cleep class for RPC request wrapping
    """

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects.
            debug_enabled (bool): flag to set debug level to logger.
        """
        # init cleep
        Cleep.__init__(self, bootstrap, debug_enabled)

    def _wrap_request(self, route, request):  # pragma: no cover
        """
        Function called when web request from / in POST is called.

        By default this access point is not supported by Cleep but it can be wrapped here

        Warning:
            Must be implemented

        Args:
            request (bottle.request): web server bottle request content. See
                                      doc https://bottlepy.org/docs/dev/tutorial.html#request-data

        Returns:
            returns any data
        """
        raise NotImplementedError(
            'wrap_request function must be implemented in "%s"'
            % self.__class__.__name__
        )


class CleepModule(Cleep):
    """
    Base cleep class for application

    It implements:

        * device helpers
        * default directories (storage, tmp, asset, bin)

    Filesystem contract
    -------------------
    Non-core apps must persist data only under their ``APP_*`` directories
    (and their config file under ``CONFIG_DIR``), using ``self.cleep_filesystem``.
    At init, that attribute is replaced by ``cleep_filesystem.scoped(...)``:
    writes outside allowed dirs are refused (deny). Raw ``open()`` / ``os.*``
    are not intercepted — CI covers that.

    Core modules (``CORE_MODULES``) keep the unrestricted bootstrap instance.
    """

    # Storage path to save app files (database, music, ...)
    APP_STORAGE_PATH = None
    # Temporary path to save temp data
    APP_TMP_PATH = None
    # Asset path where app assets are stored during installation
    APP_ASSET_PATH = None
    # Binary path where binaries are stored during installation
    APP_BIN_PATH = None
    # Path policy for non-core apps
    APP_FS_POLICY = "deny"

    # Shared roots for app data (also used by update InstallModule)
    APP_STORAGE_ROOT = "/var/opt/cleep/modules/storage"
    APP_TMP_ROOT = "/tmp/cleep/modules"
    APP_ASSET_ROOT = "/var/opt/cleep/modules/asset"
    APP_BIN_ROOT = "/var/opt/cleep/modules/bin"

    @staticmethod
    def app_paths_for(module_name):
        """
        Build APP_* paths for a module name (single source of truth).

        Args:
            module_name (str): module / app name (case-insensitive)

        Returns:
            dict: APP_STORAGE_PATH / APP_TMP_PATH / APP_ASSET_PATH / APP_BIN_PATH
        """
        name = module_name.lower()
        return {
            "APP_STORAGE_PATH": os.path.join(CleepModule.APP_STORAGE_ROOT, name),
            "APP_TMP_PATH": os.path.join(CleepModule.APP_TMP_ROOT, name),
            "APP_ASSET_PATH": os.path.join(CleepModule.APP_ASSET_ROOT, name),
            "APP_BIN_PATH": os.path.join(CleepModule.APP_BIN_ROOT, name),
        }

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects.
            debug_enabled (bool): flag to set debug level to logger.
        """
        # init cleep
        Cleep.__init__(self, bootstrap, debug_enabled)

        # members
        self.__app_doc = None

        # define app paths (created via unrestricted bootstrap filesystem)
        for variable_name, path in self.app_paths_for(
            self.__class__.__name__
        ).items():
            self.__set_path(variable_name, path)

        self.__apply_module_filesystem_scope()

        # add devices section if missing
        if self._has_config_file() and not self._has_config_field("devices"):
            self._update_config({"devices": {}})

        # events
        self.deleted_device_event = None
        try:
            self.deleted_device_event = self.events_broker.get_event_instance(
                "core.device.deleted"
            )
        except:
            pass

    def __set_path(self, variable_name, path):
        """
        Create directories if not exists

        Args:
            variable_name (string): variable name
            path (string): path
        """
        if not os.path.exists(path):
            self.cleep_filesystem.mkdirs(path)
        setattr(self.__class__, variable_name, path)
        self.__dict__[variable_name] = path

    def _is_filesystem_privileged(self):
        """
        Return True if this module may write anywhere via cleep_filesystem.

        Returns:
            bool: True for CORE_MODULES (unrestricted)
        """
        return self._get_module_name() in CORE_MODULES

    def _get_filesystem_allowed_roots(self):
        """
        Paths this module is allowed to mutate via cleep_filesystem.

        Returns:
            list: absolute path roots (dirs and optional config file)
        """
        roots = [
            self.APP_STORAGE_PATH,
            self.APP_TMP_PATH,
            self.APP_ASSET_PATH,
            self.APP_BIN_PATH,
        ]
        config_file = getattr(self, "MODULE_CONFIG_FILE", None)
        if config_file:
            roots.append(os.path.join(self.CONFIG_DIR, config_file))
        return [r for r in roots if r]

    def __apply_module_filesystem_scope(self):
        """Replace cleep_filesystem with a scoped view for non-core modules."""
        if self._is_filesystem_privileged():
            return

        from cleep.libs.internals.cleepfilesystem import CleepFilesystem

        policy = getattr(self, "APP_FS_POLICY", CleepFilesystem.POLICY_WARN)
        self.cleep_filesystem = self.cleep_filesystem.scoped(
            self._get_module_name(),
            allowed_roots=self._get_filesystem_allowed_roots(),
            policy=policy,
        )

    def get_env(self):
        """
        Return module environment variables
        Useful when executing console command

        Returns:
            dict: env vars::

                {
                    APP_STORAGE_PATH (str): app storage path,
                    APP_TMP_PATH (str): app tmp path,
                    APP_ASSET_PATH (str): app asset path,
                    APP_BIN_PATH (str): app binary path,
                }

        """
        return self.app_paths_for(self.__class__.__name__)

    def _add_device(self, data):
        """
        Helper function to add device in module configuration file.
        This function auto inject new entry "devices" in configuration file.
        It appends new device in devices section and add unique id in uuid property.
        It also appends 'name' property if not provided.

        Args:
            data (dict): device data.

        Returns:
            dict: device data if process was successful, None otherwise.
        """
        # check parameters
        if not isinstance(data, dict):
            raise InvalidParameter('Parameter "data" must be a dict')

        # prepare config file
        devices = {}
        if self._has_config_field("devices"):
            devices = self._get_config_field("devices")

        # prepare data
        device_uuid = self._get_unique_id()
        data["uuid"] = device_uuid
        if "name" not in data:
            data["name"] = "noname"
        devices[device_uuid] = data
        data["update"] = int(time.time())
        self.logger.trace("devices: %s", devices)

        # save data
        if not self._update_config({"devices": devices}):
            # error occured
            return None

        return data

    def _delete_device(self, device_uuid):
        """
        Helper function to remove device from module configuration file.

        Args:
            device_uuid (string): device identifier.

        Returns:
            bool: True if device was deleted, False otherwise.
        """
        # check values
        devices = self._get_config_field("devices")
        if device_uuid not in devices:
            self.logger.error("Trying to delete unknown device")
            return False

        # delete device entry
        del devices[device_uuid]

        # save config
        conf_result = self._set_config_field("devices", devices)

        # send device deleted event
        if conf_result and self.deleted_device_event:
            self.deleted_device_event.send(device_id=device_uuid)

        return conf_result

    def _update_device(self, device_uuid, data):
        """
        Helper function to update device.
        This function only update fields that already exists in device data. Other new fields are dropped.

        Args:
            device_uuid (string): device identifier.
            data (dict): device data to update.

        Returns:
            bool: True if device updated, False otherwise.
        """
        # check parameters
        if not isinstance(data, dict):
            raise InvalidParameter('Parameter "data" must be a dict')

        data_ = copy.deepcopy(data)

        # check values
        devices = self._get_config_field("devices")
        if device_uuid not in devices:
            self.logger.warning('Trying to update unknown device "%s"', device_uuid)
            return False

        # always force uuid to make sure data is always valid
        data_["uuid"] = device_uuid
        data_["update"] = int(time.time())

        # update data
        devices[device_uuid].update(
            {k: v for k, v in data_.items() if k in devices[device_uuid].keys()}
        )

        # save data
        return self._set_config_field("devices", devices)

    def _search_device(self, key, value):
        """
        Helper function to search a device based on the property value.
        Useful to search a device of course, but can be used to check if a name is not already assigned to a device.

        Args:
            key (string): device property to search on.
            value (any): property value.

        Returns
            dict: the device data if key-value found, or None otherwise.
        """
        devices = self._get_config_field("devices")
        if len(devices) == 0:
            # no device in dict, return no match
            return None

        # search
        for device_uuid in devices:
            if key in devices[device_uuid] and devices[device_uuid][key] == value:
                # device found
                return devices[device_uuid]

        return None

    def _search_devices(self, key, value):
        """
        Helper function to search a device based on the property value.
        Useful to search a device of course, but can be used to check if a name is not already assigned to a device.

        Args:
            key (string): device property to search on.
            value (any): property value.

        Returns
            list: list of devices which key-value matches, empty list if nothing found
        """
        output = []

        # check values
        devices = self._get_config_field("devices")
        if len(devices) == 0:
            # no device in dict, return no match
            return output

        # search
        for device_uuid in devices:
            if key in devices[device_uuid] and devices[device_uuid][key] == value:
                # device found
                output.append(devices[device_uuid])

        return output

    def _get_device(self, device_uuid):
        """
        Get device according to specified identifier.

        Args:
            device_uuid (string): device identifier.

        Returns:
            dict: None if device not found, device data otherwise.
        """
        devices = self._get_config_field("devices")
        return devices[device_uuid] if device_uuid in devices else None

    def get_module_devices(self):
        """
        Returns module devices.

        Returns:
            dict: all devices registered in 'devices' config section::

                {
                    device uuid (string): device data (dict),
                    ...
                }

        """
        return self._get_config()["devices"] if self._has_config_file() else {}

    def _get_devices(self):
        """
        Return module devices (get_module_devices alias).

        Returns:
            dict: all devices registered in 'devices' config section::

                {
                    device uuid (string): device data (dict),
                    ...
                }

        """
        return self.get_module_devices()

    def _get_device_count(self):
        """
        Return number of devices registered in module.

        Returns:
            int: number of saved devices.
        """
        return len(self._get_config_field("devices")) if self._has_config_file() else 0

    def get_module_config(self):
        """
        Returns module configuration.

        Returns:
            dict: all config content except 'devices' entry.
        """
        config = self._get_config()

        # remove devices from config
        if "devices" in config:
            del config["devices"]

        return config

    def get_module_commands(self):
        """
        Return available module commands.

        Returns:
            list: list of command names.
        """
        members = Cleep.get_module_commands(self)
        members.remove("get_module_devices")
        return members

    def get_documentation(self, no_cache=False):
        """
        Return app documentation

        Args:
            no_cache (bool, optional): True to bypass cached documentation. Defaults to False.

        Returns:
            dict: app documentation::

                {
                    command name (dict): dict of command documentation
                        {
                            descriptions (dict): command descriptions (short and long)
                            args (list): list of command arguments
                            returns (list): list of command returned values
                            raises (list): list of exception
                        }
                    ...
                }

        """
        if self.__app_doc and not no_cache:
            return self.__app_doc

        cleep_doc = CleepDoc()
        app_doc = {}

        commands = self.get_module_commands()
        for command_name in commands:
            command_pointer = getattr(self, command_name)
            app_doc[command_name] = cleep_doc.get_command_doc(command_pointer)
        self.__app_doc = app_doc

        return self.__app_doc

    def check_documentation(self, with_details=False):
        """
        Check app documentation

        Args:
            with_details (bool): append check details to result. Defaults to False.

        Returns:
            dict: app errors and warnings::

                {
                    command name (dict): check result for specified command
                        {
                            valid (bool): True if valid
                            errors (list): list of errors
                            warnings (list): list of warnings
                        }
                    ...
                }

        """
        cleep_doc = CleepDoc()
        app_doc_validity = {}

        # Validate against a fresh class loaded from disk so modsync'd sources
        # are checked even if this process still holds an older in-memory copy.
        command_owner = self.__load_class_from_disk_for_doc_check()

        commands = self.get_module_commands()
        for command_name in commands:
            command_pointer = getattr(command_owner, command_name)
            app_doc_validity[command_name] = cleep_doc.is_command_doc_valid(
                command_pointer, with_details
            )

        return app_doc_validity

    def __load_class_from_disk_for_doc_check(self):
        """
        Load a fresh copy of this module class from its source file.

        Only applies to installed apps (cleep.modules.*). Does not replace the
        live module in sys.modules (safe while Cleep runs). Falls back to the
        in-memory class if reload fails or for non-app classes (tests, core).
        """
        module_name = self.__class__.__module__
        if not module_name.startswith("cleep.modules."):
            return self.__class__

        try:
            import importlib.util
            import inspect
            import time

            path = inspect.getfile(self.__class__)
            if path.endswith(".pyc"):
                path = path[:-1]
            temp_module_name = (
                f"_cleep_doccheck_{self.__class__.__name__}_{time.time_ns()}"
            )
            spec = importlib.util.spec_from_file_location(temp_module_name, path)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"Unable to load module spec from {path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, self.__class__.__name__)
        except Exception:
            self.logger.exception(
                "Unable to load module from disk for documentation check, "
                "falling back to in-memory class"
            )
            return self.__class__

    def send_command_advanced(
        self, command, to, params=None, timeout=3.0, raise_exc=False
    ):
        """
        Send command as default send_command function but handle errors logging them and return data
        It also can throw exception if requested

        Args:
            command (string): command name.
            to (string): command recipient. If None the command is broadcasted but you'll get no reponse in return.
            params (dict): command parameters.
            timeout (float): change default timeout if you wish. Default is 3 seconds.
            raise_exc (boolean): if True raise exception

        Returns:
            any: message response data or None if error (and raise_exc False)
        """
        resp = self.send_command(command, to, params, timeout)
        if resp.error:
            self.logger.error(
                "Error occured executing command %s to %s: %s",
                command,
                to,
                resp.message,
            )
            if raise_exc:
                raise Exception(resp.message)
            return None

        return resp.data


class CleepResources(CleepModule):
    """
    Base class for apps that share exclusive peripherals via CriticalResources.

    Declare catalogue names in ``MODULE_RESOURCES``::

        MODULE_RESOURCES = {
            "audio.playback": {"permanent": False},  # acquire on demand
            "audio.capture": {"permanent": True},   # hold at boot, yield, reclaim when idle
        }

    Only one app may set ``permanent: True`` per resource. The first module
    that registers wins; a second permanent claim is refused (handlers still
    register so the app can acquire on demand). Load order = inventory order.

    Then implement the ``_on_resource_*`` handlers. Use ``_need_resource`` /
    ``_need_resources`` to acquire and ``_release_resource_session`` (or
    ``_release_resource`` for a single name) to release.

    See :mod:`cleep.libs.internals.resource_catalog` for the contract and
    ReSpeaker remigration notes.
    """

    # resource_name -> {"permanent": bool}
    MODULE_RESOURCES = {}

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        CleepModule.__init__(self, bootstrap, debug_enabled)

        self.__critical_resources = bootstrap["critical_resources"]
        self.__resource_sessions = {}
        self.__register_resources()

    def __register_resources(self):
        """Register handlers and optional permanent resources with the arbitrator."""
        handlers = {
            "on_granted": self._on_resource_granted,
            "on_revoke_requested": self._on_resource_revoke_requested,
            "on_revoked": self._on_resource_revoked,
            "on_denied": self._on_resource_denied,
        }
        permanent = []
        for resource_name, conf in (self.MODULE_RESOURCES or {}).items():
            conf = conf or {}
            if conf.get("permanent"):
                permanent.append(resource_name)

        try:
            self.__critical_resources.register(
                self.MODULE_NAME,
                handlers,
                permanent_resources=tuple(permanent),
            )
        except Exception as exc:
            # Two apps claimed permanent on the same resource: keep handlers,
            # drop permanent so the module still works on demand.
            if "already has permanent module" not in str(exc):
                raise
            self.logger.error(
                'Permanent resource conflict for module "%s": %s. '
                "Registering without permanent hold (first claimant wins).",
                self.MODULE_NAME,
                exc,
            )
            if self.crash_report:
                self.crash_report.manual_report(
                    "Critical resource permanent conflict",
                    {
                        "module": self.MODULE_NAME,
                        "permanent_resources": permanent,
                        "error": str(exc),
                    },
                )
            self.__critical_resources.register(
                self.MODULE_NAME,
                handlers,
                permanent_resources=(),
            )

    def _on_resource_granted(self, session):
        """
        Resource session granted.

        Args:
            session (ResourceSession): granted session
        """
        self.__resource_sessions[session.session_id] = session
        # Compatibility shim for apps still overriding _resource_acquired
        for name in session.resource_names:
            self._resource_acquired(name)

    def _on_resource_revoke_requested(self, session):
        """
        Another module needs resources you hold — release soon.

        Args:
            session (ResourceSession): requester session (not your hold)
        """
        for name in session.resource_names:
            self._resource_needs_to_be_released(name)

    def _on_resource_revoked(self, session, forced=False):
        """
        Your hold was revoked (after timeout steal when ``forced``).

        Args:
            session (ResourceSession): your former session
            forced (bool): True if stolen after timeout
        """
        self.__resource_sessions.pop(session.session_id, None)
        for name in session.resource_names:
            self._resource_needs_to_be_released(name)

    def _on_resource_denied(self, session, reason=""):
        """
        Acquire was denied (e.g. higher-priority holder).

        Args:
            session (ResourceSession): denied session
            reason (str): deny reason
        """
        self.logger.warning(
            "Resource acquire denied for %s (%s)",
            session.resource_names,
            reason,
        )

    def _resource_acquired(self, resource_name):
        """
        Compatibility hook called per resource name after grant.

        Override `_on_resource_granted` for session-aware handling, or this
        method for simple single-name apps.
        """
        raise NotImplementedError(
            'Method "_resource_acquired" must be implemented in "%s"'
            % self.__class__.__name__
        )

    def _resource_needs_to_be_released(self, resource_name):
        """
        Compatibility hook when release is requested or forced.

        Override `_on_resource_revoke_requested` / `_on_resource_revoked` for
        session-aware handling.
        """
        raise NotImplementedError(
            'Method "_resource_needs_to_be_released" must be implemented in "%s"'
            % self.__class__.__name__
        )

    def _need_resource(
        self,
        resource_name,
        priority=None,
        timeout_s=None,
    ):
        """
        Request a single catalogue resource.

        Args:
            resource_name (str): catalogue name (e.g. ``audio.playback``)
            priority (ResourcePriority|None): defaults to NORMAL
            timeout_s (float|None): steal timeout seconds
        """
        return self._need_resources(
            (resource_name,), priority=priority, timeout_s=timeout_s
        )

    def _need_resources(self, resource_names, priority=None, timeout_s=None):
        """
        Request one or more catalogue resources atomically.

        Args:
            resource_names (list|tuple): catalogue names
            priority (ResourcePriority|None): defaults to NORMAL
            timeout_s (float|None): steal timeout seconds

        Returns:
            ResourceSession: the session submitted for acquisition
        """
        from cleep.libs.internals.resource_catalog import (
            DEFAULT_ACQUIRE_TIMEOUT_S,
            ResourcePriority,
            make_session,
        )

        if priority is None:
            priority = ResourcePriority.NORMAL
        if timeout_s is None:
            timeout_s = DEFAULT_ACQUIRE_TIMEOUT_S
        session = make_session(
            self.MODULE_NAME,
            resource_names,
            priority=priority,
            timeout_s=timeout_s,
        )
        self.__critical_resources.acquire(session)
        return session

    def _release_resource(self, resource_name):
        """
        Release the resource currently held by this module (single name).

        Args:
            resource_name (str): catalogue name
        """
        return self.__critical_resources.release_by_module(
            self.MODULE_NAME, resource_name
        )

    def _release_resource_session(self, session):
        """
        Release a specific session returned by ``_need_resources``.

        Args:
            session (ResourceSession): session to release
        """
        return self.__critical_resources.release(session)

    def _get_resources(self):
        """
        Return catalogue resource names.

        Returns:
            list: available resource names
        """
        return self.__critical_resources.get_resources()


class CleepRenderer(CleepModule):
    """
    Base cleep class for renderer.

    It implements:

        * automatic renderer registration
        * render function to render received profile

    A renderer application must declare members:
        * RENDERER_TYPE (RENDERERS): see RENDERERS values in common
        * RENDERER_PROFILES (list): list of profiles handled by application (see list of available renderers in core/profiles dir)
    And declare mathods:
        * on_render: implement this function to handle render event using profile parameters
    """

    RENDERER_TYPE = RENDERERS.UNKNOWN
    RENDERER_PROFILES = []

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger.
        """
        CleepModule.__init__(self, bootstrap, debug_enabled)

        # members
        self.profiles_types = []

    def _get_renderer_config(self):
        """
        Register internally available profiles and return it.
        This method is called once by inventory at startup

        Returns:
            dict: handled profiles by instance::

                {
                    profiles: list (RendererProfile)
                }

        Raises:
            Exception: if RENDERER_PROFILES member is not defined
        """
        if getattr(self, "RENDERER_PROFILES", None) is None:
            raise Exception(
                'RENDERER_PROFILES is not defined in "%s"' % self.__class__.__name__
            )
        if not isinstance(self.RENDERER_PROFILES, list):
            raise Exception(
                'RENDERER_PROFILES must be a list in "%s"' % self.__class__.__name__
            )

        # cache profile types as string
        for profile in self.RENDERER_PROFILES:
            self.profiles_types.append(profile.__name__)

        return {"profiles": self.RENDERER_PROFILES}

    def render(self, profile_name, profile_values):
        """
        Render profile

        Args:
            profile_name (string): profile name to identify processed profile
            profile_values (dict): profile values to render

        Returns:
            bool: True if post is successful.
        """
        # call implementation
        try:
            self.on_render(profile_name, profile_values)
            return True
        except NotImplementedError:
            raise
        except:
            self.logger.exception(
                'Rendering profile "%s" failed (%s):', profile_name, profile_values
            )
            return False

    def on_render(self, profile_name, profile_values):  # pragma: no cover
        """
        Use specified profile values to render them

        Args:
            profile_name (string): profile name to identify processed profile
            profile_values (dict): profile values to render

        Warning:
            Must be implemented

        Raises:
            NotImplementedError: if not implemented
        """
        raise NotImplementedError(
            'Method "on_render" must be implemented in "%s"' % self.__class__.__name__
        )

    def get_module_commands(self):
        """
        Return available module commands.

        Returns:
            list: list of command names.
        """
        members = CleepModule.get_module_commands(self)
        members.remove("render")
        members.remove("on_render")
        return members


class CleepExternalBus(CleepModule):
    """
    Base Cleep class for external bus implementation.

    Provides inventory-backed device attributes (auth, remote access URLs,
    and future fields) as a plain dict. Subclasses decide how to publish
    that data on their transport — core has no notion of headers or ZRE.
    """

    # Timeout for inventory lookups when collecting device info
    PEER_DEVICE_INFO_TIMEOUT = 3.0

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects.
            debug_enabled (bool): flag to set debug level to logger.
        """
        # init cleep
        CleepModule.__init__(self, bootstrap, debug_enabled)

        # store rpc config
        self.rpc_config = bootstrap.get("rpc_config", {})

    def _get_peer_device_info(self):
        """
        Collect device attributes any external bus may need to advertise.

        Inventory knowledge stays in core: subclasses must not call inventory
        for these fields. Add new keys here when core exposes more data.
        How (or whether) they are published is left to the subclass.

        Returns:
            dict: typed values::

                {
                    auth (bool): HTTP basic auth effectively enabled
                    remoteaccess (dict): {application_name: url}
                }
        """
        return {
            "auth": self.__get_auth_enabled(),
            "remoteaccess": self.__get_remote_access_urls(),
        }

    def __get_auth_enabled(self):
        """
        Whether HTTP basic auth is effectively enabled (from inventory).

        Returns:
            bool: True when clients must send credentials
        """
        try:
            resp = self.send_command(
                "get_auth_enabled",
                "inventory",
                timeout=self.PEER_DEVICE_INFO_TIMEOUT,
            )
            if resp and not resp.error:
                return bool(resp.data)
        except Exception:
            self.logger.exception("Unable to read auth status from inventory")
        return False

    def __get_remote_access_urls(self):
        """
        Public addresses registered on this device (from inventory).

        Returns:
            dict: ``{application_name: url}``
        """
        try:
            resp = self.send_command(
                "get_remote_access_urls",
                "inventory",
                timeout=self.PEER_DEVICE_INFO_TIMEOUT,
            )
            if resp and not resp.error and isinstance(resp.data, dict):
                return resp.data
        except Exception:
            self.logger.exception("Unable to read remote access urls from inventory")
        return {}

    def send_command_to_peer(
        self, command, to, peer_uuid, params=None, timeout=5.0, manual_response=None
    ):
        """
        Helper function to send command message to specified peer through external bus.

        Args:
            command (string): command name.
            to (string): command recipient. If None the command is broadcasted but yo'll get no reponse in return.
            peer_uuid (string): peer uuid
            params (dict): command parameters. Default None
            timeout (float): timeout. Default 5 seconds
            manual_response (function): manual response function to call to return command response. This parameter is automatically
                                        filled by internal bus or is None if function is called from the module itself.
        """
        # overwrite super function to call directly internal function
        self._send_command_to_peer(
            command, to, peer_uuid, params, timeout, manual_response
        )

    def _send_command_to_peer(
        self, command, to, peer_uuid, params=None, timeout=5.0, manual_response=None
    ):
        """
        Send command to peer implementation

        Args:
            command (string): command name.
            to (string): command recipient. If None the command is broadcasted but yo'll get no reponse in return.
            peer_infos (dict): infos about peer that sends the command
            params (dict): command parameters.
            manual_response (function): manual response function to call to return command response. This parameter is automatically
                                        filled by internal bus or is None if function is called from the module itself.

        Warning:
            Must be implemented
        """
        raise NotImplementedError(
            '_send_command_to_peer function must be implemented in "%s"'
            % self.__class__.__name__
        )

    def send_event_to_peer(self, event_name, peer_uuid, params=None):
        """
        Send event to specified peer through external bus

        Args:
            event_name (string): event name
            peer_uuid (string): peer uuid
            params (dict): event parameters. Default None
        """
        # overwrite super function to call directly internal function
        self._send_event_to_peer(event_name, peer_uuid, params)

    def _send_event_to_peer(self, event_name, peer_uuid, params=None):
        """
        Send event to specified peer through external bus implementation

        Args:
            event_name (string): event name
            peer_uuid (string): peer uuid
            params (dict): event parameters. Default None

        Warning:
            Must be implemented
        """
        raise NotImplementedError(
            '_send_event_to_peer function must be implemented in "%s"'
            % self.__class__.__name__
        )


class CleepRemoteAccessModule(CleepModule):
    """
    Base class for an application that publishes a public address.

    The subclass reports the address when the tunnel is open and clears it when
    the tunnel closes. A later revision of this class will proxy the other
    devices of the house through that address.
    """

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects.
            debug_enabled (bool): flag to set debug level to logger.
        """
        CleepModule.__init__(self, bootstrap, debug_enabled)

    def register_remote_access_url(self, url):
        """
        Register this application's public address.

        One address is kept per application.

        Args:
            url (str): public address

        Returns:
            bool: True when the address is registered
        """
        try:
            resp = self.send_command(
                "register_remote_access_url", "inventory", {"url": url}
            )
            if resp.error:
                self.logger.error(
                    "Unable to request inventory register_remote_access_url: %s",
                    resp.message,
                )
                return False

            return True

        except Exception:
            self.logger.exception("Unable to register remote access url:")
            self.crash_report.report_exception(
                {
                    "message": "Unable register remote access url",
                    "url": url,
                }
            )
            return False

    def unregister_remote_access_url(self):
        """
        Remove this application's public address.

        Returns:
            bool: True when the address is removed
        """
        try:
            resp = self.send_command("unregister_remote_access_url", "inventory")
            if resp.error:
                self.logger.error(
                    "Unable to request inventory unregister_remote_access_url: %s",
                    resp.message,
                )
                return False

            return True

        except Exception:
            self.logger.exception("Unable to unregister remote access url:")
            self.crash_report.report_exception(
                {
                    "message": "Unable unregister remote access url",
                }
            )
            return False
