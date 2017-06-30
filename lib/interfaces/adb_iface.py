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
from time import sleep

sys.path.append("../")
sys.path.append("../../runtime")

from crash_data import CCrashData
from nfp_log import log
from utils import run_subproc, flush_log


class ADBInterface:
    def __init__(self, logfile, cmd, device_id, file):
        self.logfile = logfile
        self.cmd = cmd[0]
        self.device_id = device_id
        self.crash_data = None
        self.running = False
        self.file = file
        self.log = None
        self.log_sbp = None
        self.cmd_start_log = 'adb -s %s shell log -p W -t nightmare Starting'% self.device_id
        self.cmd_finish_log = 'adb -s %s shell log -p W -t nightmare Finishing'% self.device_id
        self.cmd_pull_tombstone = 'adb -s %s shell'% self.device_id
        self.cmd_logcat = 'adb -s %s logcat >> %s' % (self.device_id, self.logfile)
        self.cmd_test = 'adb -s %s shell test -f /sdcard/dexs/%s'%(self.device_id, self.file)
        
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
                        if m != '':
                            if 'Fatal' in m:
                                log('[*] WE GOT A CRASH[*]')
                            log_r.append(m)
                        m = f.readline()
                    break
                l = f.readline()
        self.log = log_r
        return

    def dump_log(self):
        log_sbp = None
        try:
            log_sbp = subprocess.Popen([self.cmd_logcat], shell=True)
        except Exception, e:
            log('Exception on dump log: %s'%e)
        return log_sbp

    def run(self):
        # Log starting
        # ./adb shell log -p W -t Fuzz Starting
        flush_log(self.device_id)
        # res = 1
        # while res != 0:
        #     try:
        #         log(self.cmd_test)
        #         p = subprocess.Popen([self.cmd_test], shell=True)
        #     except Exception, e:
        #         log(e)
        #     sleep(0.05)
        #     res = p.returncode
        #     p.kill()
        self.running = True
        self.log_sbp = self.dump_log()
        t_parser = threading.Thread(target=self.parse_log, args=[])
        t_parser.start()
        run_subproc(self.cmd_start_log)
        run_subproc(self.cmd)
        run_subproc(self.cmd_finish_log)
        self.running = False
        self.log_sbp.kill()
        t_parser.join()
        return self.log

#-----------------------------------------------------------------------
def main(cmd, device_id, file):
    logfile = mkstemp()[1]
    adb = ADBInterface(logfile, cmd, device_id, file)
    data = adb.run()
    remove(logfile)
    print data
    return None

#-----------------------------------------------------------------------
def usage():
    print "Usage:", sys.argv[0], "adb <command>"    

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])