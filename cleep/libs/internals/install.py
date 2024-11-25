#!/usr/bin/env python
# -*- coding: utf-8 -*

import logging
import os
from gevent import sleep
from cleep.libs.internals.console import EndlessConsole
from cleep.libs.internals.installmodule import (
    InstallModule,
    UninstallModule,
    UpdateModule,
)
from cleep.libs.internals.installdeb import InstallDeb
from cleep.exception import MissingParameter, InvalidParameter

__all__ = ["Install"]


class Install:
    """
    Install helper

    This class helps you to install different kind of things:

        * deb files using dpkg
        * tar.gz using tar
        * zip using unzip
        * Cleep module install/uninstall/update (ok class name is not correct ;) )
        * system packages install/uninst using apt-get command

    """

    STATUS_IDLE = 0
    STATUS_PROCESSING = 1
    STATUS_DONE = 2
    STATUS_ERROR = 3

    def __init__(self, cleep_filesystem, crash_report, task_factory, status_callback, blocking=False):
        """
        Constructor

        Args:
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            crash_report (CrashReport): Crash report instance
            task_factory (TaskFactory): Task factory instance
            status_callback (function): status callback. Params: status
            blocking (bool): enable or not blocking mode. If blocking mode is enabled, all functions are blocking
        """
        # logger
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)

        # members
        self.cleep_filesystem = cleep_filesystem
        self.crash_report = crash_report
        self.task_factory = task_factory
        self.blocking = blocking
        self.__console = None
        self.status = self.STATUS_IDLE
        self.status_callback = status_callback
        self.stdout = []
        self.stderr = []
        self.__running = True
        self.extra = None

    def get_status(self):
        """
        Return current installation status

        Returns:
            dict: status::

                {
                    status (string): current status
                    stdout (list): list of messages received on console
                    stderr (list): list of messages received on stderr
                }

        """
        return {"status": self.status, "stdout": self.stdout, "stderr": self.stderr}

    def __reset_status(self, status):
        """
        Reset status

        Args:
            status (int): status to set (use self.STATUS_XXX)
        """
        self.status = status
        self.stdout = []
        self.stderr = []

    def __callback_end(self, return_code, killed):
        """
        End of process callback

        Args:
            return_code (int): command return code
            killed (bool): True if command was killed
        """
        self.logger.trace("Command terminated callback")

        # update status if necessary
        if return_code != 0 or killed:
            self.status = self.STATUS_ERROR
        elif self.status != self.STATUS_ERROR:
            self.status = self.STATUS_DONE

        # send for the last time current status
        if self.status_callback:
            self.status_callback(self.get_status())

        # unblock function call
        self.__running = False

        # disable write at end of command execution
        self.cleep_filesystem.disable_write()

    def __callback_quiet(self, stdout, stderr):  # pragma: no cover
        """
        Quiet output. Does nothing
        """
        return

    def refresh_system_packages(self):
        """
        Refresh sytem packages list
        """
        if self.status == self.STATUS_PROCESSING:
            raise Exception("Installer is already processing")

        # update status
        self.__reset_status(self.STATUS_PROCESSING)

        # enable file system writings
        self.cleep_filesystem.enable_write()

        # refresh packages
        command = "/usr/bin/apt-get update"
        self.logger.debug("Command: %s", command)
        self.__console = EndlessConsole(
            command, self.__callback_quiet, self.__callback_end
        )
        self.__console.start()

        # blocking mode
        if self.blocking:
            self.__running = True
            while self.__running:
                sleep(0.25)

            return self.status == self.STATUS_DONE

        return True

    def __callback_package(self, stdout, stderr):
        """
        Package install callback

        Args:
            stdout (list): console stdout
            stderr (list): console stderr
        """
        # append current stdout/stderr
        if stdout is not None:
            self.stdout.append(stdout)
        if stderr is not None:
            self.stderr.append(stderr)

        # send status to caller callback
        if self.status_callback:
            self.status_callback(self.get_status())

    def install_system_package(self, package_name):
        """
        Install package using apt-get

        Args:
            package_name (string): package name to install

        Returns:
            bool: True if install succeed (in blocking mode only)
        """
        if self.status == self.STATUS_PROCESSING:
            raise Exception("Installer is already processing")

        # reset status
        self.__reset_status(self.STATUS_PROCESSING)

        # enable write
        self.cleep_filesystem.enable_write()

        # install deb
        command = '/usr/bin/apt-get install -y "%s"' % package_name
        self.logger.debug("Command: %s", command)
        self.__running = True
        self.__console = EndlessConsole(
            command, self.__callback_package, self.__callback_end
        )
        self.__console.start()

        # blocking mode
        if self.blocking:
            while self.__running:
                sleep(0.25)

            return self.status == self.STATUS_DONE

        return True

    def uninstall_system_package(self, package_name, purge=False):
        """
        Install package using apt

        Args:
            package_name (string): package name to install
            purge (bool): purge package (remove config files)

        Returns:
            bool: True if install succeed (in blocking mode only)
        """
        if self.status == self.STATUS_PROCESSING:
            raise Exception("Installer is already processing")

        # reset status
        self.__reset_status(self.STATUS_PROCESSING)

        # enable write
        self.cleep_filesystem.enable_write()

        # install deb
        action = "purge" if purge else "remove"
        command = '/usr/bin/apt-get %s -y "%s"' % (action, package_name)
        self.logger.debug("Command: %s", command)
        self.__running = True
        self.__console = EndlessConsole(
            command, self.__callback_package, self.__callback_end
        )
        self.__console.start()

        # blocking mode
        if self.blocking:
            while self.__running:
                sleep(0.25)

            return self.status == self.STATUS_DONE

        return True

    def __callback_deb(self, status):
        """
        Deb install callback

        Args:
            status (dict): status dict like returned by InstallDeb get_status function
        """
        # update output
        self.stdout = status["stdout"]
        self.stderr = status["stderr"]

        # update status
        if status["status"] == InstallDeb.STATUS_RUNNING:
            self.status = self.STATUS_PROCESSING
        elif status["status"] in (InstallDeb.STATUS_ERROR, InstallDeb.STATUS_KILLED):
            self.status = self.STATUS_ERROR
        elif status["status"] == InstallDeb.STATUS_DONE:
            self.status = self.STATUS_DONE

        # send status to caller callback
        if self.status_callback:
            self.status_callback(self.get_status())

    def install_deb(self, deb_path):
        """
        Install .deb file using dpkg

        Args:
            deb_path (string): path to deb package

        Returns:
            bool: True if install succeed (in blocking mode only)
        """
        if self.status == self.STATUS_PROCESSING:
            raise Exception("Installer is already processing")

        # reset status
        self.__reset_status(self.STATUS_PROCESSING)

        # install deb (and its dependencies)
        # note: filesystem writings are handled by InstallDeb lib
        installer = InstallDeb(self.cleep_filesystem, self.crash_report)
        installer.install(deb_path, blocking=False, status_callback=self.__callback_deb)

        # blocking mode
        if self.blocking:
            # loop
            while self.status == self.STATUS_PROCESSING:
                sleep(0.25)

            return self.status == self.STATUS_DONE

        return True

    def __callback_archive(self, stdout, stderr):
        """
        Deb install callback

        Args:
            stdout (list): console stdout
            stderr (list): console stderr
        """
        # append current stdout/stderr
        if stdout is not None:
            self.stdout.append(stdout)
        if stderr is not None:
            self.stderr.append(stderr)

        # send status to caller callback
        if self.status_callback:
            self.status_callback(self.get_status())

    def install_archive(self, archive, install_path):
        """
        Install archive (.tar.gz, .zip) to specified install path

        Args:
            archive (string): archive full path
            install_path (string): installation fullpath directory

        Returns:
            bool: True if install succeed (in blocking mode only)
        """
        if self.status == self.STATUS_PROCESSING:
            raise Exception("Installer is already processing")

        # check params
        if archive is None or len(archive.strip()) == 0:
            raise Exception('Parameter "archive" is missing')
        if install_path is None or len(install_path.strip()) == 0:
            raise Exception('Parameter "install_path" is missing')
        if not os.path.exists(archive):
            raise Exception('Archive "%s" does not exist' % archive)

        # reset status
        self.__reset_status(self.STATUS_PROCESSING)

        # get archive decompressor according to archive extension
        command = None
        if archive.endswith(".tar.gz"):
            command = '/bin/tar xzf "%s" -C "%s"' % (archive, install_path)
        elif archive.endswith(".zip"):
            command = '/usr/bin/unzip "%s" -d "%s"' % (archive, install_path)
        else:
            raise Exception("File format not supported. Only zip and tar.gz supported.")

        # enable write
        self.cleep_filesystem.enable_write()

        # create output dir if it isn't exist
        if not os.path.exists(install_path):
            self.cleep_filesystem.mkdir(install_path, recursive=True)

        # execute command
        self.logger.debug("Command: %s", command)
        self.__running = True
        self.__console = EndlessConsole(
            command, self.__callback_archive, self.__callback_end
        )
        self.__console.start()

        # blocking mode
        if self.blocking:
            # loop
            while self.__running:
                sleep(0.25)

            return self.status == self.STATUS_DONE

        return True

    def __callback_install_module(self, status):
        """
        Module install callback

        Args:
            status (dict): module status::

                {
                    module (string): module name
                    status (int): module process status
                    prescript (dict): {stderr, stdout, returncode}
                    postscript (dict): {stderr, stdout, returncode}
                    updateprocess (bool): uninstall triggered by module update
                    process (list): process status
                }

        """
        self.logger.debug("Install status: %s", status)
        # save status
        if status["status"] == InstallModule.STATUS_IDLE:
            self.status = self.STATUS_IDLE
        elif status["status"] == InstallModule.STATUS_INSTALLING:
            self.status = self.STATUS_PROCESSING
        elif status["status"] == InstallModule.STATUS_INSTALLED:
            self.status = self.STATUS_DONE
        else:
            self.status = self.STATUS_ERROR

        # save stdout/stderr at end of process
        if self.status in (self.STATUS_DONE, self.STATUS_ERROR):
            # prescript
            if status["prescript"]["returncode"] is not None:
                self.stdout += (
                    ["Pre-install script stdout:"]
                    + status["prescript"]["stdout"]
                    + [
                        "Pre-install script return code: %s"
                        % status["prescript"]["returncode"]
                    ]
                )
                self.stderr += ["Pre-install script stderr:"] + status["prescript"][
                    "stderr"
                ]
            else:
                self.stdout += ["No pre-install script"]
                self.stderr += ["No pre-install script"]

            # postscript
            if status["postscript"]["returncode"] is not None:
                self.stdout += (
                    ["", "Post-install script stdout:"]
                    + status["postscript"]["stdout"]
                    + [
                        "Post-install script return code: %s"
                        % status["postscript"]["returncode"]
                    ]
                )
                self.stderr += ["", "Post-install script stderr:"] + status[
                    "postscript"
                ]["stderr"]
            else:
                self.stdout += ["No post-install script"]
                self.stderr += ["No post-install script"]

        # send status
        if self.status_callback:
            current_status = self.get_status()
            # inject more data
            current_status["module"] = status["module"]
            current_status["updateprocess"] = status["updateprocess"]
            current_status["process"] = status["process"]
            current_status["extra"] = self.extra
            self.status_callback(current_status)

    def install_module(self, module_name, module_infos, extra={}):
        """
        Install specified module

        Args:
            module_name (string): module name to install
            modules_infos (dict): module infos reported in modules.json
            extra (dict): extra data to install process

        Returns:
            bool: True if module installed (in blocking mode only)
        """
        if self.status == self.STATUS_PROCESSING:
            raise Exception("Installer is already processing")

        # check params
        if module_name is None or len(module_name) == 0:
            raise MissingParameter('Parameter "module_name" is missing')
        if not module_infos:
            raise MissingParameter('Parameter "module_infos" is missing')
        if not isinstance(module_infos, dict):
            raise InvalidParameter('Parameter "module_infos" is invalid')
        if not isinstance(extra, dict):
            raise InvalidParameter('Parameter "extra" is invalid')

        # save extra
        self.extra = extra

        # reset status
        self.__reset_status(self.STATUS_PROCESSING)

        # launch installation
        # note: filesystem writings are handled by InstallModule lib
        install = InstallModule(
            module_name,
            module_infos,
            update_process=False,
            status_callback=self.__callback_install_module,
            cleep_filesystem=self.cleep_filesystem,
            crash_report=self.crash_report,
            task_factory=self.task_factory,
        )
        if extra and extra.get("package"):
            install.set_package(extra.get("package"))
        install.start()

        # blocking mode
        self.logger.debug("Install module blocking? %s", self.blocking)
        if self.blocking:
            # wait for end of installation
            while install.is_installing():
                sleep(0.25)

            # check install status
            return install.get_status().get("status") == InstallModule.STATUS_INSTALLED

        return True

    def __callback_uninstall_module(self, status):
        """
        Module uninstall callback

        Args:
            status (dict): module status::

                {
                    module (string): module name
                    status (int): module process status
                    prescript (dict): {stderr, stdout, returncode}
                    postscript (dict): {stderr, stdout, returncode}
                    updateprocess (bool): uninstall triggered by module update
                }

        """
        # save status
        if status["status"] == UninstallModule.STATUS_IDLE:
            self.status = self.STATUS_IDLE
        elif status["status"] == UninstallModule.STATUS_UNINSTALLING:
            self.status = self.STATUS_PROCESSING
        elif status["status"] == UninstallModule.STATUS_UNINSTALLED:
            self.status = self.STATUS_DONE
        else:
            self.status = self.STATUS_ERROR

        # save stdout/stderr at end of process
        if self.status in (self.STATUS_DONE, self.STATUS_ERROR):
            # prescript
            if status["prescript"]["returncode"] is not None:
                self.stdout += (
                    ["Pre-uninstall script stdout:"]
                    + status["prescript"]["stdout"]
                    + [
                        "Pre-uninstall script return code: %s"
                        % status["prescript"]["returncode"]
                    ]
                )
                self.stderr += ["Pre-uninstall script stderr:"] + status["prescript"][
                    "stderr"
                ]
            else:
                self.stdout += ["No pre-uninstall script"]
                self.stderr += ["No pre-uninstall script"]

            # postscript
            if status["postscript"]["returncode"] is not None:
                self.stdout += (
                    ["", "Post-uninstall script stdout:"]
                    + status["postscript"]["stdout"]
                    + [
                        "Post-uninstall script return code: %s"
                        % status["postscript"]["returncode"]
                    ]
                )
                self.stderr += ["", "Post-uninstall script stderr:"] + status[
                    "postscript"
                ]["stderr"]
            else:
                self.stdout += ["No post-uninstall script"]
                self.stderr += ["No post-uninstall script"]

        # send status
        if self.status_callback:
            current_status = self.get_status()
            # inject more data
            current_status["module"] = status["module"]
            current_status["updateprocess"] = status["updateprocess"]
            current_status["process"] = status["process"]
            self.status_callback(current_status)

    def uninstall_module(self, module_name, module_infos, force=False):
        """
        Uninstall specified module

        Warning:
            This function does not handle filesystem because process could be async.
            So take care to enable/disable writings before calling it.

        Args:
            module_name (string): module name to uninstall
            modules_infos (dict): module infos reported in modules.json
            force (bool): uninstall module and continue if error occured

        Returns:
            bool: True if module uninstalled (in blocking mode only)
        """
        if self.status == self.STATUS_PROCESSING:
            raise Exception("Installer is already processing")

        # check params
        if module_name is None or len(module_name) == 0:
            raise MissingParameter('Parameter "module_name" is missing')
        if not module_infos:
            raise MissingParameter('Parameter "module_infos" is missing')
        if not isinstance(module_infos, dict):
            raise InvalidParameter('Parameter "module_infos" is invalid')

        # reset status
        self.__reset_status(self.STATUS_PROCESSING)

        # launch uninstallation
        uninstall = UninstallModule(
            module_name,
            module_infos,
            update_process=False,
            force_uninstall=force,
            status_callback=self.__callback_uninstall_module,
            cleep_filesystem=self.cleep_filesystem,
            crash_report=self.crash_report,
            task_factory=self.task_factory,
        )
        uninstall.start()

        # blocking mode
        if self.blocking:
            # wait for end of installation
            while uninstall.is_uninstalling():
                sleep(0.25)

            # check uinstall status
            return (
                uninstall.get_status().get("status")
                == UninstallModule.STATUS_UNINSTALLED
            )

        return True

    def __callback_update_module(self, status):
        """
        Module update callback

        Args:
            status (dict): module status::

                {
                    module (string): module name
                    status (int): module process status
                    uninstall (dict): {status, prescript, postscript}
                    install (dict): {status, prescript, postscript}
                }

        """
        # save status
        if status["status"] == UpdateModule.STATUS_IDLE:
            self.status = self.STATUS_IDLE
        elif status["status"] == UpdateModule.STATUS_UPDATING:
            self.status = self.STATUS_PROCESSING
        elif status["status"] == UpdateModule.STATUS_UPDATED:
            self.status = self.STATUS_DONE
        else:
            self.status = self.STATUS_ERROR

        # save install/uninstall status at end of process
        process = ["No process output"]
        if self.status in (self.STATUS_DONE, self.STATUS_ERROR):
            # uninstall prescript
            if status["uninstall"]["prescript"]["returncode"] is not None:
                self.stdout += (
                    ["Pre-uninstall script stdout:"]
                    + status["uninstall"]["prescript"]["stdout"]
                    + [
                        "Pre-uninstall script return code: %s"
                        % status["uninstall"]["prescript"]["returncode"]
                    ]
                )
                self.stderr += ["Pre-uninstall script stderr:"] + status["uninstall"][
                    "prescript"
                ]["stderr"]
            else:
                self.stdout += ["No pre-uninstall script"]
                self.stderr += ["No pre-uninstall script"]

            # uninstall postscript
            if status["uninstall"]["postscript"]["returncode"] is not None:
                self.stdout += (
                    ["", "Post-uninstall script stdout:"]
                    + status["uninstall"]["postscript"]["stdout"]
                    + [
                        "Post-uninstall script return code: %s"
                        % status["uninstall"]["postscript"]["returncode"]
                    ]
                )
                self.stderr += ["", "Post-uninstall script stderr:"] + status[
                    "uninstall"
                ]["postscript"]["stderr"]
            else:
                self.stdout += ["No post-uninstall script"]
                self.stderr += ["No post-uninstall script"]

            # install prescript
            if status["install"]["prescript"]["returncode"] is not None:
                self.stdout += (
                    ["", "Pre-install script stdout:"]
                    + status["install"]["prescript"]["stdout"]
                    + [
                        "Pre-install script return code: %s"
                        % status["install"]["prescript"]["returncode"]
                    ]
                )
                self.stderr += ["", "Pre-install script stderr:"] + status["install"][
                    "prescript"
                ]["stderr"]
            else:
                self.stdout += ["No pre-install script"]
                self.stderr += ["No pre-install script"]

            # install postscript
            if status["install"]["postscript"]["returncode"] is not None:
                self.stdout += (
                    ["", "Post-install script stdout:"]
                    + status["install"]["postscript"]["stdout"]
                    + [
                        "Post-install script return code: %s"
                        % status["install"]["postscript"]["returncode"]
                    ]
                )
                self.stderr += ["", "Post-install script stderr:"] + status["install"][
                    "postscript"
                ]["stderr"]
            else:
                self.stdout += ["No post-install script"]
                self.stderr += ["No post-install script"]

            # process
            process = (
                ["Uninstall process:"]
                + status["uninstall"]["process"]
                + ["", "Install process:"]
                + status["install"]["process"]
            )

        # send status
        if self.status_callback:
            current_status = self.get_status()
            # inject more data
            current_status["module"] = status["module"]
            current_status["process"] = process
            self.logger.trace("current_status=%s", current_status)
            self.status_callback(current_status)

    def update_module(self, module_name, new_module_infos, force_uninstall=False):
        """
        Update specified module
        An update executes consecutively uninstall and install action

        Warning:
            This function does not handle filesystem because process could be async.
            So take care to enable/disable writings before calling it.

        Args:
            module_name (string): module name
            new_modules_infos (dict): module infos as reported in modules.json
            force_uninstall (bool): force module uninstall even if error occured

        Returns:
            bool: True if module updated (in blocking mode only)
        """
        if self.status == self.STATUS_PROCESSING:
            raise Exception("Installer is already processing")

        # check params
        if module_name is None or len(module_name) == 0:
            raise MissingParameter('Parameter "module_name" is missing')
        if not new_module_infos:
            raise MissingParameter('Parameter "new_module_infos" is missing')
        if not isinstance(new_module_infos, dict):
            raise InvalidParameter('Parameter "new_module_infos" is invalid')

        # reset status
        self.__reset_status(self.STATUS_PROCESSING)

        # launch update
        update = UpdateModule(
            module_name,
            new_module_infos,
            force_uninstall=force_uninstall,
            status_callback=self.__callback_update_module,
            cleep_filesystem=self.cleep_filesystem,
            crash_report=self.crash_report,
            task_factory=self.task_factory,
        )
        update.start()

        # blocking mode
        if self.blocking:
            # wait for end of update
            while update.is_updating():
                sleep(0.25)

            # check update status
            return update.get_status().get("status") == UpdateModule.STATUS_UPDATED

        return True
