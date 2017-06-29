#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Nightmare Fuzzing Project generic fuzzer
Generic application fuzzer
@developer: wormer
"""

import os
import sys
import json
import base64
import tempfile
import ConfigParser

from multiprocessing import Process, cpu_count

sys.path.append("../")
sys.path.append("../runtime")

import config

from nfp_log import log, debug
from nfp_queue import get_queue
from nfp_process import process_manager

try:
  from lib.interfaces import vtrace_iface, gdb_iface, asan_iface, pykd_iface, adb_iface
  has_pykd = True
except ImportError:
  from lib.interfaces import vtrace_iface, gdb_iface, asan_iface, adb_iface
  has_pykd = False

#-----------------------------------------------------------------------
class CGenericFuzzer:
  def __init__(self, cfg, section, device_id=None):
    self.cfg = cfg
    self.section = section
    self.read_configuration()
    self.device_id = device_id or 'emulator-5554'
    
    self.q = get_queue(name=self.tube_name, watch=True)
    self.delete_q = get_queue(name="delete", watch=False)
    self.crash_q = get_queue(name=self.crash_tube, watch=False)

    self.crash_info = None

  def read_configuration(self):
    if not os.path.exists(self.cfg):
      raise Exception("Invalid configuration file given")

    parser = ConfigParser.SafeConfigParser()
    parser.optionxform = str
    parser.read(self.cfg)

    if self.section not in parser.sections():
      raise Exception("Section %s does not exist in the given configuration file" % self.section)
    
    try:
      self.pre_command = parser.get(self.section, 'pre-command')
    except:
      # Ignore it, it isn't mandatory
      self.pre_command = None

    try:
      self.post_command = parser.get(self.section, 'post-command')
    except:
      # Ignore it, it isn't mandatory
      self.post_command = None

    try:
      self.command = parser.get(self.section, 'command')
    except:
      raise Exception("No command specified in the configuration file for section %s" % self.section)
    
    try:
      self.tube_name = parser.get(self.section, 'tube')
    except:
      raise
      raise Exception("No tube specified in the configuration file for section %s" % self.section)

    try:
      self.crash_tube = parser.get(self.section, 'crash-tube')
    except:
      self.crash_tube = "%s-crash" % self.tube_name
    
    try:
      self.extension = parser.get(self.section, 'extension')
    except:
      raise Exception("No extension specified in the configuration file for section %s" % self.section)
    
    try:
      self.timeout = parser.get(self.section, 'timeout')
    except:
      # Default timeout is 90 seconds
      self.timeout = 90
    
    try:
      environment = parser.get(self.section, 'environment')
      self.env = dict(parser.items(environment))
    except:
      self.env = {}
    
    try:
      self.cleanup = parser.get(self.section, 'cleanup-command')
    except:
      self.cleanup = None
    
    try:
      is_debug = parser.getboolean(self.section, 'debug')
      config.DEBUG = is_debug
    except:
      # Silently ignore the exception
      pass

    try:
      self.mode = parser.get(self.section, 'mode')
      if self.mode.isdigit():
        self.mode = int(self.mode)
    except:
      self.mode = 32

    try:
      self.windbg_path = parser.get(self.section, 'windbg-path')
    except:
      self.windbg_path = None

    try:
      self.exploitable_path = parser.get(self.section, 'exploitable-path')
    except:
      self.exploitable_path = None

    # Left "for now", for backward compatibility reasons.
    # Subject to be removed at any time. See below why.
    try:
      if parser.getboolean(self.section, 'use-gdb'):
        self.iface = gdb_iface
      else:
        self.iface = vtrace_iface
    except:
      self.iface = vtrace_iface

    try:
      self.debugging_interface = parser.get(self.section, 'debugging-interface')
      if self.debugging_interface == "pykd":
        self.iface = pykd_iface
      elif self.debugging_interface == "gdb":
        self.iface = gdb_iface
      elif self.debugging_interface == "asan":
        self.iface = asan_iface
      elif self.debugging_interface == "adb":
        self.iface = adb_iface
      else:
        self.iface = vtrace_iface
    except:
      self.debugging_interface = None
      self.iface = vtrace_iface

    try:
      self.asan_symbolizer_path = parser.get(self.section, 'asan-symbolizer-path')
    except:
      if self.debugging_interface == "asan":
        raise Exception("No asan-symbolizer-path specified in the configuration file for section %s" % self.section)

      self.asan_symbolizer_path = None

  def launch_debugger(self, timeout, command, filename, file=None):
    if command.find("@@") > -1:
        tmp_cmd = command.replace("@@", file)
        tmp_cmd = tmp_cmd.replace('$$', str(self.device_id))
        cmd = [tmp_cmd, ]
    else:
      cmd = [command, filename]

    log("Launching debugger with command %s" % " ".join(cmd))
    # if self.debugging_interface == "adb":
    #     crash = self.iface.main(cmd=cmd, device_id=self.device_id)
    
    if not has_pykd or self.iface != pykd_iface:
      self.iface.timeout = int(timeout)
      if self.debugging_interface == "asan":
        crash = self.iface.main(asan_symbolizer_path=self.asan_symbolizer_path, args=cmd)
      elif self.debugging_interface == "adb":
        crash = self.iface.main(cmd=cmd, device_id=self.device_id)
      else:
        crash = self.iface.main(cmd)
    else:
      reload(pykd_iface)
      crash = pykd_iface.main(cmd, self.timeout, mode=self.mode, windbg_path=self.windbg_path, exploitable_path=self.exploitable_path)
    return crash

  def launch_sample(self, buf):
    # Re-read configuration each time we're running the fuzzer so the 
    # new changes are immediately applied.
    self.read_configuration()

    filename = tempfile.mktemp(suffix=self.extension)
    f = open(filename, "wb")
    f.write(buf)
    f.close()

    file = filename.split('/')[-1]
    #os.putenv("NIGHTMARE_TIMEOUT", str(self.timeout))
    for key in self.env:
      debug("Setting environment variable %s=%s" % (key, self.env[key]))
      os.putenv(key, self.env[key])

    if self.pre_command is not None:
      if self.pre_command.find("@@") > -1 and self.pre_command.find("$$") > -1:
        self.pre_command = self.pre_command.replace('@@', filename)
        self.pre_command = self.pre_command.replace('$$', file)
      log('UPLOADING: %s'%self.pre_command)
      os.system(self.pre_command)

    crash = None
    for i in range(0,3):
      try:
        crash = self.launch_debugger(self.timeout, self.command, filename, file=file)
        break
      except:
        log("Exception: %s" % sys.exc_info()[1])
        continue

##################### THINGS CHANGE HERE
    if self.post_command is not None:
      if self.post_command.find("@@") > -1:
        self.post_command = self.post_command.replace('@@', file)
      if self.post_command.find("$$") > -1:
        self.post_command = self.post_command.replace('$$', self.device_id)
      log('POST: %s'%self.post_command)
      os.system(self.post_command)

    if crash is not None:
      self.crash_info = crash
      return True
    else:
      os.remove(filename)
    return False

  def fuzz(self):
    log("Launching fuzzer, listening in tube %s" % self.tube_name)
    while 1:
      value = self.q.stats_tube(self.tube_name)["current-jobs-ready"]
      debug("Total of %d job(s) in queue" % value)
      job = self.q.reserve()
      buf, temp_file = json.loads(job.body)
      buf = base64.b64decode(buf)

      debug("Launching sample %s..." % os.path.basename(temp_file))
      if self.launch_sample(buf):
        log("We have a crash, moving to %s queue..." % self.crash_tube)
        crash = self.crash_info
        d = {temp_file:self.crash_info}
        self.crash_q.put(json.dumps(d))
        self.crash_info = None

        log("$PC 0x%08x Signal %s Exploitable %s " % (crash["pc"], crash["signal"], crash["exploitable"]))
        if crash["disasm"] is not None:
          log("%08x: %s" % (crash["disasm"][0], crash["disasm"][1]))
      else:
        file_delete = os.path.basename(temp_file)
        self.delete_q.put(str(file_delete))
      
      if self.cleanup is not None:
        debug("Running clean-up command %s" % self.cleanup)
        os.system(self.cleanup)
        debug("Done")
      job.delete()
      
      if self.iface == gdb_iface:
        break

#-----------------------------------------------------------------------
def do_fuzz(cfg, section):
  try:
    fuzzer = CGenericFuzzer(cfg, section)
    fuzzer.fuzz()
  except KeyboardInterrupt:
    log("Aborted")
  except:
    log("Error: %s" % str(sys.exc_info()[1]))
    raise

#-----------------------------------------------------------------------
def main(cfg, section, device_id=None):
  procs = os.getenv("NIGHTMARE_PROCESSES")
  if procs is not None:
    process_manager(int(procs), do_fuzz, (cfg, section, device_id))
  else:
    try:
      fuzzer = CGenericFuzzer(cfg, section, device_id)
      fuzzer.fuzz()
    except:
      print "Error:", sys.exc_info()[1]

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<config file> <fuzzer> <device_id>"
  print
  print "Environment variables:"
  print "NIGHTMARE_PROCESSES     Number of processes to run at the same time"
  print

if __name__ == "__main__":
  if len(sys.argv) == 4:
    main(sys.argv[1], sys.argv[2], sys.argv[3])
  elif len(sys.argv) == 3:
    main(sys.argv[1], sys.argv[2])
  else:
    usage()
