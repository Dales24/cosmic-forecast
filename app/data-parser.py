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


def get_data(start_date, end_date):
    """
    Get data from the Earth Access API
    """

    with requests.Session() as session:

        session.auth = (username, password)

        r1 = session.request("get", url)

        r = session.get(r1.url, auth=(username, password))

        if r.ok:

            print(r.content)  # Say

    data = ea.search_data(
        platform="LANDSAT_8",
        instrument="OLI_TIRS",
    )
    print(data)


def build_situation_data(data):
    """
    Build the situation data
    """
    return data


def main():
    """
    Main function
    """
    data = get_data("2024-01-01", "2024-01-02")
    print(data)


main()
