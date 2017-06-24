from crash_data import CCrashData


class ADBInterface():
	def __init__(self, log_pipe, ):
		pass

	def clear_log():

	def parse_logs():
		recording = False
		crash = None
		buff = []
		while 'W Fuzz    : Starting' not in fd.readline():
			pass

		while l != 'W Fuzz    : Finishing':
			l = fd.readline()
			buff.append(l)
		
		if crash:
			recover_tombstone()
			clean_tombstone()

	def dump_log():
		pass	
	def run():
		# Log starting
		# ./adb shell log -p W -t Fuzz Starting
		pass

#-----------------------------------------------------------------------
def main(args):
	logfile = mkstemp()[1]
	adb = ADBInterface()
	return adb.run()

#-----------------------------------------------------------------------
def usage():
	print "Usage:", sys.argv[0], "adb <command>"	

if __mame__ == '__main__':
	if len(sys.argv) == 1:
    	usage()
  	else:
    	main(sys.argv[1:])