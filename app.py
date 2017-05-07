#app.py
from flask import Flask, request, render_template, make_response
import sqlite3

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
			#+"AND strftime('%Y-%m-%d', datetime(a.Timestamp, 'unixepoch', 'localtime')) >= datetime('2017-04-08', '-24 hour') "\
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

@app.route("/hello")
def hello():
	return "Hello World!"

if __name__ == "__main__":
	app.run(host='0.0.0.0', port=8080)
