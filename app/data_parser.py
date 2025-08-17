import pandas as pd
import earthaccess as ea
from http.cookiejar import CookieJar
from urllib.parse import urlencode
import requests
import configparser
import h5py
import tempfile
import urllib.request
import os
import re

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

    for i in results:
        data_url = i.data_links()
        data = parse_hdf_file(data_url)

    return data

    # need to parse hdf file to get data


def parse_hdf_file(data_url):
    """
    Parse the HDF file to get the data
    """
    print(f"Downloading data from: {data_url}")

    # TODO: fix
    with tempfile.NamedTemporaryFile(suffix=".hdf", delete=False) as tmp_file:
        urllib.request.urlretrieve(data_url, tmp_file.name)
        tmp_file_path = tmp_file.name

    try:
        with h5py.File(tmp_file_path, "r") as f:
            print("Datasets in file:", list(f.keys()))  # See top-level datasets
            cloud_frac = f["Cloud_Fraction"][:]
            print(f"Cloud fraction data shape: {cloud_frac.shape}")
            return cloud_frac
    finally:
        os.unlink(tmp_file_path)


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
