import swagger_client
from swagger_client.rest import ApiException
import maya
import os
import json
import datetime
import glob
import socket
import urllib
import webbrowser
import requests
from loguru import logger 
from http.server import BaseHTTPRequestHandler, HTTPServer

class Shoeulogy():

    def __init__(self, access_token=None):
        if access_token is None:
            access_token = os.getenv('STRAVA_ACCESS_TOKEN')
        self.configuration = swagger_client.Configuration()
        self.configuration.access_token = access_token
        self._api_client = swagger_client.ApiClient(self.configuration)
        self.athletes_api = swagger_client.AthletesApi(self._api_client)
        self.activities_api = swagger_client.ActivitiesApi(self._api_client)
        self.gear_api = swagger_client.GearsApi(self._api_client)
    
    def get_logged_in_athlete(self):
        try:
            ath = Athlete(self.athletes_api.get_logged_in_athlete())
        except ApiException as e:
            logger.error(f""""
            Error in strava_swagger_client.AthletesApi! 
            STRAVA_ACCESS_TOKEN is likely out of date!
            Returning None.
            Original Error:
            {e}
            """)
            ath = None
        return ath

    def get_logged_in_athlete_activities(self, after=0, per_page=30, list_activities=None):
        if list_activities is None:
            list_activities = []
        after = date_to_epoch(after)
        _fetched = self.activities_api.get_logged_in_athlete_activities(after=after)
        if len(_fetched) > 0:
            print(f"Fetched {len(_fetched)}, the latests is on {_fetched[-1].start_date}")
            list_activities.extend(_fetched)
            if len(_fetched) == 30:
                last_after = list_activities[-1].start_date
                return self.get_logged_in_athlete_activities(after=last_after, list_activities=list_activities)
        else:
            print("empty list")
        
        return list_activities

    def get_activity_by_id(self, activity_id, activity=None):
        if activity is None:
            activity = {}
        _fetched = self.activities_api.get_activity_by_id(id=activity_id)
        if _fetched:
            print(f"Fetched {_fetched}")
            return _fetched
        else:
            print("no activity with that ID")
        
        return activity

    def get_gear_by_id(self, gear_id):
        try:
            gear = Gear(self.gear_api.get_gear_by_id(gear_id))
        except ApiException as e:
            logger.error(f""""
            Error in strava_swagger_client.GearApi! 
            STRAVA_ACCESS_TOKEN is likely out of date!
            Returning None.
            Original Error:
            {e}            
            """)
            gear = None
        return gear


class Athlete():

    def __init__(self, api_response):
        """
        Parameters
        ----------
        api_response: swagger_client.get...() object
            e.g. athletes_api.get_logged_in_athlete()
        """
        self.api_response = api_response
        self.id = self.api_response.id

    def __str__(self):
        return self._stringify()

    def __repr__(self):
        return self._stringify()

    def to_dict(self):
        _dict = self.api_response.to_dict()
        _dict = convert_datetime_to_iso8601(_dict)
        return _dict

    def store_locally(self):
        strava_dir = dir_stravadata()
        f_name = f"athlete_{self.api_response.id}.json"
        with open(os.path.join(strava_dir, f_name), 'w') as fp:
            json.dump(self.to_dict(), fp)

    def _stringify(self):
        return json.dumps(self.to_dict(), indent=2)

class Activity():

    def __init__(self, api_response, client=None):
        self.api_response = api_response
        self.athlete_id = self.api_response.athlete.id
        self.id = self.api_response.id
        if client:
            self.streams_api = client.streams_api
        else:
            client = None

    def __repr__(self):
        return f"Activity: {self.id}, Date: {self.api_response.start_date}, Name: {self.api_response.name}"

    def to_dict(self):
        _dict = self.api_response.to_dict()
        _dict = convert_datetime_to_iso8601(_dict)
        return _dict

    def store_locally(self):
        strava_dir = dir_stravadata()
        athlete_id = self.api_response.athlete.id
        activities_dir = os.path.join(strava_dir, f"activities_{athlete_id}")
        if not os.path.exists(activities_dir):
            os.mkdir(activities_dir)
        f_name = f"activity_{self.api_response.id}.json"
        with open(os.path.join(activities_dir, f_name), 'w') as fp:
            json.dump(self.to_dict(), fp)

class Gear():

    def __init__(self, api_response):
        self.api_response = api_response
        self.id = self.api_response.id
        self.activities = []

    def __str__(self):
        return self._stringify()

    def __repr__(self):
        return self._stringify()

    def to_dict(self):
        _dict = self.api_response.to_dict()
        _dict = convert_datetime_to_iso8601(_dict)
        return _dict

    def store_locally(self):
        strava_dir = dir_stravadata()
        f_name = f"gear_{self.api_response.id}.json"
        with open(os.path.join(strava_dir, f_name), 'w') as fp:
            json.dump(self.to_dict(), fp)

    def _stringify(self):
        return json.dumps(self.to_dict(), indent=2)


def strava_oauth2(client_id=None, client_secret=None):
    """Run strava authorization flow. This function will open a default system
    browser alongside starting a local webserver. The authorization procedure will be completed in the browser.
    The access token will be returned in the browser in the format ready to copy to the .env file.
    
    Parameters:
    -----------
    client_id: int, if not provided will be retrieved from the STRAVA_CLIENT_ID env viriable
    client_secret: str, if not provided will be retrieved from the STRAVA_CLIENT_SECRET env viriable
    """
    if client_id is None:
        client_id = os.getenv('STRAVA_CLIENT_ID', None)
        if client_id is None:
            raise ValueError('client_id is None')
    if client_secret is None:
        client_secret = os.getenv('STRAVA_CLIENT_SECRET', None)
        if client_secret is None:
            raise ValueError('client_secret is None')
    
    port = 8000
    _request_strava_authorize(client_id, port)

    logger.info(f"serving at port {port}")

    token = run_server_and_wait_for_token(
        port=port,
        client_id=client_id,
        client_secret=client_secret
    )

    return token


def _request_strava_authorize(client_id, port):
    params_oauth = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": f"http://localhost:{port}/authorization_successful",
        "scope": "read,profile:read_all,activity:read",
        "state": 'https://github.com/sladkovm/strava-http',
        "approval_prompt": "force"
    }
    values_url = urllib.parse.urlencode(params_oauth)
    base_url = 'https://www.strava.com/oauth/authorize'
    rv = base_url + '?' + values_url
    webbrowser.get().open(rv)
    return None


def run_server_and_wait_for_token(port, client_id, client_secret):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', port))
        s.listen()
        conn, addr = s.accept()

        request_bytes = b''
        with conn:
            while True:
                chunk = conn.recv(512)
                request_bytes += chunk

                if request_bytes.endswith(b'\r\n\r\n'):
                    break
            conn.sendall(b'HTTP/1.1 200 OK\r\n\r\nsuccess\r\n')

        request = request_bytes.decode('utf-8')
        status_line = request.split('\n', 1)[0]
        
        method, raw_url, protocol_version = status_line.split(' ')
        
        url = urllib.parse.urlparse(raw_url)
        query_string = url.query
        query_params = urllib.parse.parse_qs(query_string, keep_blank_values=True)

        if url.path == "/authorization_successful":
            code = query_params.get('code')[0]
            logger.debug(f"code: {code}")
            params = {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code"
            }
            r = requests.post("https://www.strava.com/oauth/token", params)
            data = r.json()
            logger.debug(f"Authorized athlete: {data.get('access_token', 'Oeps something went wrong!')}")
        else:
            data = url.path.encode()
        
        return data


def convert_datetime_to_iso8601(d):
    for k, v in d.items():
        if isinstance(v, dict):
            convert_datetime_to_iso8601(v)
        elif isinstance(v, list):
            for i in v:
                if isinstance(i, dict):
                    convert_datetime_to_iso8601(i)
        else:
            if isinstance(v, datetime.datetime):
                d[k] = maya.parse(v).iso8601()
    return d


def dir_stravadata():
    home_dir = os.path.expanduser('~')
    strava_dir = os.path.join(home_dir, '.stravadata')
    if not os.path.exists(strava_dir):
        os.mkdir(strava_dir)
    return strava_dir


def date_to_epoch(date):
    """Convert a date to epoch representation"""
    rv = None
    if isinstance(date, int):
        rv = date
    if isinstance(date, datetime.datetime):
        _ = maya.parse(date)
        rv = _.epoch
    if isinstance(date, str):
        _ = maya.when(date)
        rv = _.epoch
    if rv is None:
        raise TypeError('date must be epoch int, datetime obj or the string')
    return rv        
