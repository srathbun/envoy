# -*- coding: utf-8 -*-

"""
envoy.core
~~~~~~~~~~

This module provides envoy awesomeness.
"""

import os
import shlex
import subprocess
import threading
import platform


__version__ = '0.0.2'
__license__ = 'MIT'
__author__ = 'Kenneth Reitz'

POSIX = False if platform.system() == 'Windows' else True

class Command(object):
    def __init__(self, cmd):
        self.cmd = cmd
        self.process = None
        self.out = None
        self.err = None
        self.returncode = None
        self.data = None

    def run(self, data, timeout, env):
        self.data = data
        environ = dict(os.environ).update(env or {})

        def target():

            self.process = subprocess.Popen(self.cmd,
                universal_newlines=True,
                shell=False,
                env=environ,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )

            self.out, self.err = self.process.communicate(self.data)

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            self.process.terminate()
            thread.join()
        self.returncode = self.process.returncode
        return self.out, self.err


class ConnectedCommand(object):
    def __init__(self,
        process=None,
        std_in=None,
        std_out=None,
        std_err=None):

        self._process = process
        self.std_in = std_in
        self.std_out = std_out
        self.std_err = std_out

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.kill()

    @property
    def status_code(self):
        """The status code of the process.
        If the code is None, assume that it's still running.
        """
        if self._status_code is not None:
            return self._status_code

        # investigate
        return None

    @property
    def pid(self):
        """The process' PID."""
        return self._process.pid

    def kill(self):
        """Kills the process."""
        return self._process.kill()

    def expect(self, bytes, stream=None):
        """Block until given bytes appear in the stream."""
        if stream is None:
            stream = self.std_out
        pass

    def send(self, end='\n'):
        """Sends a line to std_in."""
        #TODO: Y U LINE BUFFER
        pass

    def block(self):
        """Blocks until command finishes. Returns Response instance."""
        self._status_code = self._process.wait()



class Response(object):
    """A command's response"""

    def __init__(self, process=None):
        super(Response, self).__init__()

        self._process = process
        self.command = None
        self.std_err = None
        self.std_out = None
        self.status_code = None
        self.history = []


    def __repr__(self):
        if len(self.command):
            return '<Response [{0}]>'.format(self.command[0])
        else:
            return '<Response>'


def expand_args(command):
    """Parses command strings and returns a Popen-ready list."""

    # Prepare arguments.
    if isinstance(command, basestring):
        item = []
        cmdlist = []

        s = shlex.shlex(command, posix=POSIX)
        if not POSIX:
            s.wordchars = '{0}./\\-:'.format(s.wordchars) # added additional chars which windows sees as part of words...
        for tok in s: # we are build a parser for context, as shlex only handles tokenizing
            if (str(tok).count('"') & 1 != 0) and not POSIX:
                item.append(tok)
                while 1:
                    t = s.get_token()
                    item[-1] = '{0} {1}'.format(item[-1], t)
                    if (str(tok).count('"') & 1 != 0):
                        break
                    elif t == s.eof:
                        break
            elif tok == '=':
                item[-1] = '{0}={1}'.format(item[-1], s.get_token())
            elif tok == '|':
                cmdlist.append(item)
                item = []
            else:
                item.append(tok)
        cmdlist.append(item)

    return cmdlist


def run(command, data=None, timeout=None, env=None):
    """Executes a given commmand and returns Response.

    Blocks until process is complete, or timeout is reached.
    """

    command = expand_args(command)

    history = []
    for c in command:

        if len(history):
            # due to broken pipe problems pass only first 10MB
            data = history[-1].std_out[0:10*1024]

        cmd = Command(c)
        out, err = cmd.run(data, timeout, env)

        r = Response(process=cmd)

        r.command = c
        r.std_out = out
        r.std_err = err
        r.status_code = cmd.returncode

        history.append(r)

    r = history.pop()
    r.history = history

    return r


def connect(command, data=None, env=None):
    """Spawns a new process from the given command."""

    # TODO: support piped commands
    command_str = expand_args(command).pop()
    environ = dict(os.environ).update(env or {})

    process = subprocess.Popen(command_str,
        universal_newlines=True,
        shell=False,
        env=environ,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )

    return ConnectedCommand(process=process)
