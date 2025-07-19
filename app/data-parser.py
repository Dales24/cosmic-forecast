import pandas as pd
import earthaccess as ea


def get_data(start_date, end_date):
    """
    Get data from the Earth Access API
    """
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
