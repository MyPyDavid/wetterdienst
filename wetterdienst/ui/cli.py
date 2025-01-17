# -*- coding: utf-8 -*-
# Copyright (C) 2018-2021, earthobservations developers.
# Distributed under the MIT License. See LICENSE for more info.
import functools
import json
import logging
import sys
from collections import OrderedDict
from pprint import pformat
from typing import List

import click
import cloup
from click_params import StringListParamType
from cloup.constraints import If, RequireExactly, accept_none

from wetterdienst import Provider, Wetterdienst, __appname__, __version__
from wetterdienst.exceptions import ProviderError
from wetterdienst.ui.core import (
    get_interpolate,
    get_stations,
    get_summarize,
    get_values,
    set_logging_level,
)
from wetterdienst.util.cli import docstring_format_verbatim, setup_logging

log = logging.getLogger(__name__)

CommaSeparator = StringListParamType(",")

appname = f"{__appname__} {__version__}"

provider_opt = cloup.option_group(
    "Provider",
    click.option(
        "--provider",
        type=click.Choice([provider.name for provider in Provider], case_sensitive=False),
        required=True,
    ),
)

network_opt = cloup.option_group(
    "Network",
    click.option(
        "--network",
        type=click.STRING,
        required=True,
    ),
)

debug_opt = click.option("--debug", is_flag=True)


def get_api(provider: str, network: str):
    """
    Function to get API for provider and network, if non found click.Abort()
    is casted with the error message

    :param provider:
    :param network:
    :return:
    """
    try:
        return Wetterdienst(provider, network)
    except ProviderError as e:
        log.error(str(e))
        sys.exit(1)


def station_options_core(command):
    """
    Station options core for cli, which can be used for stations and values endpoint

    :param command:
    :return:
    """
    arguments = [
        cloup.option("--parameter", type=CommaSeparator, required=True),
        cloup.option("--resolution", type=click.STRING, required=True),
        cloup.option("--period", type=CommaSeparator),
    ]
    return functools.reduce(lambda x, opt: opt(x), reversed(arguments), command)


def station_options_extension(command):
    """
    Station options extension for cli, which can be used for stations and values endpoint

    :param command:
    :return:
    """
    arguments = [
        cloup.option_group("All stations", click.option("--all", "all_", is_flag=True)),
        cloup.option_group(
            "Station id filtering",
            cloup.option("--station", type=CommaSeparator),
        ),
        cloup.option_group(
            "Station name filtering",
            cloup.option("--name", type=click.STRING),
        ),
        cloup.option_group(
            "Latitude-Longitude rank/distance filtering",
            cloup.option("--coordinates", metavar="LATITUDE,LONGITUDE", type=click.STRING),
            cloup.option("--rank", type=click.INT),
            cloup.option("--distance", type=click.FLOAT),
            help="Provide --coordinates plus either --rank or --distance.",
        ),
        cloup.constraint(
            If("coordinates", then=RequireExactly(1), else_=accept_none),
            ["rank", "distance"],
        ),
        cloup.option_group(
            "BBOX filtering",
            cloup.option("--bbox", metavar="LEFT BOTTOM RIGHT TOP", type=click.STRING),
        ),
        cloup.option_group(
            "SQL filtering",
            click.option("--sql", type=click.STRING),
        ),
        cloup.constraint(
            RequireExactly(1),
            ["all_", "station", "name", "coordinates", "bbox", "sql"],
        ),
    ]
    return functools.reduce(lambda x, opt: opt(x), reversed(arguments), command)


def station_options_interpolate_summarize(command):
    """
    Station options for interpolate/summarize for cli, which can be used for stations and values endpoint

    :param command:
    :return:
    """
    arguments = [
        cloup.option_group(
            "Station id filtering",
            cloup.option("--station", type=CommaSeparator),
        ),
        cloup.option_group(
            "Latitude-Longitude rank/distance filtering",
            cloup.option("--coordinates", metavar="LATITUDE,LONGITUDE", type=click.STRING),
        ),
        cloup.constraint(
            RequireExactly(1),
            ["station", "coordinates"],
        ),
    ]
    return functools.reduce(lambda x, opt: opt(x), reversed(arguments), command)


def wetterdienst_help():
    """
    Usage
    =====

        wetterdienst (-h | --help)  Display this page
        wetterdienst --version      Display the version number
        wetterdienst info           Display project information


    Overview
    ========

    This section roughly outlines the different families of command line
    options. More detailed information is available within subsequent sections
    of this page.

    Coverage information:

        wetterdienst about coverage --provider=<provider> --network=<network>
            [--parameter=<parameter>] [--resolution=<resolution>] [--period=<period>]

        wetterdienst about fields --provider=<provider> --network=<network>
            --parameter=<parameter> --resolution=<resolution> --period=<period> [--language=<language>]

    Data acquisition:

        wetterdienst {stations,values}

            # Selection options
            --provider=<provider> --network=<network> --parameter=<parameter> --resolution=<resolution> [--period=<period>]

            # Filtering options
            --all
            --date=<date>
            --station=<station>
            --name=<name>
            --coordinates=<latitude,longitude> --rank=<rank>
            --coordinates=<latitude,longitude> --distance=<distance>
            --bbox=<left,lower,right,top>
            --sql=<sql>

            # Output options
            [--format=<format>] [--pretty]
            [--tidy] [--humanize] [--si-units]
            [--dropna] [--skip_empty] [--skip_threshold=0.95]

            # Export options
            [--target=<target>]


    Options
    =======

    This section explains all command line options in detail.

    Selection options:

        --provider                  The data provider / organisation.
                                    Examples: dwd, eccc, noaa, wsv, ea, eaufrance, nws, geosphere

        --network                   The network of the data provider
                                    Examples: observation, mosmix, radar, ghcn, pegel, hydrology

        --parameter                 Data parameter or parameter set
                                    Examples: kl, precipitation_height

        --resolution                Dataset resolution / product
                                    Examples: annual, monthly, daily, hourly, minute_10, minute_1
                                    For DWD MOSMIX: small, large

        [--period]                  Dataset period
                                    Examples: "historical", "recent", "now"

    Filtering options:

        --all                       Flag to process all data

        --date                      Date for filtering data
                                    A single date(time) or interval in RFC3339/ISO8601 format.
                                    See also:
                                    - https://en.wikipedia.org/wiki/ISO_8601#Combined_date_and_time_representations
                                    - https://en.wikipedia.org/wiki/ISO_8601#Time_intervals

        --name                      Name of station

        --station                   Comma-separated list of station identifiers

        --coordinates               Geolocation point for geospatial filtering
                                    Format: <latitude,longitude>

        --rank                      Rank of nearby stations when filtering by geolocation point
                                    To be used with `--coordinates`.

        --distance                  Maximum distance in km when filtering by geolocation point
                                    To be used with `--coordinates`.

        --bbox                      Bounding box for geospatial filtering
                                    Format: <lon1,lat1,lon2,lat2> aka. <left,bottom,right,top>

        --sql                       SQL filter statement

        --sql-values                SQL filter to apply to values

    Transformation options:
        --tidy                      Tidy DataFrame
        --humanize                  Humanize parameters
        --si-units                  Convert to SI units
        --skip_empty                Skip empty stations according to skip_threshold
        --skip_threshold            Skip threshold for a station to be empty (0 < skip_threshold <= 1) [Default: 0.95]
        --dropna                    Whether to drop nan values from the result

    Output options:
        --format                    Output format. [Default: json]
        --language                  Output language. [Default: en]
        --pretty                    Pretty-print JSON

    Export options:
        --target                    Output target for storing data into different data sinks.

    Other options:
        -h --help                   Show this screen
        --debug                     Enable debug messages
        --listen                    HTTP server listen address.
        --reload                    Run service and dynamically reload changed files


    Examples
    ========

    This section includes example invocations to get you started quickly. Most
    of them can be used verbatim in your terminal. For displaying JSON output
    more conveniently, you may want to pipe the output of Wetterdienst into the
    excellent ``jq`` program, which can also be used for subsequent filtering
    and transforming.

    Acquire observation stations:

        # Get list of all stations for daily climate summary data in JSON format
        wetterdienst stations --provider=dwd --network=observation --parameter=kl --resolution=daily --all

        # Get list of all stations in CSV format
        wetterdienst stations --provider=dwd --network=observation --parameter=kl --resolution=daily --all --format=csv

        # Get list of specific stations
        wetterdienst stations --provider=dwd --network=observation --resolution=daily --parameter=kl --station=1,1048,4411

        # Get list of specific stations in GeoJSON format
        wetterdienst stations --provider=dwd --network=observation --resolution=daily --parameter=kl --station=1,1048,4411 --format=geojson

    Acquire MOSMIX stations:

        wetterdienst stations --provider=dwd --network=mosmix --parameter=large --resolution=large --all
        wetterdienst stations --provider=dwd --network=mosmix --parameter=large --resolution=large --all --format=csv

    Acquire observation data:

        # Get daily climate summary data for specific stations, selected by name and station id
        wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=daily --period=recent --name=Dresden-Hosterwitz
        wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=daily --period=recent --station=1048,4411

        # Get daily climate summary data for specific stations in CSV format
        wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=daily --period=recent --station=1048,4411

        # Get daily climate summary data for specific stations in tidy format
        wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=daily --period=recent --station=1048,4411 --tidy

        # Limit output to specific date
        wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=daily --period=recent --date=2020-05-01 --station=1048,4411

        # Limit output to specified date range in ISO-8601 time interval format
        wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=daily --date=2020-05-01/2020-05-05 --station=1048

        # The real power horse: Acquire data across historical+recent data sets
        wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=daily --date=1969-01-01/2020-06-11 --station=1048

        # Acquire monthly data for 2020-05
        wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=monthly --date=2020-05 --station=1048

        # Acquire monthly data from 2017-01 to 2019-12
        wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=monthly --date=2017-01/2019-12 --station=1048,4411

        # Acquire annual data for 2019
        wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=annual --date=2019 --station=1048,4411

        # Acquire annual data from 2010 to 2020
        wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=annual --date=2010/2020 --station=1048

        # Acquire hourly data for a given time range
        wetterdienst values --provider=dwd --network=observation --parameter=air_temperature --resolution=hourly \\
            --date=2020-06-15T12/2020-06-16T12 --station=1048,4411

        # Acquire data for specific parameter and dataset
        wetterdienst values --provider=dwd --network=observation \\
            --parameter=precipitation_height/precipitation_more,temperature_air_200/kl \\
            --resolution=hourly --date=2020-06-15T12/2020-06-16T12 --station=1048,4411

    Acquire MOSMIX data:

        wetterdienst values --provider=dwd --network=mosmix --parameter=ttt,ff --resolution=large --station=65510

    Geospatial filtering:

        # Acquire stations and readings by geolocation, request specific number of nearby stations.
        wetterdienst stations --provider=dwd --network=observation --resolution=daily --parameter=kl --period=recent \\
            --coordinates=49.9195,8.9671 --rank=5

        wetterdienst values --provider=dwd --network=observation --resolution=daily --parameter=kl --period=recent \\
            --coordinates=49.9195,8.9671 --rank=5 --date=2020-06-30

        # Acquire stations and readings by geolocation, request stations within specific distance.
        wetterdienst stations --provider=dwd --network=observation --resolution=daily --parameter=kl --period=recent \\
            --coordinates=49.9195,8.9671 --distance=25

        wetterdienst values --provider=dwd --network=observation --resolution=daily --parameter=kl --period=recent \\
            --coordinates=49.9195,8.9671 --distance=25 --date=2020-06-30

    SQL filtering:

        # Find stations by state.
        wetterdienst stations --provider=dwd --network=observation --parameter=kl --resolution=daily --period=recent \\
            --sql="SELECT * FROM data WHERE state='Sachsen'"

        # Find stations by name (LIKE query).
        wetterdienst stations --provider=dwd --network=observation --parameter=kl --resolution=daily --period=recent \\
            --sql="SELECT * FROM data WHERE lower(name) LIKE lower('%dresden%')"

        # Find stations by name (regexp query).
        wetterdienst stations --provider=dwd --network=observation --parameter=kl --resolution=daily --period=recent \\
            --sql="SELECT * FROM data WHERE regexp_matches(lower(name), lower('.*dresden.*'))"

        # Filter values: Display daily climate observation readings where the maximum temperature is below two degrees celsius.
        wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=daily --period=recent \\
            --station=1048,4411 --sql-values="SELECT * FROM data WHERE wind_gust_max > 20.0;"

        # Filter measurements: Same as above, but use tidy format.
        wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=daily --period=recent \\
            --station=1048,4411 \\
            --tidy --sql-values="SELECT * FROM data WHERE parameter='wind_gust_max' AND value > 20.0;"

    Inquire metadata:

        # Display coverage/correlation between parameters, resolutions and periods.
        # This can answer questions like ...
        wetterdienst about coverage --provider=dwd --network=observation

        # Tell me all periods and resolutions available for given dataset labels.
        wetterdienst about coverage --provider=dwd --network=observation --dataset=climate_summary
        wetterdienst about coverage --provider=dwd --network=observation --dataset=temperature_air

        # Tell me all parameters available for given resolutions.
        wetterdienst about coverage --provider=dwd --network=observation --resolution=daily
        wetterdienst about coverage --provider=dwd --network=observation --resolution=hourly

    Export data to files:

        # Export list of stations into spreadsheet
        wetterdienst stations \\
            --provider=dwd --network=observation --parameter=kl --resolution=daily --period=recent \\
            --all --target=file://stations_result.xlsx

        # Shortcut command for fetching readings.
        # It will be used for the next invocations.
        alias fetch="wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=daily --period=recent --station=1048,4411"

        # Export readings into spreadsheet (Excel-compatible)
        fetch --target="file://observations.xlsx"

        # Export readings into Parquet format and display head of Parquet file
        fetch --target="file://observations.parquet"

        # Check Parquet file
        parquet-tools schema observations.parquet
        parquet-tools head observations.parquet

        # Export readings into Zarr format
        fetch --target="file://observations.zarr"

    Export data to databases:

        # Shortcut command for fetching readings.
        # It will be used for the next invocations.
        alias fetch="wetterdienst values --provider=dwd --network=observation --parameter=kl --resolution=daily --period=recent --station=1048,4411"

        # Store readings to DuckDB
        fetch --target="duckdb:///observations.duckdb?table=weather"

        # Store readings to InfluxDB
        fetch --target="influxdb://localhost/?database=observations&table=weather"

        # Store readings to CrateDB
        fetch --target="crate://localhost/?database=observations&table=weather"

    The HTTP REST API service:

        # Start service on standard port, listening on http://localhost:7890.
        wetterdienst restapi

        # Start service on standard port and watch filesystem changes.
        # This is suitable for development.
        wetterdienst restapi --reload

        # Start service on public interface and specific port.
        wetterdienst restapi --listen=0.0.0.0:8890

    The Wetterdienst Explorer UI service:

        # Start service on standard port, listening on http://localhost:7891.
        wetterdienst explorer

        # Start service on standard port and watch filesystem changes.
        # This is suitable for development.
        wetterdienst explorer --reload

        # Start service on public interface and specific port.
        wetterdienst explorer --listen=0.0.0.0:8891

    Explore OPERA radar stations:

        # Display all radar stations.
        wetterdienst radar --all

        # Display radar stations filtered by country.
        wetterdienst radar --country-name=france

        # Display OPERA radar stations operated by DWD.
        wetterdienst radar --dwd

        # Display radar station with specific ODIM- or WMO-code.
        wetterdienst radar --odim-code=deasb
        wetterdienst radar --wmo-code=10103

    """  # noqa:E501
    pass


@cloup.group(
    "wetterdienst",
    help=docstring_format_verbatim(wetterdienst_help.__doc__),
    context_settings={"max_content_width": 120},
)
@click.version_option(__version__, "-v", "--version", message="%(version)s")
def cli():
    setup_logging()


@cli.command("info")
def info():
    from wetterdienst import info

    info()

    return


@cli.command("version")
def version():
    print(__version__)  # noqa: T201


@cli.command("restapi")
@cloup.option("--listen", type=click.STRING, default=None)
@cloup.option("--reload", is_flag=True)
@debug_opt
def restapi(listen: str, reload: bool, debug: bool):
    set_logging_level(debug)

    # Run HTTP service.
    log.info(f"Starting {appname}")
    log.info(f"Starting HTTP web service on http://{listen}")

    from wetterdienst.ui.restapi import start_service

    start_service(listen, reload=reload)

    return


@cli.command("explorer")
@cloup.option("--listen", type=click.STRING, default=None)
@cloup.option("--reload", is_flag=True)
@debug_opt
def explorer(listen: str, reload: bool, debug: bool):
    set_logging_level(debug)

    log.info(f"Starting {appname}")
    log.info(f"Starting Explorer web service on http://{listen}")
    from wetterdienst.ui.explorer.app import start_service

    start_service(listen, reload=reload)
    return


@cli.group()
def about():
    pass


@about.command()
@cloup.option_group(
    "Provider",
    click.option(
        "--provider",
        type=click.Choice([provider.name for provider in Provider], case_sensitive=False),
    ),
)
@cloup.option_group(
    "network",
    click.option(
        "--network",
        type=click.STRING,
    ),
)
@cloup.option("--dataset", type=CommaSeparator, default=None)
@cloup.option("--resolution", type=click.STRING, default=None)
@debug_opt
def coverage(provider, network, dataset, resolution, debug):
    set_logging_level(debug)

    if not provider or not network:
        print(json.dumps(Wetterdienst.discover(), indent=2))  # noqa: T201
        return

    api = get_api(provider=provider, network=network)

    cov = api.discover(
        dataset=dataset,
        resolution=resolution,
        flatten=False,
        with_units=False,
    )

    # Compute more compact representation.
    result = OrderedDict()
    for resolution, labels in cov.items():
        result[resolution] = list(labels.keys())

    print(json.dumps(result, indent=2))  # noqa: T201


@about.command("fields")
@provider_opt
@network_opt
@cloup.option_group(
    "(DWD only) information from PDF documents",
    click.option("--dataset", type=CommaSeparator),
    click.option("--resolution", type=click.STRING),
    click.option("--period", type=CommaSeparator),
    click.option("--language", type=click.Choice(["en", "de"], case_sensitive=False), default="en"),
    constraint=cloup.constraints.require_all,
)
@debug_opt
def fields(provider, network, dataset, resolution, period, language, **kwargs):
    api = get_api(provider, network)

    if not (api.provider == Provider.DWD and network.lower() == "observation") and kwargs.get("fields"):
        raise click.BadParameter("'fields' command only available for provider 'DWD'")

    metadata = api.describe_fields(
        dataset=dataset,
        resolution=resolution,
        period=period,
        language=language,
    )

    output = pformat(dict(metadata))

    print(output)  # noqa: T201

    return


@cli.command("stations")
@provider_opt
@network_opt
@station_options_core
@station_options_extension
@cloup.option_group(
    "Format/Target",
    click.option(
        "--format",
        "fmt",
        type=click.Choice(["json", "geojson", "csv"], case_sensitive=False),
        default="json",
    ),
    cloup.option("--target", type=click.STRING),
)
@cloup.constraint(
    If("coordinates", then=RequireExactly(1), else_=accept_none),
    ["rank", "distance"],
)
@cloup.option("--pretty", is_flag=True)
@debug_opt
def stations(
    provider: str,
    network: str,
    parameter: List[str],
    resolution: str,
    period: List[str],
    all_: bool,
    station: List[str],
    name: str,
    coordinates: str,
    rank: int,
    distance: float,
    bbox: str,
    sql: str,
    fmt: str,
    target: str,
    pretty: bool,
    debug: bool,
):
    set_logging_level(debug)

    api = get_api(provider=provider, network=network)

    stations_ = get_stations(
        api=api,
        parameter=parameter,
        resolution=resolution,
        period=period,
        date=None,
        issue=None,
        all_=all_,
        station_id=station,
        name=name,
        coordinates=coordinates,
        rank=rank,
        distance=distance,
        bbox=bbox,
        sql=sql,
        tidy=False,
        si_units=False,
        humanize=False,
        skip_empty=False,
        skip_threshold=0.95,
        dropna=False,
    )

    if stations_.df.empty:
        log.error("No stations available for given constraints")
        sys.exit(1)

    if target:
        stations_.to_target(target)
        return

    indent = None
    if pretty:
        indent = 2

    output = stations_.to_format(fmt, indent=indent)

    print(output)  # noqa: T201

    return


@cli.command("values")
@provider_opt
@network_opt
@station_options_core
@station_options_extension
@cloup.option("--date", type=click.STRING)
@cloup.option("--tidy", is_flag=True)
@cloup.option("--sql-values", type=click.STRING)
@cloup.option_group(
    "Format/Target",
    cloup.option(
        "--format",
        "fmt",
        type=click.Choice(["json", "csv"], case_sensitive=False),
        default="json",
    ),
    cloup.option("--target", type=click.STRING),
    help="Provide either --format or --target.",
)
@cloup.option("--issue", type=click.STRING)
@cloup.option("--si-units", type=click.BOOL, default=True)
@cloup.option("--humanize", type=click.BOOL, default=True)
@cloup.option("--pretty", is_flag=True)
@cloup.option("--skip_empty", type=click.BOOL, default=False)
@cloup.option("--skip_threshold", type=click.FloatRange(min=0, min_open=True, max=1), default=0.95)
@cloup.option("--dropna", type=click.BOOL, default=False)
@debug_opt
def values(
    provider: str,
    network: str,
    parameter: List[str],
    resolution: str,
    period: List[str],
    date: str,
    issue: str,
    all_: bool,
    station: List[str],
    name: str,
    coordinates: str,
    rank: int,
    distance: float,
    bbox: str,
    sql: str,
    sql_values,
    fmt: str,
    target: str,
    tidy: bool,
    si_units: bool,
    humanize: bool,
    skip_empty: bool,
    skip_threshold: float,
    dropna: bool,
    pretty: bool,
    debug: bool,
):
    set_logging_level(debug)

    api = get_api(provider, network)

    try:
        values_ = get_values(
            api=api,
            parameter=parameter,
            resolution=resolution,
            period=period,
            date=date,
            issue=issue,
            all_=all_,
            station_id=station,
            name=name,
            coordinates=coordinates,
            rank=rank,
            distance=distance,
            bbox=bbox,
            sql=sql,
            sql_values=sql_values,
            si_units=si_units,
            tidy=tidy,
            humanize=humanize,
            skip_empty=skip_empty,
            skip_threshold=skip_threshold,
            dropna=dropna,
        )
    except ValueError as ex:
        log.exception(ex)
        sys.exit(1)
    else:
        if values_.df.empty:
            log.error("No data available for given constraints")
            sys.exit(1)

    if target:
        values_.to_target(target)
        return

    indent = None
    if pretty:
        indent = 2

    output = values_.to_format(fmt, indent=indent)

    print(output)  # noqa: T201

    return


@cli.command("interpolate")
@provider_opt
@network_opt
@station_options_core
@station_options_interpolate_summarize
@cloup.option("--use_nearby_station_until_km", type=click.FLOAT, default=1)
@cloup.option("--date", type=click.STRING, required=True)
@cloup.option("--sql-values", type=click.STRING)
@cloup.option_group(
    "Format/Target",
    cloup.option(
        "--format",
        "fmt",
        type=click.Choice(["json", "csv"], case_sensitive=False),
        default="json",
    ),
    cloup.option("--target", type=click.STRING),
    help="Provide either --format or --target.",
)
@cloup.option("--issue", type=click.STRING)
@cloup.option("--si-units", type=click.BOOL, default=True)
@cloup.option("--humanize", type=click.BOOL, default=True)
@cloup.option("--pretty", is_flag=True)
@debug_opt
def interpolate(
    provider: str,
    network: str,
    parameter: List[str],
    resolution: str,
    period: List[str],
    use_nearby_station_until_km: float,
    date: str,
    issue: str,
    station: str,
    coordinates: str,
    sql_values,
    fmt: str,
    target: str,
    si_units: bool,
    humanize: bool,
    pretty: bool,
    debug: bool,
):
    set_logging_level(debug)

    api = get_api(provider, network)

    try:
        values_ = get_interpolate(
            api=api,
            parameter=parameter,
            resolution=resolution,
            period=period,
            date=date,
            issue=issue,
            station_id=station,
            coordinates=coordinates,
            sql_values=sql_values,
            si_units=si_units,
            humanize=humanize,
            use_nearby_station_until_km=use_nearby_station_until_km,
        )
    except ValueError as ex:
        log.exception(ex)
        sys.exit(1)
    else:
        if values_.df.empty:
            log.error("No data available for given constraints")
            sys.exit(1)

    if target:
        values_.to_target(target)
        return

    indent = None
    if pretty:
        indent = 2

    output = values_.to_format(fmt, indent=indent)

    print(output)  # noqa: T201

    return


@cli.command("summarize")
@provider_opt
@network_opt
@station_options_core
@station_options_interpolate_summarize
@cloup.option("--date", type=click.STRING, required=True)
@cloup.option("--sql-values", type=click.STRING)
@cloup.option_group(
    "Format/Target",
    cloup.option(
        "--format",
        "fmt",
        type=click.Choice(["json", "csv"], case_sensitive=False),
        default="json",
    ),
    cloup.option("--target", type=click.STRING),
    help="Provide either --format or --target.",
)
@cloup.option("--issue", type=click.STRING)
@cloup.option("--si-units", type=click.BOOL, default=True)
@cloup.option("--humanize", type=click.BOOL, default=True)
@cloup.option("--pretty", is_flag=True)
@debug_opt
def summarize(
    provider: str,
    network: str,
    parameter: List[str],
    resolution: str,
    period: List[str],
    date: str,
    issue: str,
    station: str,
    coordinates: str,
    sql_values,
    fmt: str,
    target: str,
    si_units: bool,
    humanize: bool,
    pretty: bool,
    debug: bool,
):
    set_logging_level(debug)

    api = get_api(provider, network)

    try:
        values_ = get_summarize(
            api=api,
            parameter=parameter,
            resolution=resolution,
            period=period,
            date=date,
            issue=issue,
            station_id=station,
            coordinates=coordinates,
            sql_values=sql_values,
            si_units=si_units,
            humanize=humanize,
        )
    except ValueError as ex:
        log.exception(ex)
        sys.exit(1)
    else:
        if values_.df.empty:
            log.error("No data available for given constraints")
            sys.exit(1)

    if target:
        values_.to_target(target)
        return

    indent = None
    if pretty:
        indent = 2

    output = values_.to_format(fmt, indent=indent)

    print(output)  # noqa: T201

    return


@cli.command("radar")
@cloup.option("--dwd", is_flag=True)
@cloup.option("--all", "all_", is_flag=True)
@cloup.option("--odim-code", type=click.STRING)
@cloup.option("--wmo-code", type=click.STRING)
@cloup.option("--country-name", type=click.STRING)
@cloup.constraint(
    RequireExactly(1),
    ["dwd", "all_", "odim_code", "wmo_code", "country_name"],
)
def radar(
    dwd: bool,
    all_: bool,
    odim_code: str,
    wmo_code: str,
    country_name: str,
):
    from wetterdienst.provider.dwd.radar.api import DwdRadarSites
    from wetterdienst.provider.eumetnet.opera.sites import OperaRadarSites

    if dwd:
        data = DwdRadarSites().all()
    else:
        if all_:
            data = OperaRadarSites().all()
        elif odim_code:
            data = OperaRadarSites().by_odimcode(odim_code)
        elif wmo_code:
            data = OperaRadarSites().by_wmocode(wmo_code)
        elif country_name:
            data = OperaRadarSites().by_countryname(country_name)

    output = json.dumps(data, indent=2)

    print(output)  # noqa: T201

    return


if __name__ == "__main__":
    cli()
