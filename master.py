import json

from flask import Flask, jsonify, request
from influxdb import InfluxDBClient

app = Flask(__name__, static_folder="checks")

client = InfluxDBClient(host="localhost", port=8086)
client.switch_database("testdb")


def influx_write(result):
    if client.write_points(result):
        return True
    return False


def read_config(filename="config.json"):
    with open(filename) as fd:
        config = json.load(fd)
    return config


def get_groups(uuid, config):
    found = []
    for group in config["groups"]:
        if uuid in config["groups"][group]:
            found.append(group)
    return found


def get_tests(uuid, config):
    found = get_groups(uuid, config)
    tests = []

    for test in config["tests"]:
        testgroups = config["tests"][test]["groups"]
        for group in testgroups:
            if group in found:
                tests.append(config["tests"][test])

    return tests


@app.route("/config", methods=["GET"])
def config_get():
    args = request.args

    if "uuid" not in args:
        return jsonify({"status": "error", "message": ""}), 400

    config = read_config()

    data = get_tests(args["uuid"], config)

    if data:
        return jsonify({"status": "ok", "data": data})

    return jsonify({"status": "error", "message": ""})


@app.route("/callhome", methods=["POST"])
def callhome_post():
    args = request.args

    if "uuid" not in args:
        return jsonify({"status": "error", "message": ""}), 400

    if not get_groups(args["uuid"], read_config()):
        return jsonify({"status": "error", "message": ""}), 400

    result = request.get_json()

    if influx_write(result):
        return jsonify({"status": "ok"})

    return jsonify({"status": "error"}, 400)


if __name__ == '__main__':
    app.run(debug=True, port=8080)
