import pandas as pd
import earthaccess as ea
from http.cookiejar import CookieJar
from urllib import urlencode
import requests
import urllib
import configparser

config = configparser.ConfigParser()
config.read("settings.ini")

username = config["credentials"]["username"]
password = config["credentials"]["password"]
url = config["credentials"]["url"]

ea.login()


def get_data(location, date):
    """
    Get data from the Earth Access API for a specific location and date
    """
    with requests.Session() as session:
        session.auth = (username, password)
        r1 = session.request("get", url)
        r = session.get(r1.url, auth=(username, password))
        if r.ok:
            print(r.content)
    # Example: use location and date in the search (customize as needed)
    data = ea.search_data(
        platform="LANDSAT_8",
        instrument="OLI_TIRS",
        # Add location and date filters if supported by the API
        # e.g., spatial=location, temporal=date
    )
    print(data)
    return data


def build_situation_data(data):
    """
    Build the situation data
    """
    return data


def main():
    """
    Main function
    """
    data = get_data("example_location", "2024-01-01")
    print(data)


if __name__ == "__main__":
    main()
