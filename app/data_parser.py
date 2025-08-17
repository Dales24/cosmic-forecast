import pandas as pd
import earthaccess as ea
from http.cookiejar import CookieJar
from urllib.parse import urlencode
import requests
import configparser

config = configparser.ConfigParser()
config.read("../settings.ini")

username = config["credentials"]["username"]
password = config["credentials"]["password"]
url = config["credentials"]["url"]

ea.login(username, password)


def get_data(location, date):
    """
    Get data from the Earth Access API for a specific location and date
    """
    # Example: use location and date in the search (customize as needed)
    results = ea.search_data(
        short_name="MOD06_L2",  # MODIS Cloud Product
        temporal=("2025-08-14", "2025-08-15"),
        bounding_box=(-95.8, 29.5, -95.0, 30.2),  # Houston
        cloud_hosted=True,
    )
    print(results)
    # return data


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
    get_data("example_location", "2024-01-01")  # use passed later
