import os
import hmac
import hashlib
import requests
import subprocess

import httpx

from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

client = httpx.Client(http2=True)

APP_SECRET_TOKEN = os.environ.get("APP_SECRET_TOKEN")
API_SCRAPER_URL = os.environ.get("API_SCRAPER_URL")
USER_AGENT = "Mozilla/5.0 (Linux; Android 15; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.38 Mobile Safari/537.36"


class ScrapeError(Exception):
    """
    custom exception to raise when scrapping
    """

    pass


class TimeoutError(Exception):
    """
    error to raise when timeout
    """

    pass


class RequestConnectionError(Exception):
    """
    custom exception to raise when api cannot
    send a request/contact genius.com
    """

    pass


class NoResults(Exception):
    """
    custom exception to raise when no results
    for q (query)
    """

    pass


class GeniusAPI:
    """
    making things a bit easier
    """

    def __init__(self, api_url, token):
        self.api_url = api_url
        self.token = token
        

    def scrape(self, link):
        lyrics = []
        image = None

        try:
            req = requests.get(f"{API_SCRAPER_URL}?url={link}", timeout=15)            
            req_data = req.json()

            soup = BeautifulSoup(req_data["html"], "html.parser")
            
            for lyricheader in soup.select("div[class*=LyricsHeader__Container]"):
                lyricheader.decompose()
            
            for lyrics_data in soup.select("div[class*=Lyrics__Container]"):
                data = lyrics_data.get_text("\n")
                lyrics.append(f"{data}\n")

            if len(lyrics) != 0:
                lyrics = str("".join(lyrics)).replace("\n[", "\n\n[")

            for img in soup.find_all("img"):
                try:
                    if "1000x1000x1" in img.get("src"):
                        image = img.get("src")

                except:
                    pass

            return (lyrics, image)

            raise ScrapeError(
                f"Could not scrape data. Did the HTML change? Please open an issue at https://github.com/devlocalhost/pylyrical_api and paste this: URL: {link}. Data text: ```{req.text}```"
            )

        except requests.exceptions.ConnectionError as exc:
            raise RequestConnectionError(
                f"Could not connect to {self.api_url}. Is it down?"
            ) from exc

        except requests.exceptions.Timeout as exc:
            raise TimeoutError("Could not scrape. Request to scrape API timed out.") from exc

    def search(self, query_term):
        data = {"q": query_term}
        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            result = requests.get(
                self.api_url, params=data, headers=headers, timeout=5
            ).json()

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as exc:
            raise RequestConnectionError(
                f"Could not connect to {self.api_url}. Is it down?"
            ) from exc

        if len(result["response"]["hits"]) != 0:
            artists = result["response"]["hits"][0]["result"]["artist_names"]
            title = result["response"]["hits"][0]["result"]["title"]
            genius_url = result["response"]["hits"][0]["result"]["url"]

            return (artists, title, genius_url)

        raise NoResults(
            f"'{query_term}' did not give any results, Please try a different term."
        )


genius_api = GeniusAPI(
    api_url="https://api.genius.com/search/",
    token=os.environ["GENIUS_API_TOKEN"],
)


def verify_signature(secret_token, signature_header, payload_body):
    if not signature_header:
        return False

    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()

    if hmac.compare_digest(expected_signature, signature_header):
        return True

    else:
        return False


@app.after_request
def add_cors_headers(response):
    # response.headers['Content-Type'] = 'application/json'
    # fuck this shit breaks the main page lol

    response.headers["Access-Control-Allow-Origin"] = "*"

    return response


@app.route("/autod", methods=["POST"])
def autod():
    signature = request.headers.get("X-Hub-Signature-256")
    payload = request.get_data()

    if verify_signature(APP_SECRET_TOKEN, signature, payload):
        subprocess.Popen([os.path.abspath("auto-deploy.sh")])

        return "", 200

    else:
        return "", 403


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/lyrics", methods=["GET"])
def get_lyrics():
    query = request.args.get("q")

    if query:
        try:
            data = genius_api.search(str(query))

        except RequestConnectionError as request_exc:
            return (
                jsonify(
                    {
                        "status": 502,
                        "message": str(request_exc),
                        "exception": request_exc.__class__.__name__,
                    }
                ),
                502,
            )

        except NoResults as results_exc:
            return (
                jsonify(
                    {
                        "status": 404,
                        "message": str(results_exc),
                        "exception": results_exc.__class__.__name__,
                    }
                ),
                404,
            )

        try:
            scrape_data = genius_api.scrape(data[2])

        except ScrapeError as scrape_exc:
            return (
                jsonify(
                    {
                        "status": 500,
                        "message": str(scrape_exc),
                        "exception": scrape_exc.__class__.__name__,
                    }
                ),
                500,
            )

        return (
            jsonify(
                {
                    "status": 200,
                    "artists": data[0],
                    "title": data[1],
                    "source": data[2],
                    "lyrics": scrape_data[0],
                    "cover_image": scrape_data[1],
                }
            ),
            200,
        )

    return jsonify({"status": 400, "message": "Missing parameter 'q'."}), 400
