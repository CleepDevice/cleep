#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import subprocess
import time
from gevent import sleep
from threading import Timer, Thread, Event

try:  # pragma: no cover
    from Queue import Queue, Empty
except ImportError:  # pragma: no cover
    from queue import Queue, Empty  # python 3.x
import os
from signal import SIGKILL
import logging
import re

ON_POSIX = "posix" in sys.builtin_module_names


def get_env(custom_env):
    """
    Return custom env for command execution

    Args:
        custom_env (dict): custom env

    Returns:
        dict: custom env
    """
    env = os.environ.copy()

    for key, val in custom_env.items():
        if key not in env:
            env[key] = val

    return env


def set_opts(custom_opts, default_opts):
    """
    Return opts mixing custom opts with default ones

    Args:
        custom_opts (dict): custom options (usually specified by user)
        default_opts (dict): defaut options

    Returns:
        dict: options
    """
    opts = {}

    env = custom_opts.get('env', {})
    for key, default in default_opts.items():
        opts[key] = custom_opts.get(key) or default_opts.get(key)

    # specific case for exec_dir that should be overwritten by APP_BIN_PATH from env
    opts['exec_dir'] = opts['exec_dir'] or env.get('APP_BIN_PATH')

    return opts


class EndlessConsole(Thread):
    """
    Helper class to execute long command line (system update...)
    This kind of console doesn't kill command line after timeout. It just let command running
    until end of it or if user explicitely requests to stop (or kill) it.

    This class implements thread and is non blocking unless you use join function after starting it::

        c = EndlessConsole(mycmd, myclb, myendclb)
        c.join()

    Note:
        Subprocess output async reading copied from https://stackoverflow.com/a/4896288
    """

    DEFAULT_OPTS = {
        'exec_dir': None,
        'delay': 0.2,
        'env': {},
    }

    def __init__(self, command, callback, callback_end=None, opts=DEFAULT_OPTS):
        """
        Constructor

        Args:
            command (string|list): command to execute. It is advised to use list version.
            callback (function): callback when message is received (the function will be called with 2
                                 arguments: stdout (string) and stderr (string)),
            callback_end (function): callback when process is terminated (the function will be called,
                                     with 2 arguments: return code (string) and killed (bool)),
            opts (dict): command options::

                {
                    exec_dir (str): Command line execution dir. Use APP_BIN_PATH from env if specified and exec_dir not set (defaut None),
                    delay (double): Delay between std outputs checks (default 0.20),
                    env (dict): Command line env vars to inject during command execution. get_env() function can be called to
                                fill this option (default {}),
                }

        """
        Thread.__init__(
            self,
            daemon=True,
            name=f"endlessconsole-{getattr(callback, '__name__', 'unamed')}",
        )

        # members
        self.command = command
        self.callback = callback
        self.callback_end = callback_end
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)
        self.stopped = Event()
        self.killed = False
        self.__start_time = 0
        self.__stdout_queue = Queue()
        self.__stderr_queue = Queue()
        self.__stdout_thread = None
        self.__stderr_thread = None
        self.__opts = set_opts(opts, self.DEFAULT_OPTS)

    def __del__(self):
        """
        Destructor
        """
        self.__stop()

    def __enqueue_output(self, output, queue):
        for line in iter(output.readline, b""):
            if self.stopped.is_set():
                break
            queue.put(line.decode("utf-8").rstrip())
        try:
            output.close()
        except Exception:  # pragma: no cover
            pass

    def get_start_time(self):
        """
        Return process start time

        Returns:
            float: start timestamp (with milliseconds)
        """
        return self.__start_time

    def __stop(self):
        """
        Stop command line execution
        """
        self.stopped.set()

    def stop(self):
        """
        Kill alias
        """
        self.kill()

    def kill(self):
        """
        Stop command line execution
        """
        self.logger.debug("Process killed manually")
        self.killed = True
        self.__stop()

    def __send_stds(self):
        """
        Read queues and send outputs if available

        Returns:
            True if something sent, False otherwise
        """
        if not self.callback:
            return False

        stdout = None
        stderr = None

        try:
            stdout = self.__stdout_queue.get_nowait()
        except Empty:
            pass
        except Exception:  # pragma: no cover
            self.logger.exception("Error getting stdout queue")

        try:
            stderr = self.__stderr_queue.get_nowait()
        except Empty:
            pass
        except Exception:  # pragma: no cover
            self.logger.exception("Error getting stderr queue")

        if stdout is not None or stderr is not None:
            try:
                self.callback(stdout, stderr)
            except Exception:
                self.logger.exception(
                    "Exception occured during EndlessCommand callback:"
                )
            return True

        return False

    def run(self):
        """
        Console process
        """
        # launch command
        return_code = None
        self.__start_time = time.time()
        shell = isinstance(self.command, str)

        proc = subprocess.Popen(
            self.command,
            shell=shell,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=ON_POSIX,
            preexec_fn=os.setsid,
            cwd=self.__opts.get('exec_dir'),
            env=get_env(self.__opts.get('env')),
        )
        pid = proc.pid
        self.logger.trace("PID=%d", pid)

        if self.callback:
            # async stdout reading
            self.__stdout_thread = Thread(
                target=self.__enqueue_output,
                args=(proc.stdout, self.__stdout_queue),
                daemon=True,
                name="endlessconsole-stdout",
            )
            self.__stdout_thread.start()

            # async stderr reading
            self.__stderr_thread = Thread(
                target=self.__enqueue_output,
                args=(proc.stderr, self.__stderr_queue),
                daemon=True,
                name="endlessconsole-stderr",
            )
            self.__stderr_thread.start()

        # wait for end of command line
        while not self.stopped.is_set():
            # check process status
            proc.poll()

            # read outputs and trigger callback
            self.__send_stds()

            # check end of command
            if proc.returncode is not None:
                return_code = proc.returncode
                self.logger.debug(
                    "Process is terminated with return code %s", proc.returncode
                )
                break

            # pause
            sleep(self.__opts.get('delay', 0.2))

        # purge queues
        self.logger.trace("Purging outputs...")
        count = 0
        while self.__send_stds() or count <= 5:
            self.logger.trace(" purging...")
            count += 1
            sleep(0.05)
        self.logger.trace("Purge completed")

        # make sure all stds are closed
        try:
            proc.stdout.close()
        except Exception:  # pragma: no cover
            pass
        try:
            proc.stderr.close()
        except Exception:  # pragma: no cover
            pass

        # make sure process (and child processes) is really killed
        if self.killed and pid != 1:
            try:
                if ON_POSIX:
                    os.killpg(os.getpgid(pid), SIGKILL)
                else:  # pragma: no cover
                    proc.kill()
            except Exception:  # pragma: no cover
                pass
        else:
            try:
                proc.wait(timeout=2.0)
            except Exception:  # pragma: no cover
                os.kill(pid, SIGKILL)

        # process is over
        self.stopped.set()

        # stop callback
        if self.callback_end:
            self.logger.trace("Call end callback")
            try:
                self.callback_end(return_code, self.killed)
            except Exception:
                self.logger.exception(
                    "Exception occured during EndlessCommand end callback:"
                )


class Console:
    """
    Helper class to execute command lines.
    You can execute command right now using command method or after a certain amount of time using command_delayed
    """

    DEFAULT_OPTS = {
        'exec_dir': None,
        'env': {},
    }

    def __init__(self):
        """
        Constructor
        """
        # members
        self.timer = None
        self.__callback = None
        self.encoding = sys.getfilesystemencoding()
        self.last_return_code = None
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)

    def __del__(self):
        """
        Destroy console object
        """
        if self.timer:  # pragma: no cover
            self.timer.cancel()

    def __process_lines(self, lines):
        """
        Remove end of line char for given lines and convert lines to unicode

        Args:
            lines (list): list of lines

        Results:
            list: input list of lines with eol removed
        """
        return [line.decode("utf-8").rstrip() for line in lines]

    def get_last_return_code(self):
        """
        Return last executed command return code

        Warning:
            DEPRECATED: use returncode value from command result instead of calling this function

        Returns:
            int: return code (can be None)
        """
        return self.last_return_code

    def command(self, command, timeout=2.0, opts=DEFAULT_OPTS):
        """
        Execute specified command line with auto kill after timeout

        Note:
            This function is blocking

        Args:
            command (string|list): command to execute. It is advised to use list version.
            timeout (float): wait timeout before killing process and return command result (default 2s)
            opts (dict): command options::

                {
                    exec_dir (str): Command line execution dir. Use APP_BIN_PATH from env if specified and exec_dir not set (defaut None),
                    env (dict): Command line env vars to inject during command execution. get_env() function can be called to
                                fill this option (default {}),
                }

        Returns:
            dict: result of command::

                {
                    returncode (int): command return code
                    error (bool): True if error occured,
                    killed (bool): True if command was killed,
                    stdout (list): command line output
                    stderr (list): command line error
                }

        """
        opts = set_opts(opts, self.DEFAULT_OPTS)
        shell = isinstance(command, str)

        self.logger.trace('Launch command "%s"', command)
        # check params
        if timeout is None or timeout <= 0.0:
            raise Exception("Timeout is mandatory and must be greater than 0")

        # launch command
        proc = subprocess.Popen(
            command,
            shell=shell,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=ON_POSIX,
            preexec_fn=os.setsid,
            cwd=opts.get('exec_dir'),
            env=get_env(opts.get('env')),
        )
        pid = proc.pid

        # wait for end of command line
        done = False
        start = time.time()
        killed = False
        return_code = None
        while not done:
            # check if command has finished
            proc.poll()
            if proc.returncode is not None:
                # command terminated
                self.logger.trace(
                    "Command terminated with returncode %s", proc.returncode
                )
                return_code = proc.returncode
                self.last_return_code = return_code
                done = True
                break

            # check timeout
            if time.time() > (start + timeout):
                # timeout is over, kill command
                killed = True
                break

            # pause
            sleep(0.125)

        # prepare result
        result = {
            "returncode": return_code,
            "error": False,
            "killed": killed,
            "stdout": [],
            "stderr": [],
        }
        if not killed:
            result["stderr"] = self.__process_lines(proc.stderr.readlines())
            result["error"] = len(result["stderr"]) > 0
            result["stdout"] = self.__process_lines(proc.stdout.readlines())
        self.logger.trace("Result: %s" % result)

        # make sure all stds are closed
        try:
            proc.stdout.close()
        except Exception:  # pragma: no cover
            pass
        try:
            proc.stderr.close()
        except Exception:  # pragma: no cover
            pass

        # make sure process is really terminated
        #try:
        #    self.logger.debug('Wait for process to stop')
        #    proc.wait(timeout=.5)
        #except Exception as error:  # pragma: no cover
        #    self.logger.debug('Error waiting process to stop: %s', error)
        #    os.kill(pid, SIGKILL)
        if killed:
            pgid = os.getpgid(pid)
            self.logger.debug(
                "Timeout over, kill command for PID=%s PGID=%s", pid, pgid
            )
            try:
                if ON_POSIX:
                    os.killpg(pgid, SIGKILL)
                else:  # pragma: no cover
                    proc.kill()
                proc.wait(timeout=5.0)
            except Exception:  # pragma: no cover
                pass

        # trigger callback (used for delayed command)
        if self.__callback:
            self.__callback(result)

        return result

    def command_delayed(self, command, delay, timeout=2.0, callback=None):
        """
        Execute specified command line after specified delay

        Args:
            command (string|list): command to execute. It is advised to use list version.
            delay (int): time to wait before executing command (milliseconds)
            timeout (float): timeout before killing command
            callback (function): function called when command is over. Callback will received command
                                 result as single function parameter

        Note:
            See command function to have more details
        """
        self.__callback = callback
        self.timer = Timer(delay, self.command, [command, timeout])
        self.timer.daemon = True
        self.timer.name = "commanddelayed"
        self.timer.start()


class AdvancedConsole(Console):
    """
    Create console with advanced feature like find function to match pattern on stdout
    """

    def __init__(self):
        """
        Constructor
        """
        Console.__init__(self)

    def find(self, command, pattern, options=re.UNICODE | re.MULTILINE, timeout=2.0):
        """
        Find all pattern matches in command stdout. Found order is preserved

        Args:
            command (string|list): command to execute. It is advised to use list version.
            pattern (string): search pattern
            options (flag): regexp flags (see https://docs.python.org/3/library/re.html#module-contents)
            timeout (float): timeout before killing command

        Returns:
            list: list of matches::

                [
                    (group (string), matches in group (tuple)),
                    ...
                ]

        """
        # execute command
        res = self.command(command, timeout)
        if res["returncode"] != 0:
            # command failed
            return []

        # parse command output
        content = "\n".join(res["stdout"])
        return self.find_in_string(content, pattern, options)

    def find_in_string(self, string, pattern, options=re.UNICODE | re.MULTILINE):
        """
        Find all pattern matches in specified string. Found order is respected.

        Args:
            string (string): string to search in
            pattern (string): search pattern
            options (flag): regexp flags (see https://docs.python.org/2/library/re.html#module-contents)

        Returns:
            list: list of matches::

                [
                    (group (string), subgroups (tuple)),
                    ...
                ]

        """
        results = []
        matches = re.finditer(pattern, string, options)

        for _, match in enumerate(matches):
            group = match.group().strip()
            if len(group) > 0 and len(match.groups()) > 0:
                results.append((group, match.groups()))

        return results
