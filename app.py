from flask import Flask, jsonify, render_template
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


@app.route("/")
def index():
    return render_template("index.html")
    

@app.route("/lyrics")
def get_lyrics():
   
    return jsonify({"status": 503, "message": "Access to the API has been temporarily disabled. Please check the main route (/) for more details."}), 503


@app.route("/robots.txt")
def robots():
    return "User-agent: *\nDisallow: /\n", 200, {"Content-Type": "text/plain"}
