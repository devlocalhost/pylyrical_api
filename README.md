# pylyrical_api
pylyrical_api - lyrics API scraping from genius.com

# documentation/usage
## endpoins
`/lyrics`

### parameters
Acceptable parameters: q

### example
`/lyrics?q=how+do+i+make+you+love+me+the+weeknd`

## exceptions/errors
- ScrapeError: Occurs when pylyrical cannot scrape lyrics from genius.com. Returns status code 500.
- SearchError: Occurs when pylyrical cannot send a request to genius.com. Returns status code 502.

## status codes
- 200: Occurs on a successful request.
- 400: Occurs when parameter q was not given.
- 404: Occurs searching for parameter q returned no results.

## api key
create an application from https://genius.com/api-clients, and paste the token into a `.env` file:
```
GENIUS_API_KEY="MY_KEY"
```

## dependecies
```sh
pip install requests bs4 flask python-dotenv
```
