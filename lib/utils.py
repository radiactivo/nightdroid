from os import listdir
import os
import sys
import subprocess
import re
import time
import fnmatch

def run_subproc(cmd):
    r = subprocess.Popen([cmd], shell=True)
    r.wait()

def flush_log(device_id):
    cmd = 'adb -s %s logcat -c'%(device_id)
    r = subprocess.Popen([cmd], shell=True)
    r.wait()

def find(pattern, path):
    result = [] 
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result