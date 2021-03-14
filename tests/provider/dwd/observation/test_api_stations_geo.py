# -*- coding: utf-8 -*-
# Copyright (c) 2018-2021, earthobservations developers.
# Distributed under the MIT License. See LICENSE for more info.
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
import pytz
from pandas._libs.tslibs.timestamps import Timestamp
from pandas._testing import assert_frame_equal

from wetterdienst.provider.dwd.observation import (
    DwdObservationDataset,
    DwdObservationPeriod,
    DwdObservationRequest,
    DwdObservationResolution,
)
from wetterdienst.util.geo import Coordinates, derive_nearest_neighbours


@pytest.mark.remote
def test_dwd_observation_stations_nearby_number_success():

    # Test for one nearest station
    request = DwdObservationRequest(
        DwdObservationDataset.TEMPERATURE_AIR,
        DwdObservationResolution.HOURLY,
        DwdObservationPeriod.RECENT,
        datetime(2020, 1, 1),
        datetime(2020, 1, 20),
    )

    nearby_station = request.nearby_number(
        50.0,
        8.9,
        1,
    )
    nearby_station = nearby_station.df.drop("to_date", axis="columns")

    assert_frame_equal(
        nearby_station,
        pd.DataFrame(
            [
                [
                    "04411",
                    Timestamp("2002-01-24", tzinfo=pytz.UTC),
                    155.0,
                    49.9195,
                    8.9671,
                    "Schaafheim-Schlierbach",
                    "Hessen",
                    11.65302672,
                ]
            ],
            columns=[
                "station_id",
                "from_date",
                "height",
                "latitude",
                "longitude",
                "station_name",
                "state",
                "distance_to_location",
            ],
        ),
    )

    request = DwdObservationRequest(
        DwdObservationDataset.TEMPERATURE_AIR,
        DwdObservationResolution.HOURLY,
        DwdObservationPeriod.RECENT,
        datetime(2020, 1, 1),
        datetime(2020, 1, 20),
    )
    nearby_station = request.nearby_number(
        50.0,
        8.9,
        3,
    )
    nearby_station = nearby_station.df.drop("to_date", axis="columns")
    nearby_station["station_id"] = nearby_station["station_id"]

    pd.testing.assert_frame_equal(
        nearby_station,
        pd.DataFrame(
            [
                [
                    "04411",
                    Timestamp("2002-01-24 00:00:00", tzinfo=pytz.UTC),
                    155.0,
                    49.9195,
                    8.9671,
                    "Schaafheim-Schlierbach",
                    "Hessen",
                    11.653026716750542,
                ],
                [
                    "02480",
                    Timestamp("2004-09-01 00:00:00", tzinfo=pytz.UTC),
                    108.0,
                    50.0643,
                    8.993,
                    "Kahl/Main",
                    "Bayern",
                    12.572153957087247,
                ],
                [
                    "07341",
                    Timestamp("2005-07-16 00:00:00", tzinfo=pytz.UTC),
                    119.0,
                    50.0899,
                    8.7862,
                    "Offenbach-Wetterpark",
                    "Hessen",
                    16.12612066977987,
                ],
            ],
            columns=[
                "station_id",
                "from_date",
                "height",
                "latitude",
                "longitude",
                "station_name",
                "state",
                "distance_to_location",
            ],
        ),
    )


def test_dwd_observation_stations_nearby_distance_success():
    request = DwdObservationRequest(
        DwdObservationDataset.TEMPERATURE_AIR,
        DwdObservationResolution.HOURLY,
        DwdObservationPeriod.RECENT,
        datetime(2020, 1, 1),
        datetime(2020, 1, 20),
    )
    nearby_station = request.nearby_radius(
        50.0,
        8.9,
        10,
    )
    assert nearby_station.df.empty


def test_dwd_observation_stations_nearby_number_fail_1():
    with pytest.raises(ValueError):
        DwdObservationRequest(
            DwdObservationDataset.TEMPERATURE_AIR,
            DwdObservationResolution.HOURLY,
            DwdObservationPeriod.RECENT,
            datetime(2020, 1, 1),
            datetime(2020, 1, 20),
        ).nearby_number(
            51.4,
            9.3,
            0,
        )


def test_derive_nearest_neighbours():
    coords = Coordinates(np.array([50.0, 51.4]), np.array([8.9, 9.3]))

    metadata = pd.DataFrame(
        {
            "station_id": [4371, 4373, 4411, 13904, 13965, 15207],
            "latitude": [52.1042, 52.8568, 49.9195, 55.0, 48.2639, 51.2835],
            "longitude": [8.7521, 11.1319, 8.9671, 6.3333, 8.8134, 9.359],
        }
    )

    distances, indices_nearest_neighbours = derive_nearest_neighbours(
        latitudes=metadata["latitude"].values,
        longitudes=metadata["longitude"].values,
        coordinates=coords,
        number_nearby=1,
    )

    np.testing.assert_array_almost_equal(distances, np.array([0.00182907, 0.00227919]))

    np.testing.assert_array_almost_equal(indices_nearest_neighbours, np.array([2, 5]))