#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Nightmare Fuzzing Project generic fuzzer
Generic application fuzzer
@developer: wormer
"""

import sys
from os import read, write, remove
from tempfile import mkstemp
import threading
import subprocess

sys.path.append("../")
sys.path.append("../../runtime")

from crash_data import CCrashData
from nfp_log import log
from utils import run_subproc, flush_log


class ADBInterface:
    def __init__(self, logfile, cmd, device_id):
        self.logfile = logfile
        self.cmd = cmd[0]
        self.device_id = device_id
        self.crash_data = None
        self.running = False
        self.cmd_start_log = 'adb -s %s shell log -p W -t nightmare Starting'% self.device_id
        self.cmd_finish_log = 'adb -s %s shell log -p W -t nightmare Finishing'% self.device_id
        self.cmd_pull_tombstone = 'adb -s %s shell'% self.device_id
        self.log = None

    def clear_log(self):
        flush_log(self.device_id)

    def parse_tombstone(self, tombstone):
        with open(tombstone, 'r+') as fd:
            text = fd.read()
            for line in text.split('\n'):
                if 'eip' in line:
                    pass

    def parse_log(self):
        log_r = []
        with open(self.logfile, 'r') as f:
            l = f.readline()
            while self.running:
                if 'nightmare' in l:
                    m = f.readline()
                    while 'nightmare' not in m:
                        log_r.append(m)
                        m = f.readline()
                    self.log = log_r
                    break
                l = f.readline()
        log('[*] PARSE KILLED [*]')
        return

    def dump_log(self):
        log_sbp = subprocess.Popen([str('adb -s %s logcat >> %s' % (self.device_id, self.logfile))], shell=True)
        while self.running:
            pass
        log_sbp.kill()
        log('[*] DUMP KILLED [*]')

    def run(self):
        # Log starting
        # ./adb shell log -p W -t Fuzz Starting
        flush_log(self.device_id)
        self.running = True
        t_log = threading.Thread(target=self.dump_log)
        t_log.start()
        t_parser = threading.Thread(target=self.parse_log, args=[])
        t_parser.start()
        run_subproc(self.cmd_start_log)
        run_subproc(self.cmd)
        run_subproc(self.cmd_finish_log)
        self.running = False
        t_log.join()
        log('One finito...')
        t_parser.join()
        log(''.join(self.log))
        log('Arrived???')
        return None

#-----------------------------------------------------------------------
def main(cmd, device_id):
    logfile = mkstemp()[1]
    adb = ADBInterface(logfile, cmd, device_id)
    data = adb.run()
    remove(logfile)
    return data

#-----------------------------------------------------------------------
def usage():
    print "Usage:", sys.argv[0], "adb <command>"    

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])