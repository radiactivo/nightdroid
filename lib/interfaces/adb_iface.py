#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Nightmare Fuzzing Project generic fuzzer
Generic application fuzzer
@developer: wormer
"""

import sys
from os import open, read, write, remove
from tempfile import mkstemp
import threading

sys.path.append("../")
sys.path.append("../../runtime")

from crash_data import CCrashData
from nfp_log import log
from utils import run_subproc, flush_log


class ADBInterface:
    def __init__(self, logfile, cmd, device_id):
        self.logfile = logfile
        self.cmd = cmd
        self.device_id = device_id
        self.crash_data = None
        self.running = False
        self.cmd_start_log = 'adb -s %s shell log -p W -t Fuzz Starting'% self.device_id
        self.cmd_finish_log = 'adb -s %s shell log -p W -t Fuzz Finishing'% self.device_id
        self.cmd_pull_tombstone = 'adb -s %s shell'% self.device_id

    def clear_log(self):
        flush_log(self.device_id)

    def parse_tombstone(self, tombstone):
        with open(tombstone, 'r+') as fd:
            text = fd.read()
            for line in text.split('\n'):
                if 'eip' in line:
                    pass

    def parse_log(self):
        while self.running:
            with open(self.logfile, 'r+') as f:
                l = fd.readline()
                if 'Fatal signal' in l:
                    pass
    def dump_log(self):
        run_subproc('adb - s %s logcat >> %s' % (self.device_id, self.logfile))
        
    def run(self):
        # Log starting
        # ./adb shell log -p W -t Fuzz Starting
        self.running = True
        t_log = threading.Thread(target=self.dump_log)
        t_log.start()
        t_parser = threading.Thread(target=self.parse_log, args=[])
        run_subproc(str(self.cmd_start_log))
        run_subproc(str(self.cmd))
        run_subproc(str(self.cmd_finish_log))
        t_log.join()
        return None

#-----------------------------------------------------------------------
def main(cmd, device_id):
    logfile = mkstemp()[1]
    log("Logfile in adb %s: %s" % (device_id,logfile))
    adb = ADBInterface(logfile, cmd, device_id)
    data = adb.run()
    remove(logfile)
    return data

#-----------------------------------------------------------------------
def usage():
    print "Usage:", sys.argv[0], "adb <command>"    

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])