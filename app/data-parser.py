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


def build_situation_data(data):
    """
    Build the situation data
    """
    return data
