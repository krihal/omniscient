import hashlib
import json
import os

from flask import Flask, jsonify, request
from influxdb import InfluxDBClient

app = Flask(__name__, static_folder="checks")

INFLUX_HOST = "localhost"
INFLUX_PORT = 8086
INFLUX_DB = "testdb"

if "INFLUX_HOST" in os.environ:
    INFLUX_HOST = os.environ["INFLUX_HOST"]
if "INFLUX_PORT" in os.environ:
    INFLUX_PORT = os.environ["INFLUX_PORT"]
if "INFLUX_DB" in os.environ:
    INFLUX_DB = os.environ["INFLUX_DB"]

client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT)
client.switch_database(INFLUX_DB)


def influx_write(result):
    if client.write_points(result):
        return True
    return False


def get_hash(filename):
    with open("checks/" + filename, "rb") as fd:
        data = fd.read()

    lines = data.split(b"\n")
    if len(lines) > 3:
        if lines[0].rstrip() == b"--- SIGNATURE START ---" and lines[2].rstrip() == b"--- SIGNATURE END ---":
            lines = lines[3:]

    data = b"\n".join(lines)
    data = data.decode()

    return hashlib.sha256(data.encode()).hexdigest()


def get_config(filename="config.json"):
    with open(filename) as fd:
        config = json.load(fd)
    return config


def get_groups(uuid, config):
    found = []
    for group in config["groups"]:
        if uuid in config["groups"][group]:
            found.append(group)
        if "*" in config["groups"][group]:
            found.append(group)

    return found


def get_tests(uuid, config):
    found = get_groups(uuid, config)
    tests = []

    for test in config["tests"]:
        testgroups = config["tests"][test]["groups"]
        for group in testgroups:
            if group in found:
                filename = config["tests"][test]["check"]
                filehash = get_hash(filename)
                config["tests"][test]["hash"] = filehash

                tests.append(config["tests"][test])

    return tests


def get_alias(uuid, config):
    if "clients" not in config:
        return uuid

    for client in config["clients"]:
        if client != uuid:
            continue
        if "alias" not in config["clients"][client]:
            return uuid
        alias = config["clients"][client]["alias"]

        if alias is None:
            return uuid
        if alias == "":
            return uuid

    return uuid


@app.route("/config", methods=["GET"])
def config_get():
    args = request.args
    config = get_config()

    if "uuid" not in args:
        return jsonify({"status": "error", "message": "Missing argument uuid"}), 400

    data = get_tests(args["uuid"], config)

    if data:
        return jsonify({"status": "ok", "data": data})

    return jsonify({"status": "error", "message": "Unknown client"})


@app.route("/callhome", methods=["POST"])
def callhome_post():
    args = request.args
    config = get_config()

    if "uuid" not in args:
        return jsonify({"status": "error", "message": ""}), 400

    uuid = args["uuid"]
    alias = get_alias(uuid, config)

    if not get_groups(uuid, config):
        return jsonify({"status": "error", "message": ""}), 400

    results = request.get_json()

    for result in results:
        result["tags"]["uuid"] = alias

    if influx_write(results):
        return jsonify({"status": "ok"})

    return jsonify({"status": "error"}, 400)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
