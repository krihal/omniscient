from flask import Flask, jsonify, request
from influxdb import InfluxDBClient

app = Flask(__name__, static_folder="checks")

results = {}
client = InfluxDBClient(host="localhost", port=8086)
client.switch_database("testdb")


def influx_write(result):
    if client.write_points(result):
        return True
    return False


@app.route("/config", methods=["GET"])
def config_get():
    try:
        with open("worker.yaml") as fd:
            data = fd.read()
    except Exception as e:
        return jsonify({"status": "error", "message": f"{e}"})

    return jsonify({"status": "ok", "yaml": data})


@app.route("/callhome", methods=["POST"])
def callhome_post():
    global results

    result = request.get_json()

    if influx_write(result):
        return jsonify({"status": "ok"})

    return jsonify({"status": "error"}, 400)


if __name__ == '__main__':
    app.run(debug=True, port=8080)
