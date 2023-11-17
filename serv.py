import requests
import os

from flask import Flask, jsonify, request, render_template
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)


class ScrapeError(Exception):
    pass


class SearchError(Exception):
    pass


class NoResults(Exception):
    pass


class GeniusAPI:
    def __init__(self, api_url, token):
        self.api_url = api_url
        self.token = token

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

            return str("".join(song_lyrics))

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise ScrapeError(f"Could not connect to {self.api_url}. Is it down?")

    def search(self, query_term):
        data = {"q": query_term}
        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            result = requests.get(self.api_url, params=data, headers=headers).json()

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise SearchError(f"Could not connect to {self.api_url}. Is it down?")

        if len(result["response"]["hits"]) != 0:
            artists = result["response"]["hits"][0]["result"]["artist_names"]
            title = result["response"]["hits"][0]["result"]["title"]
            genius_url = result["response"]["hits"][0]["result"]["url"]

            return (artists, title, genius_url)

        else:
            raise NoResults(
                f"'{query_term}' did not give any results, Please try a different term."
            )


genius_api = GeniusAPI(
    api_url="https://api.genius.com/search/",
    token=os.environ["GENIUS_API_TOKEN"],
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/lyrics", methods=["GET"])
def get_lyrics():
    query = request.args.get("q")

    if query:
        try:
            data = genius_api.search(str(query))

        except SearchError as search_exc:
            return jsonify({"status": "502", "message": str(search_exc)}), 502

        except NoResults as results_exc:
            return jsonify({"status": "404", "message": str(results_exc)}), 502

        try:
            lyrics = genius_api.scrape_lyrics(data[2])

        except ScrapeError as scrape_exc:
            return jsonify({"status": "500", "message": str(scrape_exc)}), 500

        return (
            jsonify(
                {
                    "status": "200",
                    "artists": data[0],
                    "title": data[1],
                    "source": data[2],
                    "lyrics": lyrics,
                }
            ),
            200,
        )

    else:
        return jsonify({"status": "400", "message": "Missing parameter 'q'."}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
