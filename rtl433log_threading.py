#rtl433log
import sys
import subprocess 
import threading
import Queue
import json
import sqlite3

class PipeOutputQueue(threading.Thread):

	def __init__ (self,cmd):
		threading.Thread.__init__(self)
		self.cmd = cmd
		self.daemon = True
		self.output = Queue.Queue()
		self.rc = -1

	def run(self):
		process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, bufsize=1)

		while True:
			line = process.stdout.readline()
			if line == '' and process.poll() is not None:
				break
			if line:
				self.output.put(line)

		# Note return code
		rc = process.poll()
		self.rc = rc

	def status(self):
		return self.rc

def main():

	dbfile = '/dev/shm/log_sensor.sqlite'
	writeToDB = True
	cmd = ['/usr/local/bin/rtl_433', '-F', 'json', '-R', '8', '-R', '54', '-R', '16', '-R', '12']
	#cmd = ['ping', '-c', '10', 'www.google.com']

	if (writeToDB):
		conn = sqlite3.connect(dbfile)
		c = conn.cursor()

		# Create table if it does not exist already
		sqlStmt = """
		CREATE TABLE IF NOT EXISTS log_sensor (
			ID INTEGER PRIMARY KEY AUTOINCREMENT
			,ModelNm VARCHAR NOT NULL
			,HouseCd INTEGER NOT NULL
			,ChannelCd INTEGER NULL
			,BatteryCd VARCHAR NOT NULL
			,TempC DECIMAL(6,2) NOT NULL
			,HumidityPct DECIMAL(6,2) NULL
			,Timestamp INTEGER(4) NOT NULL DEFAULT (strftime('%s', 'now'))
		);"""

		#print 'sqlStmt = "' + sqlStmt + '"'
		c.execute(sqlStmt)
		conn.commit()

	# Initialize PipeOutputQueue thread
	thread = PipeOutputQueue(cmd)
	thread.start()

	lastLine = ''
	write_count = 0

	# Poll thread output until return code indicates process is completed
	while True:

		try:
			line = thread.output.get(timeout = 1)
			if (line.find('time') != -1):

				# filter out any duplicate signals
				if line <> lastLine:
					lastLine = line
					data = json.loads(line)

					print "[DATA]" + line

					tempC = str(data['temperature_C']) if 'temperature_C' in data else '0'
					model = str(data['model']) if 'model' in data else 'Unknown'
					id = str(data['id']) if 'id' in data else '0'
					channel = str(data['channel']) if 'channel' in data else '0'
					battery = str(data['battery']) if 'battery' in data else ''
					humidity = str(data['humidity']) if 'humidity' in data else '0'

					#print "tempC = " + tempC
					#print "model = " + model
					#print "id = " + id
					#print "channel = " + channel
					#print "battery = " + battery
					#print "humidity = " + humidity

					if (writeToDB):
						print 'Writing to ' + dbfile
						c.execute("""INSERT INTO log_sensor (ModelNm, HouseCd, ChannelCd, BatteryCd, TempC, HumidityPct) VALUES (?,?,?,?,?,?);""",\
							(model, id, channel, battery, tempC, humidity))
						conn.commit()
						write_count += 1

					if (write_count >= 100):
						print "Looking for data to purge..."

						# remove old data
						c.execute("DELETE FROM log_sensor WHERE datetime(Timestamp, 'unixepoch', 'localtime') < date('now','-3 day')")
						purge_count = c.rowcount
						write_count = 0

						print 'Purged %s rows' % (purge_count)

						# shrink size of db
						if purge_count <> 0:
							c.execute("VACUUM")

		except Queue.Empty:
			#check to see if thread is still running
			if thread.status() <> -1:
				break

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print >> sys.stderr, '\nExiting by user request.\n'
		sys.exit(0)
