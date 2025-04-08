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
USER_AGENT = "Mozilla/5.0 (Linux; Android 15; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.38 Mobile Safari/537.36"


class ScrapeError(Exception):
    """
    custom exception to raise when scrapping
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

    def __init__(self, api_url, token, user_agent):
        self.api_url = api_url
        self.token = token

        self.headers = {"User-Agent": user_agent}
        self.client = httpx.Client(http2=True)

    def scrape_cover(self, link):
        image = None

        try:
            req = self.client.get(link, timeout=5, headers=self.headers)

            soup = BeautifulSoup(req.text, "html.parser")

            for img in soup.find_all("img"):
                try:
                    if "1000x1000x1" in img.get("src"):
                        image = img.get("src")

                except:  # TypeError
                    pass

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as exc:
            raise RequestConnectionError(
                f"Could not connect to {self.api_url}. Is it down?"
            ) from exc

        return image

    def scrape_lyrics(self, link):
        song_lyrics = []

        try:
            req = self.client.get(link, timeout=5, headers=self.headers)

            for lyrics_data in BeautifulSoup(req.text, "html.parser").select(
                "div[class*=Lyrics__Container]"
            ):
                data = lyrics_data.get_text("\n")
                song_lyrics.append(f"{data}\n")

            if len(song_lyrics) != 0:
                return str("".join(song_lyrics)).replace("\n[", "\n\n[")

            raise ScrapeError(
                f"Could not scrape lyrics. Did the HTML change? Please open an issue at https://github.com/devlocalhost/pylyrical_api and paste this: URL: {link}. Data text: ```{req.text}```"
            )

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as exc:
            raise RequestConnectionError(
                f"Could not connect to {self.api_url}. Is it down?"
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

            return (artists, title, genius_url)

        raise NoResults(
            f"'{query_term}' did not give any results, Please try a different term."
        )


genius_api = GeniusAPI(
    api_url="https://api.genius.com/search/",
    token=os.environ["GENIUS_API_TOKEN"],
    user_agent=USER_AGENT,
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
            lyrics = genius_api.scrape_lyrics(data[2])

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

        cover_image = genius_api.scrape_cover(data[2])

        return (
            jsonify(
                {
                    "status": 200,
                    "artists": data[0],
                    "title": data[1],
                    "source": data[2],
                    "lyrics": lyrics,
                    "cover_image": cover_image,
                }
            ),
            200,
        )

    return jsonify({"status": 400, "message": "Missing parameter 'q'."}), 400
