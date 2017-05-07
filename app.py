#app.py
from flask import Flask, request, render_template, make_response
import sqlite3
import StringIO
import csv

app = Flask(__name__)
app.config.from_object('config')
# Now we can access the configuration variables via app.config["VAR_NAME"]

dbfile = app.config["DBFILE"]

@app.route("/")
def index():

	# Connect to db
	conn = sqlite3.connect(dbfile)
	c = conn.cursor()

	# Get list of sensors and today's reading summary
	c.execute("SELECT grp.ModelNm, grp.HouseCd, grp.Dte "\
		+",strftime('%H:%M:%S', datetime(lst.Timestamp, 'unixepoch', 'localtime')) AS LstTime "\
		+",32+9.0/5*lst.TempC AS LstTempF "\
		+",lst.HumidityPct "\
		+",lst.BatteryCd "\
		+",strftime('%H:%M:%S', datetime(mnt.Timestamp, 'unixepoch', 'localtime')) AS MinTempTime "\
		+",32+9.0/5*mnt.TempC AS MinTemp "\
		+",strftime('%H:%M:%S', datetime(mxt.Timestamp, 'unixepoch', 'localtime')) AS MaxTempTime "\
		+",32+9.0/5*mxt.TempC AS MaxTemp "\
		+"FROM ( "\
		+"SELECT a.ModelNm, a.HouseCd, strftime('%Y-%m-%d', datetime(a.Timestamp, 'unixepoch', 'localtime')) AS Dte "\
		+",(SELECT b.Id FROM log_sensor b WHERE a.ModelNm = b.ModelNm AND a.HouseCd = b.HouseCd AND strftime('%Y-%m-%d', datetime(a.Timestamp, 'unixepoch', 'localtime')) = strftime('%Y-%m-%d', datetime(b.Timestamp, 'unixepoch', 'localtime')) ORDER BY b.Timestamp DESC LIMIT 1) AS LstId "\
		+",(SELECT b.Id FROM log_sensor b WHERE a.ModelNm = b.ModelNm AND a.HouseCd = b.HouseCd AND strftime('%Y-%m-%d', datetime(a.Timestamp, 'unixepoch', 'localtime')) = strftime('%Y-%m-%d', datetime(b.Timestamp, 'unixepoch', 'localtime')) ORDER BY b.TempC ASC, b.Timestamp ASC LIMIT 1) AS MinId "\
		+",(SELECT b.Id FROM log_sensor b WHERE a.ModelNm = b.ModelNm AND a.HouseCd = b.HouseCd AND strftime('%Y-%m-%d', datetime(a.Timestamp, 'unixepoch', 'localtime')) = strftime('%Y-%m-%d', datetime(b.Timestamp, 'unixepoch', 'localtime')) ORDER BY b.TempC DESC, b.Timestamp DESC LIMIT 1) AS MaxId "\
		+"FROM log_sensor a "\
		+"WHERE 1 = 1 "\
		+"AND strftime('%Y-%m-%d', datetime(a.Timestamp, 'unixepoch', 'localtime')) = '2017-04-25' "\
		#+"AND strftime('%Y-%m-%d', datetime(a.Timestamp, 'unixepoch', 'localtime')) = strftime('%Y-%m-%d', datetime(strftime('%s', 'now'), 'unixepoch', 'localtime')) "\
		+"GROUP BY 1, 2, 3 "\
		+") grp "\
		+"LEFT JOIN log_sensor lst "\
		+"ON grp.LstId = lst.Id "\
		+"LEFT JOIN log_sensor mnt "\
		+"ON grp.MinId = mnt.Id "\
		+"LEFT JOIN log_sensor mxt "\
		+"ON grp.MaxId = mxt.Id "\
		+"ORDER BY 1, 2")

	# Convert results to dict
	results = c.fetchall()
	sensor_list = []
	for row in results:
		sensor_list.append({'ModelNm': row[0], 'HouseCd':row[1], 'Dte':row[2], 'LstTime':row[3], 'LstTempF':row[4], 'HumidityPct':row[5], 'BatteryCd':row[6], 'MinTempTime':row[7], 'MinTemp':row[8], 'MaxTempTime':row[9], 'MaxTemp':row[10]})

	return render_template("index.html", SensorLst = sensor_list)

@app.route("/hourly", methods=["GET"])
def hourly():

	# Connect to db
	conn = sqlite3.connect(dbfile)
	c = conn.cursor()

	sname = request.args.get('sname')

	if sname <> None:
		c.execute("SELECT "\
			+"a.Dte "\
			+",a.Hr "\
			+",strftime('%Y-%m-%d %H:%M:%S', datetime(b.Timestamp, 'unixepoch', 'localtime')) AS DteTime "\
			+",a.ModelNm "\
			+",a.HouseCd "\
			+",a.ChannelCd "\
			+",a.MinId AS Id "\
			+",b.BatteryCd "\
			+",32+9.0/5*b.TempC AS TempF "\
			+",b.HumidityPct "\
			+"FROM ( "\
			+"SELECT "\
			+"strftime('%Y-%m-%d', datetime(a.Timestamp, 'unixepoch', 'localtime')) AS Dte "\
			+",strftime('%H:00:00', datetime(a.Timestamp, 'unixepoch', 'localtime')) AS Hr "\
			+",ModelNm "\
			+",HouseCd "\
			+",ChannelCd "\
			+",MIN(Id) AS MinId "\
			+"FROM log_sensor a "\
			+"WHERE 1 = 1 " \
			+"AND strftime('%Y-%m-%d', datetime(a.Timestamp, 'unixepoch', 'localtime')) = '2017-04-25' "\
			#+"AND strftime('%Y-%m-%d', datetime(a.Timestamp, 'unixepoch', 'localtime')) = strftime('%Y-%m-%d', datetime(strftime('%s', 'now'), 'unixepoch', 'localtime')) "\
			+"AND a.ModelNm || a.HouseCd = '" + sname + "' "\
			+"GROUP BY "\
			+"strftime('%Y-%m-%d', datetime(a.Timestamp, 'unixepoch', 'localtime')) "\
			+",strftime('%H', datetime(a.Timestamp, 'unixepoch', 'localtime')) "\
			+",ModelNm "\
			+",HouseCd "\
			+",ChannelCd "\
			+") a "\
			+"JOIN log_sensor b "\
			+"ON a.MinId = b.Id "\
			+"ORDER BY a.ModelNm, a.HouseCd, a.Dte, a.Hr")

		# Convert results to dict
		results = c.fetchall()
		hourly_list = []
		for row in results:
			hourly_list.append({'Dte': row[0], 'Hr':row[1], 'DteTime':row[2], 'ModelNm':row[3], 'HouseCd':row[4], 'ChannelCd':row[5], 'Id':row[6], 'BatteryCd':row[7], 'TempF':row[8], 'HumidityPct':row[9]})

		return render_template("hourly.html", HourlyLst = hourly_list, SensorNm = sname)
	else:
		return "Invalid querystring"

@app.route("/export", methods=["GET"])
def export():

	# Connect to db
	conn = sqlite3.connect(dbfile)
	c = conn.cursor()
	
	exportDteNbr = request.args.get('d', None)
	
	# If there is no date in the args, display a table of export dates to choose from
	if exportDteNbr == None:
	
		# Get list of report dates
		c.execute("SELECT strftime('%Y-%m-%d', datetime(Timestamp, 'unixepoch', 'localtime')) AS Dte "\
			+",strftime('%Y%m%d', datetime(Timestamp, 'unixepoch', 'localtime')) AS DteNbr "\
			+",COUNT(*) AS RecordCt "\
			+",MIN(strftime('%H:%M:%S',datetime(Timestamp, 'unixepoch', 'localtime'))) AS MinTime "\
			+",MAX(strftime('%H:%M:%S',datetime(Timestamp, 'unixepoch', 'localtime'))) AS MaxTime "\
			+"FROM log_sensor "\
			+"GROUP BY strftime('%Y-%m-%d', datetime(Timestamp, 'unixepoch', 'localtime')) "\
			+",strftime('%Y%m%d', datetime(Timestamp, 'unixepoch', 'localtime')) "\
			+"ORDER BY Dte")
	
		# Convert results to dict
		results = c.fetchall()
		export_list = []
		for row in results:
			export_list.append({'Dte': row[0], 'DteNbr':row[1], 'RecordCt':row[2], 'MinTime':row[3], 'MaxTime':row[4]})

		return render_template("export.html", ExportLst = export_list)
	
	# Otherwise, generate a csv file using date argument as a filter
	else:
		filename = 'RTL433Log-' + exportDteNbr + '.csv'
		c.execute("""SELECT Id AS RecordNbr, ModelNm, HouseCd, ChannelCd, BatteryCd, TempC, 32+9.0/5*TempC AS TempF, HumidityPct, datetime(Timestamp, 'unixepoch', 'localtime') as Timestamp FROM log_sensor WHERE strftime('%Y%m%d', datetime(Timestamp, 'unixepoch', 'localtime')) = ? ORDER BY Id""", (exportDteNbr,))
		
		# Convert resultset to CSV
		si = StringIO.StringIO()
		cw = csv.writer(si)
		cw.writerow([i[0] for i in c.description]) # heading row
		cw.writerows(c.fetchall())
		
		# Encode CSV in response
		output = make_response(si.getvalue())
		output.headers["Content-Disposition"] = "attachment; filename=" + filename
		output.headers["Content-type"] = "text/csv"
		return output

@app.route("/hello")
def hello():
	return "Hello World!"

if __name__ == "__main__":
	app.run(host='0.0.0.0', port=8080)
