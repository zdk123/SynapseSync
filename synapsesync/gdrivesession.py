from requests import Session
from urllib.parse import urlparse, parse_qs, urlencode


class GDriveSession(Session):
    """
    A Session class for handling requests to public google drive links
    """

    def __init__(self):
        super().__init__()

    ## this function originates from https://stackoverflow.com/questions/25010369/wget-curl-large-file-from-google-drive/39225039#39225039
    def _get_confirm_token(self, response):
        for key, value in response.cookies.items():
            if key.startswith("download_warning"):
                return value
        return None

    def _get_from_google_drive(self, id, url, **kwargs):  # destination,
        stream = kwargs.pop("stream")
        response = super().get(url, params={"id": id}, stream=True, **kwargs)
        token = self._get_confirm_token(response)
        if token:
            kwargs["stream"] = stream
            params = {"id": id, "confirm": token, "export": "download"}
            response = super().get(url, params=params, **kwargs)
        return response

    def _parse_id_from_url(self, url):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        id = query.pop("id")[0]
        query.pop("export")
        parsed = parsed._replace(query=urlencode(query, True))
        return id, parsed.geturl()

    def get(self, url, **kwargs):
        """
        A get method for downloading public objects from google drive accounts
        """
        ## Pop the id from the query string of a google drive url
        try:
            id, newurl = self._parse_id_from_url(url)
            return self._get_from_google_drive(id, newurl, **kwargs)
        except KeyError:
            return super().get(url, **kwargs)
