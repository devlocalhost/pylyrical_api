# pylyrical_api
pylyrical_api - lyrics API scraping from genius.com

# API Token
To self-host, you need to get an API token from the [api client page](https://genius.com/api-clients). You can then add the API token to a ".env" file. Example: `GENIUS_API_TOKEN="T0K3N"`

# Usage
- API endpoint: /lyrics
- Acceptable parameters: q
  - Example: /lyrics?q=how+do+i+make+you+love+me+the+weeknd

Responses
- 200
```json
{
    "artists": "",
    "lyrics": "",
    "source": "",
    "status": "200",
    "title": ""
}
```

- 400
```json
{
    "exception":
    "NoParameter",
    "message": "Missing parameter 'q'.",
    "status": "400"
}
```

- 404
```json
{
    "exception": "NoResults",
    "message": "'' did not give any results, Please try a different term.",
    "status": "404"
}
```

- 500
```json
{
    "exception": "ScrapeError",
    "message": "",
    "status": "500"
}
```

- 502
```json
{
    "exception": "RequestConnectionError",
    "message": "",
    "status": "502"
}
```

# Exceptions/Errors
- NoParameter: Occurs when no parameter was given.
  - Returns status code 400.
- NoResults: Occurs when no results were found.
  - Returns status code 404.
- ScrapeError: Occurs when pylyrical cannot scrape lyrics from genius.com
  - Returns status code 500.
- RequestConnectionError: Occurs when pylyrical cannot send a request to genius.com
  - Returns status code 502.

