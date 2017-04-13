#app.py
from flask import Flask
app = Flask(__name__)
app.config.from_object('config')
# Now we can access the configuration variables via app.config["VAR_NAME"]

@app.route("/")
def hello():
    return "Hello World!"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
