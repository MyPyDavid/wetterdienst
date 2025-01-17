# -*- coding: utf-8 -*-
# Copyright (C) 2018-2021, earthobservations developers.
# Distributed under the MIT License. See LICENSE for more info.
"""
Verify acquisition of DWD MOSMIX station list.

Please note that in the original data, the values in the `LAT` and `LON`
columns are in "Degrees Minutes" format (`<degrees>.<degrees minutes>`.),
and not in "Decimal Degrees".

Source: https://www.dwd.de/EN/ourservices/met_application_mosmix/mosmix_stations.cfg?view=nasPublication&nn=495490
"""
import pandas as pd
import pytest
from dirty_equals import IsInt, IsTuple
from pandas._testing import assert_frame_equal, assert_series_equal

from wetterdienst.metadata.columns import Columns
from wetterdienst.provider.dwd.mosmix import DwdMosmixRequest, DwdMosmixType


@pytest.mark.remote
def test_dwd_mosmix_stations_success():
    """
    Verify full MOSMIX station list.
    """

    # Acquire data.
    df = DwdMosmixRequest(parameter="small", mosmix_type=DwdMosmixType.LARGE).all().df
    assert not df.empty

    # Verify size of dataframe with all records.
    assert df.shape == IsTuple(IsInt(ge=5500), 9)

    # Verify content of dataframe. For reference purposes,
    # we use the first and the last record of the list.
    first_station_reference = pd.Series(
        {
            "station_id": "01001",
            "icao_id": "ENJA",
            "from_date": pd.NaT,
            "to_date": pd.NaT,
            "height": 10.0,
            "latitude": 70.93,
            "longitude": -8.67,
            "name": "JAN MAYEN",
            "state": pd.NA,
        },
    )
    last_station_reference = pd.Series(
        {
            "station_id": "Z949",
            "icao_id": pd.NA,
            "from_date": pd.NaT,
            "to_date": pd.NaT,
            "height": 1200.0,
            "latitude": 47.58,
            "longitude": 13.02,
            "name": "JENNER",
            "state": pd.NA,
        },
    )

    first_station: pd.Series = df.head(1).iloc[0]
    last_station: pd.Series = df.tail(1).iloc[0]

    assert_series_equal(first_station, first_station_reference, check_names=False)
    assert_series_equal(last_station, last_station_reference, check_names=False)


@pytest.mark.remote
def test_dwd_mosmix_stations_filtered():
    """
    Verify MOSMIX station list filtering by station identifier.
    """

    # Acquire data.
    request = DwdMosmixRequest(parameter="small", mosmix_type=DwdMosmixType.LARGE)
    df = request.all().df
    assert not df.empty

    # Filter dataframe.
    df_given = (
        df.loc[df[Columns.STATION_ID.value].isin(["01001", "72306", "83891", "94767"]), :]
        .sort_values("station_id")
        .reset_index(drop=True)
    )

    # Verify content of filtered dataframe.
    df_expected = pd.DataFrame(
        [
            {
                "station_id": "01001",
                "icao_id": "ENJA",
                "from_date": pd.NaT,
                "to_date": pd.NaT,
                "height": 10.0,
                "latitude": 70.93,
                "longitude": -8.67,
                "name": "JAN MAYEN",
                "state": pd.NA,
            },
            {
                "station_id": "72306",
                "icao_id": "KRDU",
                "from_date": pd.NaT,
                "to_date": pd.NaT,
                "height": 132.0,
                "latitude": 35.87,
                "longitude": -78.78,
                "name": "RALEIGH/DURHAM NC.",
                "state": pd.NA,
            },
            {
                "station_id": "83891",
                "icao_id": "SBLJ",
                "from_date": pd.NaT,
                "to_date": pd.NaT,
                "height": 937.0,
                "latitude": -27.8,
                "longitude": -50.33,
                "name": "LAGES",
                "state": pd.NA,
            },
            {
                "station_id": "94767",
                "icao_id": "YSSY",
                "from_date": pd.NaT,
                "to_date": pd.NaT,
                "height": 6.0,
                "latitude": -33.95,
                "longitude": 151.18,
                "name": "SYDNEY AIRPORT",
                "state": pd.NA,
            },
        ]
    )

    df_expected.from_date = pd.to_datetime(df_expected.from_date, utc=True)
    df_expected.to_date = pd.to_datetime(df_expected.to_date, utc=True)

    assert_frame_equal(df_given, df_expected)
