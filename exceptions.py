class ScrapeError(Exception):
    """
    custom exception to raise when scrapping
    """


class RequestTimeoutError(Exception):
    """
    error to raise when timeout
    """


class RequestConnectionError(Exception):
    """
    custom exception to raise when api cannot
    send a request/contact apis
    """


class NoResults(Exception):
    """
    custom exception to raise when no results
    for q (query)
    """
