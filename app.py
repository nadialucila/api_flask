from flask import Flask

app = Flask(__name__)

@app.route("/", methods=["GET"])
def inicio():
    return {}

app.run(debug=True, port=5000)