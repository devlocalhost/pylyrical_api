import os
import hmac
import hashlib
import subprocess

import requests

from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

import scraper
from exceptions import (
    ScrapeError,
    RequestConnectionError,
    NoResults,
    RequestTimeoutError,
)

load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

APP_SECRET_TOKEN = os.environ.get("APP_SECRET_TOKEN")
API_SCRAPER_URL = os.environ.get("API_SCRAPER_URL")

WEBSITE_MODE = os.getenv("WEBSITE_MODE")


if WEBSITE_MODE == "debug":
    print("[PYLYRICAL] DEBUG = True")
    app.config["DEBUG"] = True

    print("[PYLYRICAL] TEMPLATES_AUTO_RELOAD = True")
    app.config["TEMPLATES_AUTO_RELOAD"] = True


class GeniusAPI:
    """
    making things a bit easier
    """

    def __init__(self, api_url, token):
        self.api_url = api_url
        self.token = token

    def scrape(self, link):
        lyrics = []

        try:
            html_data = scraper_h.scrape(link)

            soup = BeautifulSoup(html_data, "html.parser")

            for lyricheader in soup.select("div[class*=LyricsHeader__Container]"):
                lyricheader.decompose()

            for lyrics_data in soup.select("div[class*=Lyrics__Container]"):
                for tag in lyrics_data.select("a, span"):
                    tag.unwrap()

                for br in lyrics_data.find_all("br"):
                    br.replace_with("\n")

                text = lyrics_data.get_text()
                text = text.replace("\\n", "\n").strip()
                lyrics.append(text + "\n")

            if lyrics:
                lyrics = "".join(lyrics)
                lyrics = (
                    lyrics.replace("\n(\n", "(")
                    .replace("\n)", ")")
                    .replace("(\n", "(")
                    .replace("& \n", "& ")
                    .replace("\n]", "]")
                )

            return lyrics

            # raise ScrapeError(
            #     f"Could not scrape data. Did the HTML change? Please open an issue at https://github.com/devlocalhost/pylyrical_api and paste this: URL: {link}. Data text: ```{req.text}```"
            # )

        except requests.exceptions.ConnectionError as exc:
            raise RequestConnectionError(
                "Could not connect to scraper backend. Try again later?"
            ) from exc

        except requests.exceptions.Timeout as exc:
            raise RequestTimeoutError(
                "Could not scrape. Request timed out. Try again?"
            ) from exc

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
            header_image_url = result["response"]["hits"][0]["result"][
                "header_image_url"
            ]

            return (artists, title, genius_url, header_image_url)

        raise NoResults(
            f"'{query_term}' did not give any results, Please try a different term."
        )


genius_api = GeniusAPI(
    api_url="https://api.genius.com/search/",
    token=os.environ["GENIUS_API_TOKEN"],
)
scraper_h = scraper.Scraper(
    account_id=os.environ["ACCOUNT_ID"], api_token=os.environ["API_TOKEN"]
)


def verify_signature(secret_token, signature_header, payload_body):
    if not signature_header:
        return False

    hash_object = hmac.new(
        secret_token.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()

    if hmac.compare_digest(expected_signature, signature_header):
        return True

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
            scraped_lyrics = genius_api.scrape(data[2])

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
                    "lyrics": scraped_lyrics,
                    "cover_image": data[3],
                }
            ),
            200,
        )

    return jsonify({"status": 400, "message": "Missing parameter 'q'."}), 400
