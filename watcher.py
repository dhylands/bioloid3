#!/usr/bin/env python3
"""
Implements a watcher process which kills and relaunches a server when any source files change.

To use:

    ./watcher.py program arguments
"""

import os
import signal
import sys
import time
import traceback


def entry_newer_than(entry: os.DirEntry, timestamp: float) -> bool:
    """Checks if directory entry is newer than `timestamp`."""
    if entry.is_dir():
        if entry.name == '.direnv':
            # This is the python virtual environment directory associated with direnv,
            # which we can skip
            return False
        if entry.name == '__pycache__':
            # This is where python stores the compiled byte-code - ignore
            return False
        return dir_newer_than(entry.path, timestamp)
    try:
        if os.path.getmtime(entry.path) > timestamp:
            print(
                '===========================================================')
            print('File:', entry.path, 'was modified')
            return True
    except OSError:
        # File doesn't exist - this means it was removed bwteen the time os.walk
        # was called and getmtime was called.
        pass
    return False


def dir_newer_than(dirname: str, timestamp: float) -> bool:
    """Recursively tests if any file in `dir` is neweer than `timestamp`."""
    with os.scandir(dirname) as it:
        for entry in it:
            if entry_newer_than(entry, timestamp):
                return True
    return False


def relaunch():
    """Relaunches the process when it dies."""
    cmd = sys.argv[1]
    args = sys.argv[1:]
    print('cmd =', cmd)
    print('args =', args)
    print('Launching', cmd, args)
    pid = os.spawnv(os.P_NOWAIT, cmd, args)
    print('Launched process', pid)
    return pid


def start_watcher(pid) -> None:
    """Starts a file watcher, which shutsdown the server when changes are detected."""
    try:
        print("Watching for changes...")
        print('-----------------------------------------------------------')
        start_time = time.time()
        while True:
            if dir_newer_than('.', start_time):
                # A file was modified
                print('Killing pid', pid)
                os.kill(pid, signal.SIGTERM)
                print("Waiting for", pid, 'to exit')
                os.waitpid(pid, 0)
                pid = relaunch()
                print("Watching for changes...")
                print(
                    '-----------------------------------------------------------'
                )
                start_time = time.time()
                continue
            exited_pid, _status = os.waitpid(pid, os.WNOHANG)
            if exited_pid != 0:
                print('Process exited')
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(exc)
        traceback.print_tb(exc.__traceback__)
        print('-----')


def main() -> None:
    """Main program"""
    pid = relaunch()
    start_watcher(pid)


if __name__ == '__main__':
    main()
