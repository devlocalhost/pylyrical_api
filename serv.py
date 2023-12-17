import os
import requests

from flask import Flask, jsonify, request, render_template
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)


class ScrapeError(Exception):
    pass


class RequestConnectionError(Exception):
    pass


class NoResults(Exception):
    pass


class GeniusAPI:
    def __init__(self, api_url, token):
        self.api_url = api_url
        self.token = token

    def scrape_cover(self, link):
        image = None

        try:
            req = requests.get(link, timeout=5)
            req.raise_for_status()

            soup = BeautifulSoup(req.text, "html.parser")

            """
            for h in soup.find_all("img"):
                try:
                    print(h.get("src") if "1000x1000x1" in h.get("src") else "No")

                except:
                    pass
            """

            for img in soup.find_all("img"):
                try:
                    if "1000x1000x1" in img.get("src"):
                        image = img.get("src")

                except: # TypeError
                    pass

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise RequestConnectionError(
                f"Could not connect to {self.api_url}. Is it down?"
            )

        return image

    def scrape_lyrics(self, link):
        song_lyrics = []

        try:
            req = requests.get(link, timeout=5)
            req.raise_for_status()

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

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise RequestConnectionError(
                f"Could not connect to {self.api_url}. Is it down?"
            )

    def search(self, query_term):
        data = {"q": query_term}
        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            result = requests.get(self.api_url, params=data, headers=headers, timeout=5).json()

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise RequestConnectionError(
                f"Could not connect to {self.api_url}. Is it down?"
            )

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


@app.after_request
def add_cors_headers(response):
    # response.headers['Content-Type'] = 'application/json'
    # fuck this shit breaks the main page lol

    response.headers["Access-Control-Allow-Origin"] = "*"

    return response


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
                        "status": "502",
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
                        "status": "404",
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
                        "status": "500",
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
                    "status": "200",
                    "artists": data[0],
                    "title": data[1],
                    "source": data[2],
                    "lyrics": lyrics,
                    "cover_image": cover_image,
                }
            ),
            200,
        )

    return jsonify({"status": "400", "message": "Missing parameter 'q'."}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
