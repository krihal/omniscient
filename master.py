from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

results = {}


@app.route("/callhome", methods=["POST"])
def post():
    global results

    result = request.get_json()
    hostname = result["hostname"]
    results[hostname] = result

    return jsonify({"status": "ok"})


@app.route("/", methods=["GET"])
def get():
    return render_template("index.html", results=results)


if __name__ == '__main__':
    app.run(debug=True, port=8080)
