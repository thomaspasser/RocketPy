# -*- coding: utf-8 -*-

__author__ = "Giovani Hidalgo Ceotto, Guilherme Fernandes Alves, Lucas Azevedo Pezente, Oscar Mauricio Prada Ramirez, Lucas Kierulff Balabram"
__copyright__ = "Copyright 20XX, RocketPy Team"
__license__ = "MIT"

import bisect
import json
import re
import warnings
from datetime import datetime, timedelta

import numpy as np
import numpy.ma as ma
import pytz
import requests
from collections import namedtuple
from rocketpy.Function import funcify_method

from .Function import Function

from .plots.environment_plots import _EnvironmentPlots
from .prints.environment_prints import _EnvironmentPrints

try:
    import netCDF4
except ImportError:
    has_netCDF4 = False
    warnings.warn(
        "Unable to load netCDF4. NetCDF files and OPeNDAP will not be imported.",
        ImportWarning,
    )
else:
    has_netCDF4 = True


def requires_netCDF4(func):
    def wrapped_func(*args, **kwargs):
        if has_netCDF4:
            func(*args, **kwargs)
        else:
            raise ImportError(
                "This feature requires netCDF4 to be installed. Install it with `pip install netCDF4`"
            )

    return wrapped_func


class Environment:
    """Keeps all environment information stored, such as wind and temperature
    conditions, as well as gravity and rail length.

    Attributes
    ----------

        Constants
        Environment.earthRadius : float
            Value of Earth's Radius = 6.3781e6 m.
        Environment.airGasConstant : float
            Value of Air's Gas Constant = 287.05287 J/K/Kg

        Gravity and Launch Rail Length:
        Environment.railLength : float
            Launch rail length in meters.
        Environment.gravity : float
            Positive value of gravitational acceleration in m/s^2.

        Coordinates and Date:
        Environment.latitude : float
            Launch site latitude.
        Environment.longitude : float
            Launch site longitude.
        Environment.datum: string
            The desired reference ellipsoid model, the following options are
            available: "SAD69", "WGS84", "NAD83", and "SIRGAS2000". The default
            is "SIRGAS2000", then this model will be used if the user make some
            typing mistake
        Environment.initialEast: float
            Launch site East UTM coordinate
        Environment.initialNorth:  float
            Launch site North UTM coordinate
        Environment.initialUtmZone: int
            Launch site UTM zone number
        Environment.initialUtmLetter: string
            Launch site UTM letter, to keep the latitude band and describe the
            UTM Zone
        Environment.initialHemisphere: string
            Launch site S/N hemisphere
        Environment.initialEW: string
            Launch site E/W hemisphere
        Environment.elevation : float
            Launch site elevation.
        Environment.date : datetime
            Date time of launch in UTC.
        Environment.localDate : datetime
                    Date time of launch in the local time zone, defined by Environment.timeZone.
        Environment.timeZone : string
                    Local time zone specification. See pytz for time zone info.

        Topographic information:
        Environment.elevLonArray: array
            Unidimensional array containing the longitude coordinates
        Environment.elevLatArray: array
            Unidimensional array containing the latitude coordinates
        Environment.elevArray: array
            Two-dimensional Array containing the elevation information
        Environment.topographicProfileActivated: bool
            True if the user already set a topographic profile

        Atmosphere Static Conditions:
        Environment.maxExpectedHeight : float
            Maximum altitude in meters to keep weather data.
            Used especially for plotting range.
            Can be altered as desired.
        Environment.pressureISA : Function
            Air pressure in Pa as a function of altitude as defined
            by the International Standard Atmosphere ISO 2533.
            Only defined after load Environment.loadInternationalStandardAtmosphere
            has been called.
            Can be accessed as regular array, or called
            as a function. See Function for more information.
        Environment.temperatureISA : Function
            Air temperature in K as a function of altitude  as defined
            by the International Standard Atmosphere ISO 2533.
            Only defined after load Environment.loadInternationalStandardAtmosphere
            has been called.
            Can be accessed as regular array, or called
            as a function. See Function for more information.
        Environment.pressure : Function
            Air pressure in Pa as a function of altitude.
            Can be accessed as regular array, or called
            as a function. See Function for more information.
        Environment.temperature : Function
            Air temperature in K as a function of altitude.
            Can be accessed as regular array, or called
            as a function. See Function for more information.
        Environment.speedOfSound : Function
            Speed of sound in air in m/s as a function of altitude.
            Can be accessed as regular array, or called
            as a function. See Function for more information.
        Environment.density : Function
            Air density in kg/m³ as a function of altitude.
            Can be accessed as regular array, or called
            as a function. See Function for more information.
        Environment.dynamicViscosity : Function
            Air dynamic viscosity in Pa s as a function of altitude.
            Can be accessed as regular array, or called
            as a function. See Function for more information.

        Atmosphere Wind Conditions:
        Environment.windSpeed : Function
            Wind speed in m/s as a function of altitude.
            Can be accessed as regular array, or called
            as a function. See Function for more information.
        Environment.windDirection : Function
            Wind direction (from which the wind blows)
            in degrees relative to north (positive clockwise)
            as a function of altitude.
            Can be accessed as regular array, or called
            as a function. See Function for more information.
        Environment.windHeading : Function
            Wind heading (direction towards which the wind blows)
            in degrees relative to north (positive clockwise)
            as a function of altitude.
            Can be accessed as regular array, or called
            as a function. See Function for more information.
        Environment.windVelocityX : Function
            Wind U, or X (east) component of wind velocity in m/s as a function of
            altitude.
            Can be accessed as regular array, or called
            as a function. See Function for more information.
        Environment.windVelocityY : Function
            Wind V, or Y (east) component of wind velocity in m/s as a function of
            altitude.
            Can be accessed as regular array, or called
            as a function. See Function for more information.

        Atmospheric Model Details
        Environment.atmosphericModelType : string
            Describes the atmospheric model which is being used.
            Can only assume the following values: 'StandardAtmosphere',
            'CustomAtmosphere', 'WyomingSounding', 'NOAARucSounding',
            'Forecast', 'Reanalysis', 'Ensemble'.
        Environment.atmosphericModelFile : string
            Address of the file used for the atmospheric model being used.
            Only defined for 'WyomingSounding', 'NOAARucSounding',
            'Forecast', 'Reanalysis', 'Ensemble'
        Environment.atmosphericModelDict : dictionary
            Dictionary used to properly interpret netCDF and OPeNDAP
            files. Only defined for 'Forecast', 'Reanalysis', 'Ensemble'.
        Environment.atmosphericModelInitDate : datetime
            Datetime object instance of first available date in netCDF
            and OPeNDAP files when using 'Forecast', 'Reanalysis' or
            'Ensemble'.
        Environment.atmosphericModelEndDate : datetime
            Datetime object instance of last available date in netCDF
            and OPeNDAP files when using 'Forecast', 'Reanalysis' or
            'Ensemble'.
        Environment.atmosphericModelInterval : int
            Hour step between weather condition used in netCDF and
            OPeNDAP files when using 'Forecast', 'Reanalysis' or
            'Ensemble'.
        Environment.atmosphericModelInitLat : float
            Latitude of vertex just before the launch site in netCDF
            and OPeNDAP files when using 'Forecast', 'Reanalysis' or
            'Ensemble'.
        Environment.atmosphericModelEndLat : float
            Latitude of vertex just after the launch site in netCDF
            and OPeNDAP files when using 'Forecast', 'Reanalysis' or
            'Ensemble'.
        Environment.atmosphericModelInitLon : float
            Longitude of vertex just before the launch site in netCDF
            and OPeNDAP files when using 'Forecast', 'Reanalysis' or
            'Ensemble'.
        Environment.atmosphericModelEndLon : float
            Longitude of vertex just after the launch site in netCDF
            and OPeNDAP files when using 'Forecast', 'Reanalysis' or
            'Ensemble'.

        Atmospheric Model Storage
        Environment.latArray : array
            Defined if netCDF or OPeNDAP file is used, for Forecasts,
            Reanalysis and Ensembles. 2x2 matrix for each pressure level of latitudes
            corresponding to the vertices of the grid cell which surrounds
            the launch site.
        Environment.lonArray : array
            Defined if netCDF or OPeNDAP file is used, for Forecasts,
            Reanalysis and Ensembles. 2x2 matrix for each pressure level of longitudes
            corresponding to the vertices of the grid cell which surrounds
            the launch site.
        Environment.lonIndex : int
            Defined if netCDF or OPeNDAP file is used, for Forecasts,
            Reanalysis and Ensembles. Index to a grid longitude which
            is just over the launch site longitude, while lonIndex - 1
            points to a grid longitude which is just under the launch
            site longitude.
        Environment.latIndex : int
            Defined if netCDF or OPeNDAP file is used, for Forecasts,
            Reanalysis and Ensembles. Index to a grid latitude which
            is just over the launch site latitude, while lonIndex - 1
            points to a grid latitude which is just under the launch
            site latitude.
        Environment.geopotentials : array
            Defined if netCDF or OPeNDAP file is used, for Forecasts,
            Reanalysis and Ensembles. 2x2 matrix for each pressure level of geopotential heights
            corresponding to the vertices of the grid cell which surrounds
            the launch site.
        Environment.windUs : array
            Defined if netCDF or OPeNDAP file is used, for Forecasts,
            Reanalysis and Ensembles. 2x2 matrix for each pressure level of wind U (east) component
            corresponding to the vertices of the grid cell which surrounds
            the launch site.
        Environment.windVs : array
            Defined if netCDF or OPeNDAP file is used, for Forecasts,
            Reanalysis and Ensembles. 2x2 matrix for each pressure level of wind V (north) component
            corresponding to the vertices of the grid cell which surrounds
            the launch site.
        Environment.levels : array
            Defined if netCDF or OPeNDAP file is used, for Forecasts,
            Reanalysis and Ensembles. List of pressure levels available
            in the file.
        Environment.temperatures : array
            Defined if netCDF or OPeNDAP file is used, for Forecasts,
            Reanalysis and Ensembles. 2x2 matrix for each pressure level of temperatures
            corresponding to the vertices of the grid cell which surrounds
            the launch site.
        Environment.timeArray : array
            Defined if netCDF or OPeNDAP file is used, for Forecasts,
            Reanalysis and Ensembles. Array of dates available in the
            file.
        Environment.height : array
           Defined if netCDF or OPeNDAP file is used, for Forecasts,
           Reanalysis and Ensembles. List of geometric height
           corresponding to launch site location.

        Atmospheric Model Ensemble Specific Data
        Environment.levelEnsemble : array
            Only defined when using Ensembles.
        Environment.heightEnsemble : array
            Only defined when using Ensembles.
        Environment.temperatureEnsemble : array
            Only defined when using Ensembles.
        Environment.windUEnsemble : array
            Only defined when using Ensembles.
        Environment.windVEnsemble : array
            Only defined when using Ensembles.
        Environment.windHeadingEnsemble : array
            Only defined when using Ensembles.
        Environment.windDirectionEnsemble : array
            Only defined when using Ensembles.
        Environment.windSpeedEnsemble : array
            Only defined when using Ensembles.
        Environment.numEnsembleMembers : int
            Number of ensemble members. Only defined when using Ensembles.
        Environment.ensembleMember : int
            Current selected ensemble member. Only defined when using Ensembles.
    """

    def __init__(
        self,
        railLength,
        gravity=None,
        date=None,
        latitude=0,
        longitude=0,
        elevation=0,
        datum="SIRGAS2000",
        timeZone="UTC",
    ):
        """Initialize Environment class, saving launch rail length,
        launch date, location coordinates and elevation. Note that
        by default the standard atmosphere is loaded until another
        atmospheric model is used. See Environment.setAtmosphericModel
        for details.

        Parameters
        ----------
        railLength : scalar
            Length in which the rocket will be attached to the rail, only
            moving along a fixed direction, that is, the line parallel to the
            rail.
        gravity : int, float, callable, string, array, optional
            Surface gravitational acceleration. Positive values point the
            acceleration down. If None, the Somigliana formula is used to
            compute the gravity at the launch site as a function of height.
        date : array, optional
            Array of length 4, stating (year, month, day, hour (UTC))
            of rocket launch. Must be given if a Forecast, Reanalysis
            or Ensemble, will be set as an atmospheric model.
        latitude : float, optional
            Latitude in degrees (ranging from -90 to 90) of rocket
            launch location. Must be given if a Forecast, Reanalysis
            or Ensemble will be used as an atmospheric model or if
            Open-Elevation will be used to compute elevation.
        longitude : float, optional
            Longitude in degrees (ranging from -180 to 360) of rocket
            launch location. Must be given if a Forecast, Reanalysis
            or Ensemble will be used as an atmospheric model or if
            Open-Elevation will be used to compute elevation.
        elevation : float, optional
            Elevation of launch site measured as height above sea
            level in meters. Alternatively, can be set as
            'Open-Elevation' which uses the Open-Elevation API to
            find elevation data. For this option, latitude and
            longitude must also be specified. Default value is 0.
        datum : string
            The desired reference ellipsoidal model, the following options are
            available: "SAD69", "WGS84", "NAD83", and "SIRGAS2000". The default
            is "SIRGAS2000", then this model will be used if the user make some
            typing mistake.
        timeZone : string, optional
            Name of the time zone. To see all time zones, import pytz and run

        Returns
        -------
        None
        """
        # Save launch rail length
        self.railLength = railLength

        # Initialize constants
        self.earthRadius = 6.3781 * (10**6)
        self.airGasConstant = 287.05287  # in J/K/Kg
        self.standard_g = 9.80665

        # Initialize atmosphere
        self.setAtmosphericModel("StandardAtmosphere")

        # Save latitude and longitude
        if latitude != None and longitude != None:
            self.setLocation(latitude, longitude)
        else:
            self.latitude, self.longitude = None, None

        # Save date
        if date != None:
            self.setDate(date, timeZone)
        else:
            self.date = None
            self.datetime_date = None
            self.localDate = None
            self.timeZone = None

        # Initialize Earth geometry and save datum
        self.datum = datum
        self.ellipsoid = self.setEarthGeometry(datum)

        # Set gravity model
        self.gravity = self.setGravityModel(gravity)

        # Initialize plots and prints objects
        self.prints = _EnvironmentPrints(self)

        # Initialize atmosphere
        self.setAtmosphericModel("StandardAtmosphere")

        # Save latitude and longitude
        self.latitude = latitude
        self.longitude = longitude
        if latitude != None and longitude != None:
            self.setLocation(latitude, longitude)
        else:
            self.latitude, self.longitude = None, None

        # Store launch site coordinates referenced to UTM projection system
        if self.latitude > -80 and self.latitude < 84:
            convert = self.geodesicToUtm(self.latitude, self.longitude)

            self.initialNorth = convert[1]
            self.initialEast = convert[0]
            self.initialUtmZone = convert[2]
            self.initialUtmLetter = convert[3]
            self.initialHemisphere = convert[4]
            self.initialEW = convert[5]

        # Save elevation
        self.elevation = elevation
        self.setElevation(elevation)

        # Recalculate Earth Radius
        self.earthRadius = self.calculateEarthRadius(self.latitude)  # in m

        # Initialize plots and prints object
        self.plots = _EnvironmentPlots(self)

        return None

    def setDate(self, date, timeZone="UTC"):
        """Set date and time of launch and update weather conditions if
        date dependent atmospheric model is used.

        Parameters
        ----------
        date : Datetime
            Datetime object specifying launch date and time.
        timeZone : string, optional
            Name of the time zone. To see all time zones, import pytz and run
        print(pytz.all_timezones). Default time zone is "UTC".

        Return
        ------
        None
        """
        # Store date and configure time zone
        self.timeZone = timeZone
        tz = pytz.timezone(self.timeZone)
        if type(date) != datetime:
            localDate = datetime(*date)
        else:
            localDate = date
        if localDate.tzinfo == None:
            localDate = tz.localize(localDate)
        self.date = date
        self.localDate = localDate
        self.datetime_date = self.localDate.astimezone(pytz.UTC)

        # Update atmospheric conditions if atmosphere type is Forecast,
        # Reanalysis or Ensemble
        try:
            if self.atmosphericModelType in ["Forecast", "Reanalysis", "Ensemble"]:
                self.setAtmosphericModel(
                    self.atmosphericModelFile, self.atmosphericModelDict
                )
        except AttributeError:
            pass

        return None

    def setLocation(self, latitude, longitude):
        """Set latitude and longitude of launch and update atmospheric
        conditions if location dependent model is being used.

        Parameters
        ----------
        latitude : float
            Latitude of launch site. May range from -90 to 90
            degrees.
        longitude : float
            Longitude of launch site. Either from 0 to 360 degrees
            or from -180 to 180 degrees.

        Return
        ------
        None
        """
        # Store latitude and longitude
        self.latitude = latitude
        self.longitude = longitude

        # Update atmospheric conditions if atmosphere type is Forecast,
        # Reanalysis or Ensemble
        if self.atmosphericModelType in ["Forecast", "Reanalysis", "Ensemble"]:
            self.setAtmosphericModel(
                self.atmosphericModelFile, self.atmosphericModelDict
            )

        # Return None

    def setGravityModel(self, gravity):
        """Sets the gravity model to be used in the simulation based
        on the given user input to the gravity parameter.

        Parameters
        ----------
        gravity : None or Function source

        Returns
        -------
        Function
            Function object representing the gravity model.
        """
        if gravity is None:
            return self.somiglianaGravity.setDiscrete(0, self.maxExpectedHeight, 100)
        else:
            return Function(gravity, "height (m)", "gravity (m/s²)").setDiscrete(
                0, self.maxExpectedHeight, 100
            )

    @funcify_method("height (m)", "gravity (m/s²)")
    def somiglianaGravity(self, height):
        """Computes the gravity acceleration with the Somigliana formula.
        An height correction is applied to the normal gravity that is
        accurate for heights used in aviation. The formula is based on the
        WGS84 ellipsoid, but is accurate for other reference ellipsoids.

        Parameters
        ----------
        height : float
            Height above the reference ellipsoid in meters.

        Returns
        -------
        Function
            Function object representing the gravity model.
        """
        a = 6378137.0  # semi_major_axis
        f = 1 / 298.257223563  # flattening_factor
        m_rot = 3.449786506841e-3  # rotation_factor
        g_e = 9.7803253359  # normal gravity at equator
        k_somgl = 1.931852652458e-3  # normal gravity formula const.
        first_ecc_sqrd = 6.694379990141e-3  # square of first eccentricity

        # Compute quantities
        sin_lat_sqrd = (np.sin(self.latitude * np.pi / 180)) ** 2

        gravity_somgl = g_e * (
            (1 + k_somgl * sin_lat_sqrd) / (np.sqrt(1 - first_ecc_sqrd * sin_lat_sqrd))
        )
        height_correction = (
            1
            - height * 2 / a * (1 + f + m_rot - 2 * f * sin_lat_sqrd)
            + 3 * height**2 / a**2
        )

        return height_correction * gravity_somgl

    def setElevation(self, elevation="Open-Elevation"):
        """Set elevation of launch site given user input or using the
        Open-Elevation API.

        Parameters
        ----------
        elevation : float, string, optional
            Elevation of launch site measured as height above sea
            level in meters.
            Alternatively, can be set as 'Open-Elevation' which uses
            the Open-Elevation API to find elevation data. For this
            option, latitude and longitude must have already been
            specified. See Environment.setLocation for more details.

        Return
        ------
        None
        """
        if elevation != "Open-Elevation" and elevation != "SRTM":
            self.elevation = elevation
        # elif elevation == "SRTM" and self.latitude != None and self.longitude != None:
        #     # Trigger the authentication flow.
        #     #ee.Authenticate()
        #     # Initialize the library.
        #     ee.Initialize()

        #     # Calculate elevation
        #     dem  = ee.Image('USGS/SRTMGL1_003')
        #     xy   = ee.Geometry.Point([self.longitude, self.latitude])
        #     elev = dem.sample(xy, 30).first().get('elevation').getInfo()

        #     self.elevation = elev

        elif self.latitude != None and self.longitude != None:
            try:
                print("Fetching elevation from open-elevation.com...")
                requestURL = "https://api.open-elevation.com/api/v1/lookup?locations={:f},{:f}".format(
                    self.latitude, self.longitude
                )
                response = requests.get(requestURL)
                results = response.json()["results"]
                self.elevation = results[0]["elevation"]
                print("Elevation received:", self.elevation)
            except:
                raise RuntimeError("Unable to reach Open-Elevation API servers.")
        else:
            raise ValueError(
                "Latitude and longitude must be set to use"
                " Open-Elevation API. See Environment.setLocation."
            )

    @requires_netCDF4
    def setTopographicProfile(self, type, file, dictionary="netCDF4", crs=None):
        """[UNDER CONSTRUCTION] Defines the Topographic profile, importing data
        from previous downloaded files. Mainly data from the Shuttle Radar
        Topography Mission (SRTM) and NASA Digital Elevation Model will be used
        but other models and methods can be implemented in the future.
        So far, this function can only handle data from NASADEM, available at:
        https://cmr.earthdata.nasa.gov/search/concepts/C1546314436-LPDAAC_ECS.html

        Parameters
        ----------
        type : string
            Defines the topographic model to be used, usually 'NASADEM Merged
            DEM Global 1 arc second nc' can be used. To download this kind of
            data, access 'https://search.earthdata.nasa.gov/search'.
            NASADEM data products were derived from original telemetry data from
            the Shuttle Radar Topography Mission (SRTM).
        file : string
            The path/name of the topographic file. Usually .nc provided by
        dictionary : string, optional
            Dictionary which helps to read the specified file. By default
            'netCDF4' which works well with .nc files will be used.
        crs : string, optional
            Coordinate reference system, by default None, which will use the crs
            provided by the file.
        """

        if type == "NASADEM_HGT":
            if dictionary == "netCDF4":
                rootgrp = netCDF4.Dataset(file, "r", format="NETCDF4")
                self.elevLonArray = rootgrp.variables["lon"][:].tolist()
                self.elevLatArray = rootgrp.variables["lat"][:].tolist()
                self.elevArray = rootgrp.variables["NASADEM_HGT"][:].tolist()
                # crsArray = rootgrp.variables['crs'][:].tolist().
                self.topographicProfileActivated = True

                print("Region covered by the Topographical file: ")
                print(
                    "Latitude from {:.6f}° to {:.6f}°".format(
                        self.elevLatArray[-1], self.elevLatArray[0]
                    )
                )
                print(
                    "Longitude from {:.6f}° to {:.6f}°".format(
                        self.elevLonArray[0], self.elevLonArray[-1]
                    )
                )

        return None

    def getElevationFromTopographicProfile(self, lat, lon):
        """Function which receives as inputs the coordinates of a point and finds its
        elevation in the provided Topographic Profile

        Parameters
        ----------
        lat : float
            latitude of the point.
        lon : float
            longitude of the point.

        Returns
        -------
        elevation: float
            Elevation provided by the topographic data, in meters.

        Raises
        ------
        ValueError
            [description]
        ValueError
            [description]
        """
        if self.topographicProfileActivated == False:
            print(
                "You must define a Topographic profile first, please use the method Environment.setTopographicProfile()"
            )
            return None

        # Find latitude index
        # Check if reversed or sorted
        if self.elevLatArray[0] < self.elevLatArray[-1]:
            # Deal with sorted self.elevLatArray
            latIndex = bisect.bisect(self.elevLatArray, lat)
        else:
            # Deal with reversed self.elevLatArray
            self.elevLatArray.reverse()
            latIndex = len(self.elevLatArray) - bisect.bisect_left(
                self.elevLatArray, lat
            )
            self.elevLatArray.reverse()
        # Take care of latitude value equal to maximum longitude in the grid
        if (
            latIndex == len(self.elevLatArray)
            and self.elevLatArray[latIndex - 1] == lat
        ):
            latIndex = latIndex - 1
        # Check if latitude value is inside the grid
        if latIndex == 0 or latIndex == len(self.elevLatArray):
            raise ValueError(
                "Latitude {:f} not inside region covered by file, which is from {:f} to {:f}.".format(
                    lat, self.elevLatArray[0], self.elevLatArray[-1]
                )
            )

        # Find longitude index
        # Determine if file uses -180 to 180 or 0 to 360
        if self.elevLonArray[0] < 0 or self.elevLonArray[-1] < 0:
            # Convert input to -180 - 180
            lon = lon if lon < 180 else -180 + lon % 180
        else:
            # Convert input to 0 - 360
            lon = lon % 360
        # Check if reversed or sorted
        if self.elevLonArray[0] < self.elevLonArray[-1]:
            # Deal with sorted self.elevLonArray
            lonIndex = bisect.bisect(self.elevLonArray, lon)
        else:
            # Deal with reversed self.elevLonArray
            self.elevLonArray.reverse()
            lonIndex = len(self.elevLonArray) - bisect.bisect_left(
                self.elevLonArray, lon
            )
            self.elevLonArray.reverse()
        # Take care of longitude value equal to maximum longitude in the grid
        if (
            lonIndex == len(self.elevLonArray)
            and self.elevLonArray[lonIndex - 1] == lon
        ):
            lonIndex = lonIndex - 1
        # Check if longitude value is inside the grid
        if lonIndex == 0 or lonIndex == len(self.elevLonArray):
            raise ValueError(
                "Longitude {:f} not inside region covered by file, which is from {:f} to {:f}.".format(
                    lon, self.elevLonArray[0], self.elevLonArray[-1]
                )
            )

        # Get the elevation
        elevation = self.elevArray[latIndex][lonIndex]

        return elevation

    def setAtmosphericModel(
        self,
        type,
        file=None,
        dictionary=None,
        pressure=None,
        temperature=None,
        wind_u=0,
        wind_v=0,
    ):
        """Defines an atmospheric model for the Environment.
        Supported functionality includes using data from the
        International Standard Atmosphere, importing data from
        weather reanalysis, forecasts and ensemble forecasts,
        importing data from upper air soundings and inputting
        data as custom functions, arrays or csv files.

        Parameters
        ----------
        type : string
            One of the following options:
            - 'StandardAtmosphere': sets pressure and temperature
            profiles corresponding to the International Standard
            Atmosphere defined by ISO 2533 and ranging from -2 km
            to 80 km of altitude above sea level. Note that the wind
            profiles are set to zero when this type is chosen.

            - 'WyomingSounding': sets pressure, temperature, wind-u
            and wind-v profiles and surface elevation obtained from
            an upper air sounding given by the file parameter through
            an URL. This URL should point to a data webpage given by
            selecting plot type as text: list, a station and a time at
            http://weather.uwyo.edu/upperair/sounding.html.
            An example of a valid link would be:
            http://weather.uwyo.edu/cgi-bin/sounding?region=samer&TYPE=TEXT%3ALIST&YEAR=2019&MONTH=02&FROM=0200&TO=0200&STNM=82599

            - 'NOAARucSounding': sets pressure, temperature, wind-u
            and wind-v profiles and surface elevation obtained from
            an upper air sounding given by the file parameter through
            an URL. This URL should point to a data webpage obtained
            through NOAA's Ruc Sounding servers, which can be accessed
            in https://rucsoundings.noaa.gov/. Selecting ROABs as the
            initial data source, specifying the station through it's
            WMO-ID and opting for the ASCII (GSD format) button, the
            following example URL opens up: https://rucsoundings.noaa.gov/get_raobs.cgi?data_source=RAOB&latest=latest&start_year=2019&start_month_name=Feb&start_mday=5&start_hour=12&start_min=0&n_hrs=1.0&fcst_len=shortest&airport=83779&text=Ascii%20text%20%28GSD%20format%29&hydrometeors=false&start=latest
            Any ASCII GSD format page from this server can be read,
            so information from virtual soundings such as GFS and NAM
            can also be imported.

            - 'WindyAtmosphere': sets pressure, temperature, wind-u and wind-v
            profiles and surface elevation obtained from the Windy API. See file
            argument to specify the model as either ECMWF, GFS or ICON.

            - 'Forecast': sets pressure, temperature, wind-u and wind-v
            profiles and surface elevation obtained from a weather
            forecast file in netCDF format or from an OPeNDAP URL, both
            given through the file parameter. When this type
            is chosen, the date and location of the launch
            should already have been set through the date and
            location parameters when initializing the Environment.
            The netCDF and OPeNDAP datasets must contain at least
            geopotential height or geopotential, temperature,
            wind-u and wind-v profiles as a function of pressure levels.
            If surface geopotential or geopotential height is given,
            elevation is also set. Otherwise, elevation is not changed.
            Profiles are interpolated bi-linearly using supplied
            latitude and longitude. The date used is the nearest one
            to the date supplied. Furthermore, a dictionary must be
            supplied through the dictionary parameter in order for the
            dataset to be accurately read. Lastly, the dataset must use
            a rectangular grid sorted in either ascending or descending
            order of latitude and longitude.

            - 'Reanalysis': sets pressure, temperature, wind-u and wind-v
            profiles and surface elevation obtained from a weather
            forecast file in netCDF format or from an OPeNDAP URL, both
            given through the file parameter. When this type
            is chosen, the date and location of the launch
            should already have been set through the date and
            location parameters when initializing the Environment.
            The netCDF and OPeNDAP datasets must contain at least
            geopotential height or geopotential, temperature,
            wind-u and wind-v profiles as a function of pressure levels.
            If surface geopotential or geopotential height is given,
            elevation is also set. Otherwise, elevation is not changed.
            Profiles are interpolated bi-linearly using supplied
            latitude and longitude. The date used is the nearest one
            to the date supplied. Furthermore, a dictionary must be
            supplied through the dictionary parameter in order for the
            dataset to be accurately read. Lastly, the dataset must use
            a rectangular grid sorted in either ascending or descending
            order of latitude and longitude.

            - 'Ensemble': sets pressure, temperature, wind-u and wind-v
            profiles and surface elevation obtained from a weather
            forecast file in netCDF format or from an OPeNDAP URL, both
            given through the file parameter. When this type
            is chosen, the date and location of the launch
            should already have been set through the date and
            location parameters when initializing the Environment.
            The netCDF and OPeNDAP datasets must contain at least
            geopotential height or geopotential, temperature,
            wind-u and wind-v profiles as a function of pressure
            levels. If surface geopotential or geopotential height
            is given, elevation is also set. Otherwise, elevation is not
            changed. Profiles are interpolated bi-linearly using supplied
            latitude and longitude. The date used is the nearest one
            to the date supplied. Furthermore, a dictionary must be
            supplied through the dictionary parameter in order for the
            dataset to be accurately read. Lastly, the dataset must use
            a rectangular grid sorted in either ascending or descending
            order of latitude and longitude. By default the first ensemble
            forecast is activated. To activate other ensemble forecasts
            see Environment.selectEnsembleMemberMember().

            - 'CustomAtmosphere': sets pressure, temperature, wind-u
            and wind-v profiles given though the pressure, temperature,
            wind-u and wind-v parameters of this method. If pressure
            or temperature is not given, it will default to the
            International Standard Atmosphere. If the wind components
            are not given, it will default to 0.

        file : string, optional
            String that must be given when type is either
            'WyomingSounding', 'Forecast', 'Reanalysis', 'Ensemble' or 'Windy'.
            It specifies the location of the data given, either through
            a local file address or a URL.
            If type is 'Forecast', this parameter can also be either
            'GFS', 'FV3', 'RAP' or 'NAM' for latest of these forecasts.
            References: GFS: Global - 0.25deg resolution - Updates every 6 hours, forecast for 81 points spaced by 3 hours
                        FV3: Global - 0.25deg resolution - Updates every 6 hours, forecast for 129 points spaced by 3 hours
                        RAP: Regional USA - 0.19deg resolution - Updates hourly, forecast for 40 points spaced hourly
                        NAM: Regional CONUS Nest - 5 km resolution - Updates every 6 hours, forecast for 21 points spaced by 3 hours
            If type is 'Ensemble', this parameter can also be either
            'GEFS', or 'CMC' for the latest of these ensembles.
            References: GEFS: Global, bias-corrected, 0.5deg resolution, 21 forecast members, Updates every 6 hours, forecast for 65 points spaced by 4 hours
                       CMC: Global, 0.5deg resolution, 21 forecast members, Updates every 12 hours, forecast for 65 points spaced by 4 hours
            If type is 'Windy', this parameter can be either 'GFS', 'ECMWF', 'ICON' or
            'ICONEU'
            Default in this case is 'ecmwf'.
        dictionary : dictionary, string, optional
            Dictionary that must be given when type is either
            'Forecast', 'Reanalysis' or 'Ensemble'.
            It specifies the dictionary to be used when reading netCDF
            and OPeNDAP files, allowing the correct retrieval of data.
            Acceptable values include 'ECMWF', 'NOAA' and 'UCAR' for
            default dictionaries which can generally be used to read
            datasets from these institutes.
            Alternatively, a dictionary structure can also be given,
            specifying the short names used for time, latitude, longitude,
            pressure levels, temperature profile, geopotential or
            geopotential height profile, wind-u and wind-v profiles in
            the dataset given in the file parameter. Additionally,
            ensemble dictionaries must have the ensemble as well.
            An example is the following dictionary, used for 'NOAA':
                                  {'time': 'time',
                               'latitude': 'lat',
                              'longitude': 'lon',
                                  'level': 'lev',
                               'ensemble': 'ens',
                            'temperature': 'tmpprs',
            'surface_geopotential_height': 'hgtsfc',
                    'geopotential_height': 'hgtprs',
                           'geopotential': None,
                                 'u_wind': 'ugrdprs',
                                 'v_wind': 'vgrdprs'}
        pressure : float, string, array, callable, optional
            This defines the atmospheric pressure profile.
            Should be given if the type parameter is 'CustomAtmosphere'. If not,
            than the the Standard Atmosphere pressure will be used.
            If a float is given, it will define a constant pressure
            profile. The float should be in units of Pa.
            If a string is given, it should point to a .CSV file
            containing at most one header line and two columns of data.
            The first column must be the geometric height above sea level in
            meters while the second column must be the pressure in Pa.
            If an array is given, it is expected to be a list or array
            of coordinates (height in meters, pressure in Pa).
            Finally, a callable or function is also accepted. The
            function should take one argument, the height above sea
            level in meters and return a corresponding pressure in Pa.
        temperature : float, string, array, callable, optional
            This defines the atmospheric temperature profile.
            Should be given if the type parameter is 'CustomAtmosphere'. If not,
            than the the Standard Atmosphere temperature will be used.
            If a float is given, it will define a constant temperature
            profile. The float should be in units of K.
            If a string is given, it should point to a .CSV file
            containing at most one header line and two columns of data.
            The first column must be the geometric height above sea level in
            meters while the second column must be the temperature in K.
            If an array is given, it is expected to be a list or array
            of coordinates (height in meters, temperature in K).
            Finally, a callable or function is also accepted. The
            function should take one argument, the height above sea
            level in meters and return a corresponding temperature in K.
        wind_u : float, string, array, callable, optional
            This defines the atmospheric wind-u profile, corresponding
            the the magnitude of the wind speed heading East.
            Should be given if the type parameter is 'CustomAtmosphere'. If not,
            it will be assumed to be constant and equal to 0.
            If a float is given, it will define a constant wind-u
            profile. The float should be in units of m/s.
            If a string is given, it should point to a .CSV file
            containing at most one header line and two columns of data.
            The first column must be the geometric height above sea level in
            meters while the second column must be the wind-u in m/s.
            If an array is given, it is expected to be an array of
            coordinates (height in meters, wind-u in m/s).
            Finally, a callable or function is also accepted. The
            function should take one argument, the height above sea
            level in meters and return a corresponding wind-u in m/s.
        wind_v : float, string, array, callable, optional
            This defines the atmospheric wind-v profile, corresponding
            the the magnitude of the wind speed heading North.
            Should be given if the type parameter is 'CustomAtmosphere'. If not,
            it will be assumed to be constant and equal to 0.
            If a float is given, it will define a constant wind-v
            profile. The float should be in units of m/s.
            If a string is given, it should point to a .CSV file
            containing at most one header line and two columns of data.
            The first column must be the geometric height above sea level in
            meters while the second column must be the wind-v in m/s.
            If an array is given, it is expected to be an array of
            coordinates (height in meters, wind-v in m/s).
            Finally, a callable or function is also accepted. The
            function should take one argument, the height above sea
            level in meters and return a corresponding wind-v in m/s.

        Return
        ------
        None
        """
        # Save atmospheric model type
        self.atmosphericModelType = type

        # Handle each case
        if type == "StandardAtmosphere":
            self.processStandardAtmosphere()
        elif type == "WyomingSounding":
            self.processWyomingSounding(file)
            # Save file
            self.atmosphericModelFile = file
        elif type == "NOAARucSounding":
            self.processNOAARUCSounding(file)
            # Save file
            self.atmosphericModelFile = file
        elif type == "Forecast" or type == "Reanalysis":
            # Process default forecasts if requested
            if file == "GFS":
                # Define dictionary
                dictionary = {
                    "time": "time",
                    "latitude": "lat",
                    "longitude": "lon",
                    "level": "lev",
                    "temperature": "tmpprs",
                    "surface_geopotential_height": "hgtsfc",
                    "geopotential_height": "hgtprs",
                    "geopotential": None,
                    "u_wind": "ugrdprs",
                    "v_wind": "vgrdprs",
                }
                # Attempt to get latest forecast
                timeAttempt = datetime.utcnow()
                success = False
                attemptCount = 0
                while not success and attemptCount < 10:
                    timeAttempt -= timedelta(hours=6 * attemptCount)
                    file = "https://nomads.ncep.noaa.gov/dods/gfs_0p25/gfs{:04d}{:02d}{:02d}/gfs_0p25_{:02d}z".format(
                        timeAttempt.year,
                        timeAttempt.month,
                        timeAttempt.day,
                        6 * (timeAttempt.hour // 6),
                    )
                    try:
                        self.processForecastReanalysis(file, dictionary)
                        success = True
                    except OSError:
                        attemptCount += 1
                if not success:
                    raise RuntimeError(
                        "Unable to load latest weather data for GFS through " + file
                    )
            elif file == "FV3":
                # Define dictionary
                dictionary = {
                    "time": "time",
                    "latitude": "lat",
                    "longitude": "lon",
                    "level": "lev",
                    "temperature": "tmpprs",
                    "surface_geopotential_height": "hgtsfc",
                    "geopotential_height": "hgtprs",
                    "geopotential": None,
                    "u_wind": "ugrdprs",
                    "v_wind": "vgrdprs",
                }
                # Attempt to get latest forecast
                timeAttempt = datetime.utcnow()
                success = False
                attemptCount = 0
                while not success and attemptCount < 10:
                    timeAttempt -= timedelta(hours=6 * attemptCount)
                    file = "https://nomads.ncep.noaa.gov/dods/gfs_0p25_parafv3/gfs{:04d}{:02d}{:02d}/gfs_0p25_parafv3_{:02d}z".format(
                        timeAttempt.year,
                        timeAttempt.month,
                        timeAttempt.day,
                        6 * (timeAttempt.hour // 6),
                    )
                    try:
                        self.processForecastReanalysis(file, dictionary)
                        success = True
                    except OSError:
                        attemptCount += 1
                if not success:
                    raise RuntimeError(
                        "Unable to load latest weather data for FV3 through " + file
                    )
            elif file == "NAM":
                # Define dictionary
                dictionary = {
                    "time": "time",
                    "latitude": "lat",
                    "longitude": "lon",
                    "level": "lev",
                    "temperature": "tmpprs",
                    "surface_geopotential_height": "hgtsfc",
                    "geopotential_height": "hgtprs",
                    "geopotential": None,
                    "u_wind": "ugrdprs",
                    "v_wind": "vgrdprs",
                }
                # Attempt to get latest forecast
                timeAttempt = datetime.utcnow()
                success = False
                attemptCount = 0
                while not success and attemptCount < 10:
                    timeAttempt -= timedelta(hours=6 * attemptCount)
                    file = "https://nomads.ncep.noaa.gov/dods/nam/nam{:04d}{:02d}{:02d}/nam_conusnest_{:02d}z".format(
                        timeAttempt.year,
                        timeAttempt.month,
                        timeAttempt.day,
                        6 * (timeAttempt.hour // 6),
                    )
                    try:
                        self.processForecastReanalysis(file, dictionary)
                        success = True
                    except OSError:
                        attemptCount += 1
                if not success:
                    raise RuntimeError(
                        "Unable to load latest weather data for NAM through " + file
                    )
            elif file == "RAP":
                # Define dictionary
                dictionary = {
                    "time": "time",
                    "latitude": "lat",
                    "longitude": "lon",
                    "level": "lev",
                    "temperature": "tmpprs",
                    "surface_geopotential_height": "hgtsfc",
                    "geopotential_height": "hgtprs",
                    "geopotential": None,
                    "u_wind": "ugrdprs",
                    "v_wind": "vgrdprs",
                }
                # Attempt to get latest forecast
                timeAttempt = datetime.utcnow()
                success = False
                attemptCount = 0
                while not success and attemptCount < 10:
                    timeAttempt -= timedelta(hours=1 * attemptCount)
                    file = "https://nomads.ncep.noaa.gov/dods/rap/rap{:04d}{:02d}{:02d}/rap_{:02d}z".format(
                        timeAttempt.year,
                        timeAttempt.month,
                        timeAttempt.day,
                        timeAttempt.hour,
                    )
                    try:
                        self.processForecastReanalysis(file, dictionary)
                        success = True
                    except OSError:
                        attemptCount += 1
                if not success:
                    raise RuntimeError(
                        "Unable to load latest weather data for RAP through " + file
                    )
            # Process other forecasts or reanalysis
            else:
                # Check if default dictionary was requested
                if dictionary == "ECMWF":
                    dictionary = {
                        "time": "time",
                        "latitude": "latitude",
                        "longitude": "longitude",
                        "level": "level",
                        "temperature": "t",
                        "surface_geopotential_height": None,
                        "geopotential_height": None,
                        "geopotential": "z",
                        "u_wind": "u",
                        "v_wind": "v",
                    }
                elif dictionary == "NOAA":
                    dictionary = {
                        "time": "time",
                        "latitude": "lat",
                        "longitude": "lon",
                        "level": "lev",
                        "temperature": "tmpprs",
                        "surface_geopotential_height": "hgtsfc",
                        "geopotential_height": "hgtprs",
                        "geopotential": None,
                        "u_wind": "ugrdprs",
                        "v_wind": "vgrdprs",
                    }
                elif dictionary is None:
                    raise TypeError(
                        "Please specify a dictionary or choose a default one such as ECMWF or NOAA."
                    )
                # Process forecast or reanalysis
                self.processForecastReanalysis(file, dictionary)
            # Save dictionary and file
            self.atmosphericModelFile = file
            self.atmosphericModelDict = dictionary
        elif type == "Ensemble":
            # Process default forecasts if requested
            if file == "GEFS":
                # Define dictionary
                dictionary = {
                    "time": "time",
                    "latitude": "lat",
                    "longitude": "lon",
                    "level": "lev",
                    "ensemble": "ens",
                    "temperature": "tmpprs",
                    "surface_geopotential_height": None,
                    "geopotential_height": "hgtprs",
                    "geopotential": None,
                    "u_wind": "ugrdprs",
                    "v_wind": "vgrdprs",
                }
                # Attempt to get latest forecast
                timeAttempt = datetime.utcnow()
                success = False
                attemptCount = 0
                while not success and attemptCount < 10:
                    timeAttempt -= timedelta(hours=6 * attemptCount)
                    file = "https://nomads.ncep.noaa.gov/dods/gens_bc/gens{:04d}{:02d}{:02d}/gep_all_{:02d}z".format(
                        timeAttempt.year,
                        timeAttempt.month,
                        timeAttempt.day,
                        6 * (timeAttempt.hour // 6),
                    )
                    try:
                        self.processEnsemble(file, dictionary)
                        success = True
                    except OSError:
                        attemptCount += 1
                if not success:
                    raise RuntimeError(
                        "Unable to load latest weather data for GEFS through " + file
                    )
            elif file == "CMC":
                # Define dictionary
                dictionary = {
                    "time": "time",
                    "latitude": "lat",
                    "longitude": "lon",
                    "level": "lev",
                    "ensemble": "ens",
                    "temperature": "tmpprs",
                    "surface_geopotential_height": None,
                    "geopotential_height": "hgtprs",
                    "geopotential": None,
                    "u_wind": "ugrdprs",
                    "v_wind": "vgrdprs",
                }
                # Attempt to get latest forecast
                timeAttempt = datetime.utcnow()
                success = False
                attemptCount = 0
                while not success and attemptCount < 10:
                    timeAttempt -= timedelta(hours=12 * attemptCount)
                    file = "https://nomads.ncep.noaa.gov/dods/cmcens/cmcens{:04d}{:02d}{:02d}/cmcens_all_{:02d}z".format(
                        timeAttempt.year,
                        timeAttempt.month,
                        timeAttempt.day,
                        12 * (timeAttempt.hour // 12),
                    )
                    try:
                        self.processEnsemble(file, dictionary)
                        success = True
                    except OSError:
                        attemptCount += 1
                if not success:
                    raise RuntimeError(
                        "Unable to load latest weather data for CMC through " + file
                    )
            # Process other forecasts or reanalysis
            else:
                # Check if default dictionary was requested
                if dictionary == "ECMWF":
                    dictionary = {
                        "time": "time",
                        "latitude": "latitude",
                        "longitude": "longitude",
                        "level": "level",
                        "ensemble": "number",
                        "temperature": "t",
                        "surface_geopotential_height": None,
                        "geopotential_height": None,
                        "geopotential": "z",
                        "u_wind": "u",
                        "v_wind": "v",
                    }
                elif dictionary == "NOAA":
                    dictionary = {
                        "time": "time",
                        "latitude": "lat",
                        "longitude": "lon",
                        "level": "lev",
                        "ensemble": "ens",
                        "temperature": "tmpprs",
                        "surface_geopotential_height": None,
                        "geopotential_height": "hgtprs",
                        "geopotential": None,
                        "u_wind": "ugrdprs",
                        "v_wind": "vgrdprs",
                    }
                # Process forecast or reanalysis
                self.processEnsemble(file, dictionary)
            # Save dictionary and file
            self.atmosphericModelFile = file
            self.atmosphericModelDict = dictionary
        elif type == "CustomAtmosphere":
            self.processCustomAtmosphere(pressure, temperature, wind_u, wind_v)
        elif type == "Windy":
            self.processWindyAtmosphere(file)
        else:
            raise ValueError("Unknown model type.")

        # Calculate air density
        self.calculateDensityProfile()

        # Calculate speed of sound
        self.calculateSpeedOfSoundProfile()

        # Update dynamic viscosity
        self.calculateDynamicViscosity()

        return None

    def processStandardAtmosphere(self):
        """Sets pressure and temperature profiles corresponding to the
        International Standard Atmosphere defined by ISO 2533 and
        ranging from -2 km to 80 km of altitude above sea level. Note
        that the wind profiles are set to zero.

        Parameters
        ---------
        None

        Returns
        -------
        None
        """
        # Load international standard atmosphere
        self.loadInternationalStandardAtmosphere()

        # Save temperature, pressure and wind profiles
        self.pressure = self.pressureISA
        self.temperature = self.temperatureISA
        self.windDirection = Function(
            0,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Direction (Deg True)",
            interpolation="linear",
        )
        self.windHeading = Function(
            0,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Heading (Deg True)",
            interpolation="linear",
        )
        self.windSpeed = Function(
            0,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Speed (m/s)",
            interpolation="linear",
        )
        self.windVelocityX = Function(
            0,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity X (m/s)",
            interpolation="linear",
        )
        self.windVelocityY = Function(
            0,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity Y (m/s)",
            interpolation="linear",
        )

        # Set maximum expected height
        self.maxExpectedHeight = 80000

        return None

    def processCustomAtmosphere(
        self, pressure=None, temperature=None, wind_u=0, wind_v=0
    ):
        """Import pressure, temperature and wind profile given by user.

        Parameters
        ----------
        pressure : float, string, array, callable, optional
            This defines the atmospheric pressure profile.
            Should be given if the type parameter is 'CustomAtmosphere'. If not,
            than the the Standard Atmosphere pressure will be used.
            If a float is given, it will define a constant pressure
            profile. The float should be in units of Pa.
            If a string is given, it should point to a .CSV file
            containing at most one header line and two columns of data.
            The first column must be the geometric height above sea level in
            meters while the second column must be the pressure in Pa.
            If an array is given, it is expected to be a list or array
            of coordinates (height in meters, pressure in Pa).
            Finally, a callable or function is also accepted. The
            function should take one argument, the height above sea
            level in meters and return a corresponding pressure in Pa.
        temperature : float, string, array, callable, optional
            This defines the atmospheric temperature profile.
            Should be given if the type parameter is 'CustomAtmosphere'. If not,
            than the the Standard Atmosphere temperature will be used.
            If a float is given, it will define a constant temperature
            profile. The float should be in units of K.
            If a string is given, it should point to a .CSV file
            containing at most one header line and two columns of data.
            The first column must be the geometric height above sea level in
            meters while the second column must be the temperature in K.
            If an array is given, it is expected to be a list or array
            of coordinates (height in meters, temperature in K).
            Finally, a callable or function is also accepted. The
            function should take one argument, the height above sea
            level in meters and return a corresponding temperature in K.
        wind_u : float, string, array, callable, optional
            This defines the atmospheric wind-u profile, corresponding
            the the magnitude of the wind speed heading East.
            Should be given if the type parameter is 'CustomAtmosphere'. If not,
            it will be assumed constant and 0.
            If a float is given, it will define a constant wind-u
            profile. The float should be in units of m/s.
            If a string is given, it should point to a .CSV file
            containing at most one header line and two columns of data.
            The first column must be the geometric height above sea level in
            meters while the second column must be the wind-u in m/s.
            If an array is given, it is expected to be an array of
            coordinates (height in meters, wind-u in m/s).
            Finally, a callable or function is also accepted. The
            function should take one argument, the height above sea
            level in meters and return a corresponding wind-u in m/s.
        wind_v : float, string, array, callable, optional
            This defines the atmospheric wind-v profile, corresponding
            the the magnitude of the wind speed heading North.
            Should be given if the type parameter is 'CustomAtmosphere'. If not,
            it will be assumed constant and 0.
            If a float is given, it will define a constant wind-v
            profile. The float should be in units of m/s.
            If a string is given, it should point to a .CSV file
            containing at most one header line and two columns of data.
            The first column must be the geometric height above sea level in
            meters while the second column must be the wind-v in m/s.
            If an array is given, it is expected to be an array of
            coordinates (height in meters, wind-v in m/s).
            Finally, a callable or function is also accepted. The
            function should take one argument, the height above sea
            level in meters and return a corresponding wind-v in m/s.

        Return
        ------
        None
        """
        # Initialize an estimate of the maximum expected atmospheric model height
        maxExpectedHeight = 1000

        # Save pressure profile
        if pressure is None:
            # Use standard atmosphere
            self.pressure = self.pressureISA
        else:
            # Use custom input
            self.pressure = Function(
                pressure,
                inputs="Height Above Sea Level (m)",
                outputs="Pressure (Pa)",
                interpolation="linear",
            )
            # Check maximum height of custom pressure input
            if not callable(self.pressure.source):
                maxExpectedHeight = max(self.pressure[-1, 0], maxExpectedHeight)

        # Save temperature profile
        if temperature is None:
            # Use standard atmosphere
            self.temperature = self.temperatureISA
        else:
            self.temperature = Function(
                temperature,
                inputs="Height Above Sea Level (m)",
                outputs="Temperature (K)",
                interpolation="linear",
            )
            # Check maximum height of custom temperature input
            if not callable(self.temperature.source):
                maxExpectedHeight = max(self.temperature[-1, 0], maxExpectedHeight)

        # Save wind profile
        self.windVelocityX = Function(
            wind_u,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity X (m/s)",
            interpolation="linear",
        )
        self.windVelocityY = Function(
            wind_v,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity Y (m/s)",
            interpolation="linear",
        )
        # Check maximum height of custom wind input
        if not callable(self.windVelocityX.source):
            maxExpectedHeight = max(self.windVelocityX[-1, 0], maxExpectedHeight)
        if not callable(self.windVelocityY.source):
            maxExpectedHeight = max(self.windVelocityY[-1, 0], maxExpectedHeight)

        # Compute wind profile direction and heading
        windHeading = (
            lambda h: np.arctan2(self.windVelocityX(h), self.windVelocityY(h))
            * (180 / np.pi)
            % 360
        )
        self.windHeading = Function(
            windHeading,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Heading (Deg True)",
            interpolation="linear",
        )

        def windDirection(h):
            return (windHeading(h) - 180) % 360

        self.windDirection = Function(
            windDirection,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Direction (Deg True)",
            interpolation="linear",
        )

        def windSpeed(h):
            return np.sqrt(self.windVelocityX(h) ** 2 + self.windVelocityY(h) ** 2)

        self.windSpeed = Function(
            windSpeed,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Speed (m/s)",
            interpolation="linear",
        )

        # Save maximum expected height
        self.maxExpectedHeight = maxExpectedHeight

        return None

    def processWindyAtmosphere(self, model="ECMWF"):
        """Process data from Windy.com to retrieve atmospheric forecast data.

        Parameters
        ----------
        model : string, optional
            The atmospheric model to use. Default is 'ECMWF'. Options are: 'ECMWF' for
            the ECMWF-HRES model, 'GFS' for the GFS model, 'ICON' for the ICON-Global
            model or 'ICONEU' for the ICON-EU model.
        """

        # Process the model string
        model = model.lower()
        if model[-1] == "u":  # case iconEu
            model = "".join([model[:4], model[4].upper(), model[4 + 1 :]])
        # Load data from Windy.com: json file
        url = f"https://node.windy.com/forecast/meteogram/{model}/{self.latitude}/{self.longitude}/?step=undefined"
        try:
            response = requests.get(url).json()
        except:
            if model == "iconEu":
                raise ValueError(
                    "Could not get a valid response for Icon-EU from Windy. Check if the latitude and longitude coordinates set are inside Europe.",
                )
            raise

        # Determine time index from model
        timeArray = np.array(response["data"]["hours"])
        timeUnits = "milliseconds since 1970-01-01 00:00:00"
        launchTimeInUnits = netCDF4.date2num(self.datetime_date, timeUnits)
        # Find the index of the closest time in timeArray to the launch time
        timeIndex = (np.abs(timeArray - launchTimeInUnits)).argmin()

        # Define available pressure levels
        pressureLevels = np.array(
            [1000, 950, 925, 900, 850, 800, 700, 600, 500, 400, 300, 250, 200, 150]
        )

        # Process geopotential height array
        geopotentialHeightArray = np.array(
            [response["data"][f"gh-{pL}h"][timeIndex] for pL in pressureLevels]
        )
        # Convert geopotential height to geometric altitude (ASL)
        R = self.earthRadius
        altitudeArray = R * geopotentialHeightArray / (R - geopotentialHeightArray)

        # Process temperature array (in Kelvin)
        temperatureArray = np.array(
            [response["data"][f"temp-{pL}h"][timeIndex] for pL in pressureLevels]
        )

        # Process wind-u and wind-v array (in m/s)
        windUArray = np.array(
            [response["data"][f"wind_u-{pL}h"][timeIndex] for pL in pressureLevels]
        )
        windVArray = np.array(
            [response["data"][f"wind_v-{pL}h"][timeIndex] for pL in pressureLevels]
        )

        # Determine wind speed, heading and direction
        windSpeedArray = np.sqrt(windUArray**2 + windVArray**2)
        windHeadingArray = np.arctan2(windUArray, windVArray) * (180 / np.pi) % 360
        windDirectionArray = (windHeadingArray - 180) % 360

        # Combine all data into big array
        data_array = np.ma.column_stack(
            [
                100 * pressureLevels,  # Convert hPa to Pa
                altitudeArray,
                temperatureArray,
                windUArray,
                windVArray,
                windHeadingArray,
                windDirectionArray,
                windSpeedArray,
            ]
        )

        # Save atmospheric data
        self.pressure = Function(
            data_array[:, (1, 0)],
            inputs="Height Above Sea Level (m)",
            outputs="Pressure (Pa)",
            interpolation="linear",
        )
        self.temperature = Function(
            data_array[:, (1, 2)],
            inputs="Height Above Sea Level (m)",
            outputs="Temperature (K)",
            interpolation="linear",
        )
        self.windDirection = Function(
            data_array[:, (1, 6)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Direction (Deg True)",
            interpolation="linear",
        )
        self.windHeading = Function(
            data_array[:, (1, 5)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Heading (Deg True)",
            interpolation="linear",
        )
        self.windSpeed = Function(
            data_array[:, (1, 7)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Speed (m/s)",
            interpolation="linear",
        )
        self.windVelocityX = Function(
            data_array[:, (1, 3)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity X (m/s)",
            interpolation="linear",
        )
        self.windVelocityY = Function(
            data_array[:, (1, 4)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity Y (m/s)",
            interpolation="linear",
        )

        # Save maximum expected height
        self.maxExpectedHeight = max(altitudeArray[0], altitudeArray[-1])

        # Get elevation data from file
        self.elevation = response["header"]["elevation"]

        # Compute info data
        self.atmosphericModelInitDate = netCDF4.num2date(timeArray[0], units=timeUnits)
        self.atmosphericModelEndDate = netCDF4.num2date(timeArray[-1], units=timeUnits)
        self.atmosphericModelInterval = netCDF4.num2date(
            (timeArray[-1] - timeArray[0]) / (len(timeArray) - 1), units=timeUnits
        ).hour
        self.atmosphericModelInitLat = self.latitude
        self.atmosphericModelEndLat = self.latitude
        self.atmosphericModelInitLon = self.longitude
        self.atmosphericModelEndLon = self.longitude

        # Save debugging data
        self.geopotentials = geopotentialHeightArray
        self.windUs = windUArray
        self.windVs = windVArray
        self.levels = pressureLevels
        self.temperatures = temperatureArray
        self.timeArray = timeArray
        self.height = altitudeArray

    def processWyomingSounding(self, file):
        """Import and process the upper air sounding data from Wyoming
        Upper Air Soundings database given by the url in file. Sets
        pressure, temperature, wind-u, wind-v profiles and surface elevation.

        Parameters
        ----------
        file : string
            URL of an upper air sounding data output from Wyoming
            Upper Air Soundings database.
            Example:
            http://weather.uwyo.edu/cgi-bin/sounding?region=samer&TYPE=TEXT%3ALIST&YEAR=2019&MONTH=02&FROM=0200&TO=0200&STNM=82599
            More can be found at:
            http://weather.uwyo.edu/upperair/sounding.html.

        Returns
        -------
        None
        """
        # Request Wyoming Sounding from file url
        response = requests.get(file)
        if response.status_code != 200:
            raise ImportError("Unable to load " + file + ".")
        if len(re.findall("Can't get .+ Observations at", response.text)):
            raise ValueError(
                re.findall("Can't get .+ Observations at .+", response.text)[0]
                + " Check station number and date."
            )
        if response.text == "Invalid OUTPUT: specified\n":
            raise ValueError(
                "Invalid OUTPUT: specified. Make sure the output is Text: List."
            )

        # Process Wyoming Sounding by finding data table and station info
        response_split_text = re.split("(<.{0,1}PRE>)", response.text)
        data_table = response_split_text[2]
        station_info = response_split_text[6]

        # Transform data table into np array
        data_array = []
        for line in data_table.split("\n")[
            5:-1
        ]:  # Split data table into lines and remove header and footer
            columns = re.split(" +", line)  # Split line into columns
            if (
                len(columns) == 12
            ):  # 12 is the number of column entries when all entries are given
                data_array.append(columns[1:])
        data_array = np.array(data_array, dtype=float)

        # Retrieve pressure from data array
        data_array[:, 0] = 100 * data_array[:, 0]  # Converts hPa to Pa
        self.pressure = Function(
            data_array[:, (1, 0)],
            inputs="Height Above Sea Level (m)",
            outputs="Pressure (Pa)",
            interpolation="linear",
        )

        # Retrieve temperature from data array
        data_array[:, 2] = data_array[:, 2] + 273.15  # Converts C to K
        self.temperature = Function(
            data_array[:, (1, 2)],
            inputs="Height Above Sea Level (m)",
            outputs="Temperature (K)",
            interpolation="linear",
        )

        # Retrieve wind-u and wind-v from data array
        data_array[:, 7] = data_array[:, 7] * 1.852 / 3.6  # Converts Knots to m/s
        data_array[:, 5] = (
            data_array[:, 6] + 180
        ) % 360  # Convert wind direction to wind heading
        data_array[:, 3] = data_array[:, 7] * np.sin(data_array[:, 5] * np.pi / 180)
        data_array[:, 4] = data_array[:, 7] * np.cos(data_array[:, 5] * np.pi / 180)

        # Convert geopotential height to geometric height
        R = self.earthRadius
        data_array[:, 1] = R * data_array[:, 1] / (R - data_array[:, 1])

        # Save atmospheric data
        self.windDirection = Function(
            data_array[:, (1, 6)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Direction (Deg True)",
            interpolation="linear",
        )
        self.windHeading = Function(
            data_array[:, (1, 5)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Heading (Deg True)",
            interpolation="linear",
        )
        self.windSpeed = Function(
            data_array[:, (1, 7)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Speed (m/s)",
            interpolation="linear",
        )
        self.windVelocityX = Function(
            data_array[:, (1, 3)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity X (m/s)",
            interpolation="linear",
        )
        self.windVelocityY = Function(
            data_array[:, (1, 4)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity Y (m/s)",
            interpolation="linear",
        )

        # Retrieve station elevation from station info
        station_elevation_text = station_info.split("\n")[6]

        # Convert station elevation text into float value
        self.elevation = float(
            re.findall(r"[0-9]+\.[0-9]+|[0-9]+", station_elevation_text)[0]
        )

        # Save maximum expected height
        self.maxExpectedHeight = data_array[-1, 1]

        return None

    def processNOAARUCSounding(self, file):
        """Import and process the upper air sounding data from NOAA
        Ruc Soundings database (https://rucsoundings.noaa.gov/) given as
        ASCII GSD format pages passed by its url to the file parameter. Sets
        pressure, temperature, wind-u, wind-v profiles and surface elevation.

        Parameters
        ----------
        file : string
            URL of an upper air sounding data output from NOAA Ruc Soundings
            in ASCII GSD format.
            Example:
            https://rucsoundings.noaa.gov/get_raobs.cgi?data_source=RAOB&latest=latest&start_year=2019&start_month_name=Feb&start_mday=5&start_hour=12&start_min=0&n_hrs=1.0&fcst_len=shortest&airport=83779&text=Ascii%20text%20%28GSD%20format%29&hydrometeors=false&start=latest
            More can be found at:
            https://rucsoundings.noaa.gov/.

        Returns
        -------
        None
        """
        # Request NOAA Ruc Sounding from file url
        response = requests.get(file)
        if response.status_code != 200 or len(response.text) < 10:
            raise ImportError("Unable to load " + file + ".")

        # Split response into lines
        lines = response.text.split("\n")

        # Process GSD format (https://rucsoundings.noaa.gov/raob_format.html)

        # Extract elevation data
        for line in lines:
            # Split line into columns
            columns = re.split(" +", line)[1:]
            if len(columns) > 0:
                if columns[0] == "1" and columns[5] != "99999":
                    # Save elevation
                    self.elevation = float(columns[5])
                else:
                    # No elevation data available
                    pass

        # Extract pressure as a function of height
        pressure_array = []
        for line in lines:
            # Split line into columns
            columns = re.split(" +", line)[1:]
            if len(columns) >= 6:
                if columns[0] in ["4", "5", "6", "7", "8", "9"]:
                    # Convert columns to floats
                    columns = np.array(columns, dtype=float)
                    # Select relevant columns
                    columns = columns[[2, 1]]
                    # Check if values exist
                    if max(columns) != 99999:
                        # Save value
                        pressure_array.append(columns)
        pressure_array = np.array(pressure_array)

        # Extract temperature as a function of height
        temperature_array = []
        for line in lines:
            # Split line into columns
            columns = re.split(" +", line)[1:]
            if len(columns) >= 6:
                if columns[0] in ["4", "5", "6", "7", "8", "9"]:
                    # Convert columns to floats
                    columns = np.array(columns, dtype=float)
                    # Select relevant columns
                    columns = columns[[2, 3]]
                    # Check if values exist
                    if max(columns) != 99999:
                        # Save value
                        temperature_array.append(columns)
        temperature_array = np.array(temperature_array)

        # Extract wind speed and direction as a function of height
        windSpeed_array = []
        windDirection_array = []
        for line in lines:
            # Split line into columns
            columns = re.split(" +", line)[1:]
            if len(columns) >= 6:
                if columns[0] in ["4", "5", "6", "7", "8", "9"]:
                    # Convert columns to floats
                    columns = np.array(columns, dtype=float)
                    # Select relevant columns
                    columns = columns[[2, 5, 6]]
                    # Check if values exist
                    if max(columns) != 99999:
                        # Save value
                        windDirection_array.append(columns[[0, 1]])
                        windSpeed_array.append(columns[[0, 2]])
        windSpeed_array = np.array(windSpeed_array)
        windDirection_array = np.array(windDirection_array)

        # Converts 10*hPa to Pa and save values
        pressure_array[:, 1] = 10 * pressure_array[:, 1]
        self.pressure = Function(
            pressure_array,
            inputs="Height Above Sea Level (m)",
            outputs="Pressure (Pa)",
            interpolation="linear",
        )

        # Convert 10*C to K and save values
        temperature_array[:, 1] = (
            temperature_array[:, 1] / 10 + 273.15
        )  # Converts C to K
        self.temperature = Function(
            temperature_array,
            inputs="Height Above Sea Level (m)",
            outputs="Temperature (K)",
            interpolation="linear",
        )

        # Process wind-u and wind-v
        windSpeed_array[:, 1] = (
            windSpeed_array[:, 1] * 1.852 / 3.6
        )  # Converts Knots to m/s
        windHeading_array = windDirection_array[:, :] * 1
        windHeading_array[:, 1] = (
            windDirection_array[:, 1] + 180
        ) % 360  # Convert wind direction to wind heading
        windU = windSpeed_array[:, :] * 1
        windV = windSpeed_array[:, :] * 1
        windU[:, 1] = windSpeed_array[:, 1] * np.sin(
            windHeading_array[:, 1] * np.pi / 180
        )
        windV[:, 1] = windSpeed_array[:, 1] * np.cos(
            windHeading_array[:, 1] * np.pi / 180
        )

        # Save wind data
        self.windDirection = Function(
            windDirection_array,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Direction (Deg True)",
            interpolation="linear",
        )
        self.windHeading = Function(
            windHeading_array,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Heading (Deg True)",
            interpolation="linear",
        )
        self.windSpeed = Function(
            windSpeed_array,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Speed (m/s)",
            interpolation="linear",
        )
        self.windVelocityX = Function(
            windU,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity X (m/s)",
            interpolation="linear",
        )
        self.windVelocityY = Function(
            windV,
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity Y (m/s)",
            interpolation="linear",
        )

        # Save maximum expected height
        self.maxExpectedHeight = pressure_array[-1, 0]

    @requires_netCDF4
    def processForecastReanalysis(self, file, dictionary):
        """Import and process atmospheric data from weather forecasts
        and reanalysis given as netCDF or OPeNDAP files.
        Sets pressure, temperature, wind-u and wind-v
        profiles and surface elevation obtained from a weather
        file in netCDF format or from an OPeNDAP URL, both
        given through the file parameter. The date and location of the launch
        should already have been set through the date and
        location parameters when initializing the Environment.
        The netCDF and OPeNDAP datasets must contain at least
        geopotential height or geopotential, temperature,
        wind-u and wind-v profiles as a function of pressure levels.
        If surface geopotential or geopotential height is given,
        elevation is also set. Otherwise, elevation is not changed.
        Profiles are interpolated bi-linearly using supplied
        latitude and longitude. The date used is the nearest one
        to the date supplied. Furthermore, a dictionary must be
        supplied through the dictionary parameter in order for the
        dataset to be accurately read. Lastly, the dataset must use
        a rectangular grid sorted in either ascending or descending
        order of latitude and longitude.

        Parameters
        ----------
        file : string
            String containing path to local netCDF file or URL of an
            OPeNDAP file, such as NOAA's NOMAD or UCAR TRHEDDS server.
        dictionary : dictionary
            Specifies the dictionary to be used when reading netCDF and
            OPeNDAP files, allowing for the correct retrieval of data.
            The dictionary structure should specify the short names
            used for time, latitude, longitude, pressure levels,
            temperature profile, geopotential or geopotential height
            profile, wind-u and wind-v profiles in the dataset given in
            the file parameter. An example is the following dictionary,
            generally used to read OPeNDAP files from NOAA's NOMAD
            server:               {'time': 'time',
                               'latitude': 'lat',
                              'longitude': 'lon',
                                  'level': 'lev',
                            'temperature': 'tmpprs',
            'surface_geopotential_height': 'hgtsfc',
                    'geopotential_height': 'hgtprs',
                           'geopotential': None,
                                 'u_wind': 'ugrdprs',
                                 'v_wind': 'vgrdprs'}

        Returns
        -------
        None
        """
        # Check if date, lat and lon are known
        if self.datetime_date is None:
            raise TypeError(
                "Please specify Date (array-like) when "
                "initializing this Environment. "
                "Alternatively, use the Environment.setDate"
                " method."
            )
        if self.latitude is None:
            raise TypeError(
                "Please specify Location (lat, lon). when "
                "initializing this Environment. "
                "Alternatively, use the Environment."
                "setLocation method."
            )

        # Read weather file
        weatherData = netCDF4.Dataset(file)

        # Get time, latitude and longitude data from file
        timeArray = weatherData.variables[dictionary["time"]]
        lonArray = weatherData.variables[dictionary["longitude"]][:].tolist()
        latArray = weatherData.variables[dictionary["latitude"]][:].tolist()

        # Find time index
        timeIndex = netCDF4.date2index(
            self.datetime_date, timeArray, calendar="gregorian", select="nearest"
        )
        # Convert times do dates and numbers
        inputTimeNum = netCDF4.date2num(
            self.datetime_date, timeArray.units, calendar="gregorian"
        )
        fileTimeNum = timeArray[timeIndex]
        fileTimeDate = netCDF4.num2date(
            timeArray[timeIndex], timeArray.units, calendar="gregorian"
        )
        # Check if time is inside range supplied by file
        if timeIndex == 0 and inputTimeNum < fileTimeNum:
            raise ValueError(
                "Chosen launch time is not available in the provided file, which starts at {:}.".format(
                    fileTimeDate
                )
            )
        elif timeIndex == len(timeArray) - 1 and inputTimeNum > fileTimeNum:
            raise ValueError(
                "Chosen launch time is not available in the provided file, which ends at {:}.".format(
                    fileTimeDate
                )
            )
        # Check if time is exactly equal to one in the file
        if inputTimeNum != fileTimeNum:
            warnings.warn(
                "Exact chosen launch time is not available in the provided file, using {:} UTC instead.".format(
                    fileTimeDate
                )
            )

        # Find longitude index
        # Determine if file uses -180 to 180 or 0 to 360
        if lonArray[0] < 0 or lonArray[-1] < 0:
            # Convert input to -180 - 180
            lon = (
                self.longitude if self.longitude < 180 else -180 + self.longitude % 180
            )
        else:
            # Convert input to 0 - 360
            lon = self.longitude % 360
        # Check if reversed or sorted
        if lonArray[0] < lonArray[-1]:
            # Deal with sorted lonArray
            lonIndex = bisect.bisect(lonArray, lon)
        else:
            # Deal with reversed lonArray
            lonArray.reverse()
            lonIndex = len(lonArray) - bisect.bisect_left(lonArray, lon)
            lonArray.reverse()
        # Take care of longitude value equal to maximum longitude in the grid
        if lonIndex == len(lonArray) and lonArray[lonIndex - 1] == lon:
            lonIndex = lonIndex - 1
        # Check if longitude value is inside the grid
        if lonIndex == 0 or lonIndex == len(lonArray):
            raise ValueError(
                "Longitude {:f} not inside region covered by file, which is from {:f} to {:f}.".format(
                    lon, lonArray[0], lonArray[-1]
                )
            )

        # Find latitude index
        # Check if reversed or sorted
        if latArray[0] < latArray[-1]:
            # Deal with sorted latArray
            latIndex = bisect.bisect(latArray, self.latitude)
        else:
            # Deal with reversed latArray
            latArray.reverse()
            latIndex = len(latArray) - bisect.bisect_left(latArray, self.latitude)
            latArray.reverse()
        # Take care of latitude value equal to maximum longitude in the grid
        if latIndex == len(latArray) and latArray[latIndex - 1] == self.latitude:
            latIndex = latIndex - 1
        # Check if latitude value is inside the grid
        if latIndex == 0 or latIndex == len(latArray):
            raise ValueError(
                "Latitude {:f} not inside region covered by file, which is from {:f} to {:f}.".format(
                    self.latitude, latArray[0], latArray[-1]
                )
            )

        # Get pressure level data from file
        try:
            levels = (
                100 * weatherData.variables[dictionary["level"]][:]
            )  # Convert mbar to Pa
        except:
            raise ValueError(
                "Unable to read pressure levels from file. Check file and dictionary."
            )

        # Get geopotential data from file
        try:
            geopotentials = weatherData.variables[dictionary["geopotential_height"]][
                timeIndex, :, (latIndex - 1, latIndex), (lonIndex - 1, lonIndex)
            ]
        except:
            try:
                geopotentials = (
                    weatherData.variables[dictionary["geopotential"]][
                        timeIndex, :, (latIndex - 1, latIndex), (lonIndex - 1, lonIndex)
                    ]
                    / self.standard_g
                )
            except:
                raise ValueError(
                    "Unable to read geopotential height"
                    " nor geopotential from file. At least"
                    " one of them is necessary. Check "
                    " file and dictionary."
                )

        # Get temperature from file
        try:
            temperatures = weatherData.variables[dictionary["temperature"]][
                timeIndex, :, (latIndex - 1, latIndex), (lonIndex - 1, lonIndex)
            ]
        except:
            raise ValueError(
                "Unable to read temperature from file. Check file and dictionary."
            )

        # Get wind data from file
        try:
            windUs = weatherData.variables[dictionary["u_wind"]][
                timeIndex, :, (latIndex - 1, latIndex), (lonIndex - 1, lonIndex)
            ]
        except:
            raise ValueError(
                "Unable to read wind-u component. Check file and dictionary."
            )
        try:
            windVs = weatherData.variables[dictionary["v_wind"]][
                timeIndex, :, (latIndex - 1, latIndex), (lonIndex - 1, lonIndex)
            ]
        except:
            raise ValueError(
                "Unable to read wind-v component. Check file and dictionary."
            )

        # Prepare for bilinear interpolation
        x, y = self.latitude, lon
        x1, y1 = latArray[latIndex - 1], lonArray[lonIndex - 1]
        x2, y2 = latArray[latIndex], lonArray[lonIndex]

        # Determine geopotential in lat, lon
        f_x1_y1 = geopotentials[:, 0, 0]
        f_x1_y2 = geopotentials[:, 0, 1]
        f_x2_y1 = geopotentials[:, 1, 0]
        f_x2_y2 = geopotentials[:, 1, 1]
        f_x_y1 = ((x2 - x) / (x2 - x1)) * f_x1_y1 + ((x - x1) / (x2 - x1)) * f_x2_y1
        f_x_y2 = ((x2 - x) / (x2 - x1)) * f_x1_y2 + ((x - x1) / (x2 - x1)) * f_x2_y2
        height = ((y2 - y) / (y2 - y1)) * f_x_y1 + ((y - y1) / (y2 - y1)) * f_x_y2

        # Determine temperature in lat, lon
        f_x1_y1 = temperatures[:, 0, 0]
        f_x1_y2 = temperatures[:, 0, 1]
        f_x2_y1 = temperatures[:, 1, 0]
        f_x2_y2 = temperatures[:, 1, 1]
        f_x_y1 = ((x2 - x) / (x2 - x1)) * f_x1_y1 + ((x - x1) / (x2 - x1)) * f_x2_y1
        f_x_y2 = ((x2 - x) / (x2 - x1)) * f_x1_y2 + ((x - x1) / (x2 - x1)) * f_x2_y2
        temperature = ((y2 - y) / (y2 - y1)) * f_x_y1 + ((y - y1) / (y2 - y1)) * f_x_y2

        # Determine wind u in lat, lon
        f_x1_y1 = windUs[:, 0, 0]
        f_x1_y2 = windUs[:, 0, 1]
        f_x2_y1 = windUs[:, 1, 0]
        f_x2_y2 = windUs[:, 1, 1]
        f_x_y1 = ((x2 - x) / (x2 - x1)) * f_x1_y1 + ((x - x1) / (x2 - x1)) * f_x2_y1
        f_x_y2 = ((x2 - x) / (x2 - x1)) * f_x1_y2 + ((x - x1) / (x2 - x1)) * f_x2_y2
        windU = ((y2 - y) / (y2 - y1)) * f_x_y1 + ((y - y1) / (y2 - y1)) * f_x_y2

        # Determine wind v in lat, lon
        f_x1_y1 = windVs[:, 0, 0]
        f_x1_y2 = windVs[:, 0, 1]
        f_x2_y1 = windVs[:, 1, 0]
        f_x2_y2 = windVs[:, 1, 1]
        f_x_y1 = ((x2 - x) / (x2 - x1)) * f_x1_y1 + ((x - x1) / (x2 - x1)) * f_x2_y1
        f_x_y2 = ((x2 - x) / (x2 - x1)) * f_x1_y2 + ((x - x1) / (x2 - x1)) * f_x2_y2
        windV = ((y2 - y) / (y2 - y1)) * f_x_y1 + ((y - y1) / (y2 - y1)) * f_x_y2

        # Determine wind speed, heading and direction
        windSpeed = np.sqrt(windU**2 + windV**2)
        windHeading = np.arctan2(windU, windV) * (180 / np.pi) % 360
        windDirection = (windHeading - 180) % 360

        # Convert geopotential height to geometric height
        R = self.earthRadius
        height = R * height / (R - height)

        # Combine all data into big array
        data_array = np.ma.column_stack(
            [
                levels,
                height,
                temperature,
                windU,
                windV,
                windHeading,
                windDirection,
                windSpeed,
            ]
        )

        # Remove lines with masked content
        if np.any(data_array.mask):
            data_array = np.ma.compress_rows(data_array)
            warnings.warn(
                "Some values were missing from this weather dataset, therefore, certain pressure levels were removed."
            )
        # Save atmospheric data
        self.pressure = Function(
            data_array[:, (1, 0)],
            inputs="Height Above Sea Level (m)",
            outputs="Pressure (Pa)",
            interpolation="linear",
        )
        self.temperature = Function(
            data_array[:, (1, 2)],
            inputs="Height Above Sea Level (m)",
            outputs="Temperature (K)",
            interpolation="linear",
        )
        self.windDirection = Function(
            data_array[:, (1, 6)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Direction (Deg True)",
            interpolation="linear",
        )
        self.windHeading = Function(
            data_array[:, (1, 5)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Heading (Deg True)",
            interpolation="linear",
        )
        self.windSpeed = Function(
            data_array[:, (1, 7)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Speed (m/s)",
            interpolation="linear",
        )
        self.windVelocityX = Function(
            data_array[:, (1, 3)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity X (m/s)",
            interpolation="linear",
        )
        self.windVelocityY = Function(
            data_array[:, (1, 4)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity Y (m/s)",
            interpolation="linear",
        )

        # Save maximum expected height
        self.maxExpectedHeight = max(height[0], height[-1])

        # Get elevation data from file
        if dictionary["surface_geopotential_height"] is not None:
            try:
                elevations = weatherData.variables[
                    dictionary["surface_geopotential_height"]
                ][timeIndex, (latIndex - 1, latIndex), (lonIndex - 1, lonIndex)]
                f_x1_y1 = elevations[0, 0]
                f_x1_y2 = elevations[0, 1]
                f_x2_y1 = elevations[1, 0]
                f_x2_y2 = elevations[1, 1]
                f_x_y1 = ((x2 - x) / (x2 - x1)) * f_x1_y1 + (
                    (x - x1) / (x2 - x1)
                ) * f_x2_y1
                f_x_y2 = ((x2 - x) / (x2 - x1)) * f_x1_y2 + (
                    (x - x1) / (x2 - x1)
                ) * f_x2_y2
                self.elevation = ((y2 - y) / (y2 - y1)) * f_x_y1 + (
                    (y - y1) / (y2 - y1)
                ) * f_x_y2
            except:
                raise ValueError(
                    "Unable to read surface elevation data. Check file and dictionary."
                )

        # Compute info data
        self.atmosphericModelInitDate = netCDF4.num2date(
            timeArray[0], timeArray.units, calendar="gregorian"
        )
        self.atmosphericModelEndDate = netCDF4.num2date(
            timeArray[-1], timeArray.units, calendar="gregorian"
        )
        self.atmosphericModelInterval = netCDF4.num2date(
            (timeArray[-1] - timeArray[0]) / (len(timeArray) - 1),
            timeArray.units,
            calendar="gregorian",
        ).hour
        self.atmosphericModelInitLat = latArray[0]
        self.atmosphericModelEndLat = latArray[-1]
        self.atmosphericModelInitLon = lonArray[0]
        self.atmosphericModelEndLon = lonArray[-1]

        # Save debugging data
        self.latArray = latArray
        self.lonArray = lonArray
        self.lonIndex = lonIndex
        self.latIndex = latIndex
        self.geopotentials = geopotentials
        self.windUs = windUs
        self.windVs = windVs
        self.levels = levels
        self.temperatures = temperatures
        self.timeArray = timeArray
        self.height = height

        # Close weather data
        weatherData.close()

        return None

    @requires_netCDF4
    def processEnsemble(self, file, dictionary):
        """Import and process atmospheric data from weather ensembles
        given as netCDF or OPeNDAP files.
        Sets pressure, temperature, wind-u and wind-v
        profiles and surface elevation obtained from a weather
        ensemble file in netCDF format or from an OPeNDAP URL, both
        given through the file parameter. The date and location of the launch
        should already have been set through the date and
        location parameters when initializing the Environment.
        The netCDF and OPeNDAP datasets must contain at least
        geopotential height or geopotential, temperature,
        wind-u and wind-v profiles as a function of pressure
        levels. If surface geopotential or geopotential height
        is given, elevation is also set. Otherwise, elevation is not
        changed. Profiles are interpolated bi-linearly using supplied
        latitude and longitude. The date used is the nearest one
        to the date supplied. Furthermore, a dictionary must be
        supplied through the dictionary parameter in order for the
        dataset to be accurately read. Lastly, the dataset must use
        a rectangular grid sorted in either ascending or descending
        order of latitude and longitude. By default the first ensemble
        forecast is activated. To activate other ensemble forecasts
        see Environment.selectEnsembleMemberMember().

        Parameters
        ----------
        file : string
            String containing path to local netCDF file or URL of an
            OPeNDAP file, such as NOAA's NOMAD or UCAR TRHEDDS server.
        dictionary : dictionary
            Specifies the dictionary to be used when reading netCDF and
            OPeNDAP files, allowing for the correct retrieval of data.
            The dictionary structure should specify the short names
            used for time, latitude, longitude, pressure levels,
            temperature profile, geopotential or geopotential height
            profile, wind-u and wind-v profiles in the dataset given in
            the file parameter. An example is the following dictionary,
            generally used to read OPeNDAP files from NOAA's NOMAD
            server:               {'time': 'time',
                               'latitude': 'lat',
                              'longitude': 'lon',
                                  'level': 'lev',
                               'ensemble': 'ens',
            'surface_geopotential_height': 'hgtsfc',
                    'geopotential_height': 'hgtprs',
                           'geopotential': None,
                                 'u_wind': 'ugrdprs',
                                 'v_wind': 'vgrdprs'}

        Returns
        -------
        None
        """
        # Check if date, lat and lon are known
        if self.datetime_date is None:
            raise TypeError(
                "Please specify Date (array-like) when "
                "initializing this Environment. "
                "Alternatively, use the Environment.setDate"
                " method."
            )
        if self.latitude is None:
            raise TypeError(
                "Please specify Location (lat, lon). when "
                "initializing this Environment. "
                "Alternatively, use the Environment."
                "setLocation method."
            )

        # Read weather file
        weatherData = netCDF4.Dataset(file)

        # Get time, latitude and longitude data from file
        timeArray = weatherData.variables[dictionary["time"]]
        lonArray = weatherData.variables[dictionary["longitude"]][:].tolist()
        latArray = weatherData.variables[dictionary["latitude"]][:].tolist()

        # Find time index
        timeIndex = netCDF4.date2index(
            self.datetime_date, timeArray, calendar="gregorian", select="nearest"
        )
        # Convert times do dates and numbers
        inputTimeNum = netCDF4.date2num(
            self.datetime_date, timeArray.units, calendar="gregorian"
        )
        fileTimeNum = timeArray[timeIndex]
        fileTimeDate = netCDF4.num2date(
            timeArray[timeIndex], timeArray.units, calendar="gregorian"
        )
        # Check if time is inside range supplied by file
        if timeIndex == 0 and inputTimeNum < fileTimeNum:
            raise ValueError(
                "Chosen launch time is not available in the provided file, which starts at {:}.".format(
                    fileTimeDate
                )
            )
        elif timeIndex == len(timeArray) - 1 and inputTimeNum > fileTimeNum:
            raise ValueError(
                "Chosen launch time is not available in the provided file, which ends at {:}.".format(
                    fileTimeDate
                )
            )
        # Check if time is exactly equal to one in the file
        if inputTimeNum != fileTimeNum:
            warnings.warn(
                "Exact chosen launch time is not available in the provided file, using {:} UTC instead.".format(
                    fileTimeDate
                )
            )

        # Find longitude index
        # Determine if file uses -180 to 180 or 0 to 360
        if lonArray[0] < 0 or lonArray[-1] < 0:
            # Convert input to -180 - 180
            lon = (
                self.longitude if self.longitude < 180 else -180 + self.longitude % 180
            )
        else:
            # Convert input to 0 - 360
            lon = self.longitude % 360
        # Check if reversed or sorted
        if lonArray[0] < lonArray[-1]:
            # Deal with sorted lonArray
            lonIndex = bisect.bisect(lonArray, lon)
        else:
            # Deal with reversed lonArray
            lonArray.reverse()
            lonIndex = len(lonArray) - bisect.bisect_left(lonArray, lon)
            lonArray.reverse()
        # Take care of longitude value equal to maximum longitude in the grid
        if lonIndex == len(lonArray) and lonArray[lonIndex - 1] == lon:
            lonIndex = lonIndex - 1
        # Check if longitude value is inside the grid
        if lonIndex == 0 or lonIndex == len(lonArray):
            raise ValueError(
                "Longitude {:f} not inside region covered by file, which is from {:f} to {:f}.".format(
                    lon, lonArray[0], lonArray[-1]
                )
            )

        # Find latitude index
        # Check if reversed or sorted
        if latArray[0] < latArray[-1]:
            # Deal with sorted latArray
            latIndex = bisect.bisect(latArray, self.latitude)
        else:
            # Deal with reversed latArray
            latArray.reverse()
            latIndex = len(latArray) - bisect.bisect_left(latArray, self.latitude)
            latArray.reverse()
        # Take care of latitude value equal to maximum longitude in the grid
        if latIndex == len(latArray) and latArray[latIndex - 1] == self.latitude:
            latIndex = latIndex - 1
        # Check if latitude value is inside the grid
        if latIndex == 0 or latIndex == len(latArray):
            raise ValueError(
                "Latitude {:f} not inside region covered by file, which is from {:f} to {:f}.".format(
                    self.latitude, latArray[0], latArray[-1]
                )
            )

        # Get ensemble data from file
        try:
            numMembers = len(weatherData.variables[dictionary["ensemble"]][:])
        except:
            raise ValueError(
                "Unable to read ensemble data from file. Check file and dictionary."
            )

        # Get pressure level data from file
        try:
            levels = (
                100 * weatherData.variables[dictionary["level"]][:]
            )  # Convert mbar to Pa
        except:
            raise ValueError(
                "Unable to read pressure levels from file. Check file and dictionary."
            )

        ##
        inverseDictionary = {v: k for k, v in dictionary.items()}
        paramDictionary = {
            "time": timeIndex,
            "ensemble": range(numMembers),
            "level": range(len(levels)),
            "latitude": (latIndex - 1, latIndex),
            "longitude": (lonIndex - 1, lonIndex),
        }
        ##

        # Get geopotential data from file
        try:
            dimensions = weatherData.variables[
                dictionary["geopotential_height"]
            ].dimensions[:]
            params = tuple(
                [paramDictionary[inverseDictionary[dim]] for dim in dimensions]
            )
            geopotentials = weatherData.variables[dictionary["geopotential_height"]][
                params
            ]
        except:
            try:
                dimensions = weatherData.variables[
                    dictionary["geopotential"]
                ].dimensions[:]
                params = tuple(
                    [paramDictionary[inverseDictionary[dim]] for dim in dimensions]
                )
                geopotentials = (
                    weatherData.variables[dictionary["geopotential"]][params]
                    / self.standard_g
                )
            except:
                raise ValueError(
                    "Unable to read geopotential height"
                    " nor geopotential from file. At least"
                    " one of them is necessary. Check "
                    " file and dictionary."
                )

        # Get temperature from file
        try:
            temperatures = weatherData.variables[dictionary["temperature"]][params]
        except:
            raise ValueError(
                "Unable to read temperature from file. Check file and dictionary."
            )

        # Get wind data from file
        try:
            windUs = weatherData.variables[dictionary["u_wind"]][params]
        except:
            raise ValueError(
                "Unable to read wind-u component. Check file and dictionary."
            )
        try:
            windVs = weatherData.variables[dictionary["v_wind"]][params]
        except:
            raise ValueError(
                "Unable to read wind-v component. Check file and dictionary."
            )

        # Prepare for bilinear interpolation
        x, y = self.latitude, lon
        x1, y1 = latArray[latIndex - 1], lonArray[lonIndex - 1]
        x2, y2 = latArray[latIndex], lonArray[lonIndex]

        # Determine geopotential in lat, lon
        f_x1_y1 = geopotentials[:, :, 0, 0]
        f_x1_y2 = geopotentials[:, :, 0, 1]
        f_x2_y1 = geopotentials[:, :, 1, 0]
        f_x2_y2 = geopotentials[:, :, 1, 1]
        f_x_y1 = ((x2 - x) / (x2 - x1)) * f_x1_y1 + ((x - x1) / (x2 - x1)) * f_x2_y1
        f_x_y2 = ((x2 - x) / (x2 - x1)) * f_x1_y2 + ((x - x1) / (x2 - x1)) * f_x2_y2
        height = ((y2 - y) / (y2 - y1)) * f_x_y1 + ((y - y1) / (y2 - y1)) * f_x_y2

        # Determine temperature in lat, lon
        f_x1_y1 = temperatures[:, :, 0, 0]
        f_x1_y2 = temperatures[:, :, 0, 1]
        f_x2_y1 = temperatures[:, :, 1, 0]
        f_x2_y2 = temperatures[:, :, 1, 1]
        f_x_y1 = ((x2 - x) / (x2 - x1)) * f_x1_y1 + ((x - x1) / (x2 - x1)) * f_x2_y1
        f_x_y2 = ((x2 - x) / (x2 - x1)) * f_x1_y2 + ((x - x1) / (x2 - x1)) * f_x2_y2
        temperature = ((y2 - y) / (y2 - y1)) * f_x_y1 + ((y - y1) / (y2 - y1)) * f_x_y2

        # Determine wind u in lat, lon
        f_x1_y1 = windUs[:, :, 0, 0]
        f_x1_y2 = windUs[:, :, 0, 1]
        f_x2_y1 = windUs[:, :, 1, 0]
        f_x2_y2 = windUs[:, :, 1, 1]
        f_x_y1 = ((x2 - x) / (x2 - x1)) * f_x1_y1 + ((x - x1) / (x2 - x1)) * f_x2_y1
        f_x_y2 = ((x2 - x) / (x2 - x1)) * f_x1_y2 + ((x - x1) / (x2 - x1)) * f_x2_y2
        windU = ((y2 - y) / (y2 - y1)) * f_x_y1 + ((y - y1) / (y2 - y1)) * f_x_y2

        # Determine wind v in lat, lon
        f_x1_y1 = windVs[:, :, 0, 0]
        f_x1_y2 = windVs[:, :, 0, 1]
        f_x2_y1 = windVs[:, :, 1, 0]
        f_x2_y2 = windVs[:, :, 1, 1]
        f_x_y1 = ((x2 - x) / (x2 - x1)) * f_x1_y1 + ((x - x1) / (x2 - x1)) * f_x2_y1
        f_x_y2 = ((x2 - x) / (x2 - x1)) * f_x1_y2 + ((x - x1) / (x2 - x1)) * f_x2_y2
        windV = ((y2 - y) / (y2 - y1)) * f_x_y1 + ((y - y1) / (y2 - y1)) * f_x_y2

        # Determine wind speed, heading and direction
        windSpeed = np.sqrt(windU**2 + windV**2)
        windHeading = np.arctan2(windU, windV) * (180 / np.pi) % 360
        windDirection = (windHeading - 180) % 360

        # Convert geopotential height to geometric height
        R = self.earthRadius
        height = R * height / (R - height)

        # Save ensemble data
        self.levelEnsemble = levels
        self.heightEnsemble = height
        self.temperatureEnsemble = temperature
        self.windUEnsemble = windU
        self.windVEnsemble = windV
        self.windHeadingEnsemble = windHeading
        self.windDirectionEnsemble = windDirection
        self.windSpeedEnsemble = windSpeed
        self.numEnsembleMembers = numMembers

        # Activate default ensemble
        self.selectEnsembleMember()

        # Get elevation data from file
        if dictionary["surface_geopotential_height"] is not None:
            try:
                elevations = weatherData.variables[
                    dictionary["surface_geopotential_height"]
                ][timeIndex, (latIndex - 1, latIndex), (lonIndex - 1, lonIndex)]
                f_x1_y1 = elevations[0, 0]
                f_x1_y2 = elevations[0, 1]
                f_x2_y1 = elevations[1, 0]
                f_x2_y2 = elevations[1, 1]
                f_x_y1 = ((x2 - x) / (x2 - x1)) * f_x1_y1 + (
                    (x - x1) / (x2 - x1)
                ) * f_x2_y1
                f_x_y2 = ((x2 - x) / (x2 - x1)) * f_x1_y2 + (
                    (x - x1) / (x2 - x1)
                ) * f_x2_y2
                self.elevation = ((y2 - y) / (y2 - y1)) * f_x_y1 + (
                    (y - y1) / (y2 - y1)
                ) * f_x_y2
            except:
                raise ValueError(
                    "Unable to read surface elevation data. Check file and dictionary."
                )

        # Compute info data
        self.atmosphericModelInitDate = netCDF4.num2date(
            timeArray[0], timeArray.units, calendar="gregorian"
        )
        self.atmosphericModelEndDate = netCDF4.num2date(
            timeArray[-1], timeArray.units, calendar="gregorian"
        )
        self.atmosphericModelInterval = netCDF4.num2date(
            (timeArray[-1] - timeArray[0]) / (len(timeArray) - 1),
            timeArray.units,
            calendar="gregorian",
        ).hour
        self.atmosphericModelInitLat = latArray[0]
        self.atmosphericModelEndLat = latArray[-1]
        self.atmosphericModelInitLon = lonArray[0]
        self.atmosphericModelEndLon = lonArray[-1]

        # Save debugging data
        self.latArray = latArray
        self.lonArray = lonArray
        self.lonIndex = lonIndex
        self.latIndex = latIndex
        self.geopotentials = geopotentials
        self.windUs = windUs
        self.windVs = windVs
        self.levels = levels
        self.temperatures = temperatures
        self.timeArray = timeArray
        self.height = height

        # Close weather data
        weatherData.close()

        return None

    def selectEnsembleMember(self, member=0):
        """Activates ensemble member, meaning that all atmospheric
        variables read from the Environment instance will correspond
        to the desired ensemble member.

        Parameters
        ---------
        member : int
            Ensemble member to be activated. Starts from 0.

        Returns
        -------
        None
        """
        # Verify ensemble member
        if member >= self.numEnsembleMembers:
            raise ValueError(
                "Please choose member from 0 to {:d}".format(
                    self.numEnsembleMembers - 1
                )
            )

        # Read ensemble member
        levels = self.levelEnsemble[:]
        height = self.heightEnsemble[member, :]
        temperature = self.temperatureEnsemble[member, :]
        windU = self.windUEnsemble[member, :]
        windV = self.windVEnsemble[member, :]
        windHeading = self.windHeadingEnsemble[member, :]
        windDirection = self.windDirectionEnsemble[member, :]
        windSpeed = self.windSpeedEnsemble[member, :]

        # Combine all data into big array
        data_array = np.ma.column_stack(
            [
                levels,
                height,
                temperature,
                windU,
                windV,
                windHeading,
                windDirection,
                windSpeed,
            ]
        )

        # Remove lines with masked content
        if np.any(data_array.mask):
            data_array = np.ma.compress_rows(data_array)
            warnings.warn(
                "Some values were missing from this weather dataset, therefore, certain pressure levels were removed."
            )

        # Save atmospheric data
        self.pressure = Function(
            data_array[:, (1, 0)],
            inputs="Height Above Sea Level (m)",
            outputs="Pressure (Pa)",
            interpolation="linear",
        )
        self.temperature = Function(
            data_array[:, (1, 2)],
            inputs="Height Above Sea Level (m)",
            outputs="Temperature (K)",
            interpolation="linear",
        )
        self.windDirection = Function(
            data_array[:, (1, 6)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Direction (Deg True)",
            interpolation="linear",
        )
        self.windHeading = Function(
            data_array[:, (1, 5)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Heading (Deg True)",
            interpolation="linear",
        )
        self.windSpeed = Function(
            data_array[:, (1, 7)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Speed (m/s)",
            interpolation="linear",
        )
        self.windVelocityX = Function(
            data_array[:, (1, 3)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity X (m/s)",
            interpolation="linear",
        )
        self.windVelocityY = Function(
            data_array[:, (1, 4)],
            inputs="Height Above Sea Level (m)",
            outputs="Wind Velocity Y (m/s)",
            interpolation="linear",
        )

        # Save maximum expected height
        self.maxExpectedHeight = max(height[0], height[-1])

        # Save ensemble member
        self.ensembleMember = member

        # Update air density
        self.calculateDensityProfile()

        # Update speed of sound
        self.calculateSpeedOfSoundProfile()

        # Update dynamic viscosity
        self.calculateDynamicViscosity()

        return None

    def loadInternationalStandardAtmosphere(self):
        """Defines the pressure and temperature profile functions set
        by ISO 2533 for the International Standard atmosphere and saves
        them as self.pressureISA and self.temperatureISA.

        Parameters
        ---------
        None

        Returns
        -------
        None
        """
        # Define international standard atmosphere layers
        geopotential_height = [
            -2e3,
            0,
            11e3,
            20e3,
            32e3,
            47e3,
            51e3,
            71e3,
            80e3,
        ]  # in geopotential m
        temperature = [
            301.15,
            288.15,
            216.65,
            216.65,
            228.65,
            270.65,
            270.65,
            214.65,
            196.65,
        ]  # in K
        beta = [
            -6.5e-3,
            -6.5e-3,
            0,
            1e-3,
            2.8e-3,
            0,
            -2.8e-3,
            -2e-3,
            0,
        ]  # Temperature gradient in K/m
        pressure = [
            1.27774e5,
            1.01325e5,
            2.26320e4,
            5.47487e3,
            8.680164e2,
            1.10906e2,
            6.69384e1,
            3.95639e0,
            8.86272e-2,
        ]  # in Pa

        # Convert geopotential height to geometric height
        ER = self.earthRadius
        height = [ER * H / (ER - H) for H in geopotential_height]

        # Save international standard atmosphere temperature profile
        self.temperatureISA = Function(
            np.column_stack([height, temperature]),
            inputs="Height Above Sea Level (m)",
            outputs="Temperature (K)",
            interpolation="linear",
        )

        # Get gravity and R
        g = self.standard_g
        R = self.airGasConstant

        # Create function to compute pressure at a given geometric height
        def pressure_function(h):
            # Convert geometric to geopotential height
            H = ER * h / (ER + h)

            # Check if height is within bounds, return extrapolated value if not
            if H < -2000:
                return pressure[0]
            elif H > 80000:
                return pressure[-1]

            # Find layer that contains height h
            layer = bisect.bisect(geopotential_height, H) - 1

            # Retrieve layer base geopotential height, temp, beta and pressure
            Hb = geopotential_height[layer]
            Tb = temperature[layer]
            Pb = pressure[layer]
            B = beta[layer]

            # Compute pressure
            if B != 0:
                P = Pb * (1 + (B / Tb) * (H - Hb)) ** (-g / (B * R))
            else:
                T = Tb + B * (H - Hb)
                P = Pb * np.exp(-(H - Hb) * (g / (R * T)))

            # Return answer
            return P

        # Save international standard atmosphere pressure profile
        self.pressureISA = Function(
            pressure_function,
            inputs="Height Above Sea Level (m)",
            outputs="Pressure (Pa)",
        )

        return None

    def calculateDensityProfile(self):
        """Compute the density of the atmosphere as a function of
        height by using the formula rho = P/(RT). This function is
        automatically called whenever a new atmospheric model is set.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        # Retrieve pressure P, gas constant R and temperature T
        P = self.pressure
        R = self.airGasConstant
        T = self.temperature

        # Compute density using P/RT
        D = P / (R * T)

        # Set new output for the calculated density
        D.setOutputs("Air Density (kg/m³)")

        # Save calculated density
        self.density = D

        return None

    def calculateSpeedOfSoundProfile(self):
        """Compute the speed of sound in the atmosphere as a function
        of height by using the formula a = sqrt(gamma*R*T). This
        function is automatically called whenever a new atmospheric
        model is set.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        # Retrieve gas constant R and temperature T
        R = self.airGasConstant
        T = self.temperature
        G = 1.4

        # Compute speed of sound using sqrt(gamma*R*T)
        a = (G * R * T) ** 0.5

        # Set new output for the calculated speed of sound
        a.setOutputs("Speed of Sound (m/s)")

        # Save calculated speed of sound
        self.speedOfSound = a

        return None

    def calculateDynamicViscosity(self):
        """Compute the dynamic viscosity of the atmosphere as a function of
        height by using the formula given in ISO 2533 u = B*T^(1.5)/(T+S).
        This function is automatically called whenever a new atmospheric model is set.
        Warning: This equation is invalid for very high or very low temperatures
        and under conditions occurring at altitudes above 90 km.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        # Retrieve temperature T and set constants
        T = self.temperature
        B = 1.458e-6  # Kg/m/s/K^0.5
        S = 110.4  # K

        # Compute dynamic viscosity using u = B*T^(1.4)/(T+S) (See ISO2533)
        u = (B * T ** (1.5)) / (T + S)

        # Set new output for the calculated density
        u.setOutputs("Dynamic Viscosity (Pa s)")

        # Save calculated density
        self.dynamicViscosity = u

        return None

    def addWindGust(self, windGustX, windGustY):
        """Adds a function to the current stored wind profile, in order to
        simulate a wind gust.

        Parameters
        ----------
        windGustX : float, callable
            Callable, function of altitude, which will be added to the
            x velocity of the current stored wind profile. If float is given,
            it will be considered as a constant function in altitude.
        windGustY : float, callable
            Callable, function of altitude, which will be added to the
            y velocity of the current stored wind profile. If float is given,
            it will be considered as a constant function in altitude.

        Returns
        -------
        None
        """
        # Recalculate windVelocityX and windVelocityY
        self.windVelocityX = self.windVelocityX + windGustX
        self.windVelocityY = self.windVelocityY + windGustY

        # Reset windVelocityX and windVelocityY details
        self.windVelocityX.setInputs("Height (m)")
        self.windVelocityX.setOutputs("Wind Velocity X (m/s)")
        self.windVelocityY.setInputs("Height (m)")
        self.windVelocityY.setOutputs("Wind Velocity Y (m/s)")

        # Reset wind heading and velocity magnitude
        self.windHeading = Function(
            lambda h: (180 / np.pi)
            * np.arctan2(self.windVelocityX(h), self.windVelocityY(h))
            % 360,
            "Height (m)",
            "Wind Heading (degrees)",
            extrapolation="constant",
        )
        self.windSpeed = Function(
            lambda h: (self.windVelocityX(h) ** 2 + self.windVelocityY(h) ** 2) ** 0.5,
            "Height (m)",
            "Wind Speed (m/s)",
            extrapolation="constant",
        )

        return None

    def info(self):
        """Prints most important data and graphs available about the
        Environment.

        Parameters
        ----------
        None

        Return
        ------
        None
        """

        self.prints.all()
        self.plots.info()
        return None

    def allInfo(self):
        """Prints out all data and graphs available about the Environment.

        Parameters
        ----------
        None

        Return
        ------
        None
        """

        self.prints.all()
        self.plots.all()

        return None

    def allPlotInfoReturned(self) -> dict:
        """Returns a dictionary with all plot information available about the Environment.

        Parameters
        ----------
        None

        Returns
        ------
        plotInfo : Dict
            Dict of data relevant to plot externally
        """
        grid = np.linspace(self.elevation, self.maxExpectedHeight)
        plotInfo = dict(
            grid=[i for i in grid],
            windSpeed=[self.windSpeed(i) for i in grid],
            windDirection=[self.windDirection(i) for i in grid],
            speedOfSound=[self.speedOfSound(i) for i in grid],
            density=[self.density(i) for i in grid],
            windVelX=[self.windVelocityX(i) for i in grid],
            windVelY=[self.windVelocityY(i) for i in grid],
            pressure=[self.pressure(i) / 100 for i in grid],
            temperature=[self.temperature(i) for i in grid],
        )
        if self.atmosphericModelType != "Ensemble":
            return plotInfo
        currentMember = self.ensembleMember
        # List for each ensemble
        plotInfo["ensembleWindVelocityX"] = []
        for i in range(self.numEnsembleMembers):
            self.selectEnsembleMember(i)
            plotInfo["ensembleWindVelocityX"].append(
                [self.windVelocityX(i) for i in grid]
            )
        plotInfo["ensembleWindVelocityY"] = []
        for i in range(self.numEnsembleMembers):
            self.selectEnsembleMember(i)
            plotInfo["ensembleWindVelocityY"].append(
                [self.windVelocityY(i) for i in grid]
            )
        plotInfo["ensembleWindSpeed"] = []
        for i in range(self.numEnsembleMembers):
            self.selectEnsembleMember(i)
            plotInfo["ensembleWindSpeed"].append([self.windSpeed(i) for i in grid])
        plotInfo["ensembleWindDirection"] = []
        for i in range(self.numEnsembleMembers):
            self.selectEnsembleMember(i)
            plotInfo["ensembleWindDirection"].append(
                [self.windDirection(i) for i in grid]
            )
        plotInfo["ensemblePressure"] = []
        for i in range(self.numEnsembleMembers):
            self.selectEnsembleMember(i)
            plotInfo["ensemblePressure"].append([self.pressure(i) for i in grid])
        plotInfo["ensembleTemperature"] = []
        for i in range(self.numEnsembleMembers):
            self.selectEnsembleMember(i)
            plotInfo["ensembleTemperature"].append([self.temperature(i) for i in grid])

        # Clean up
        self.selectEnsembleMember(currentMember)
        return plotInfo

    def allInfoReturned(self):
        """Returns as dicts all data available about the Environment.

        Parameters
        ----------
        None

        Returns
        ------
        info: Dict
            Information relevant about the Environment class.
        """

        # Dictionary creation, if not commented follows the SI
        info = dict(
            grav=self.gravity,
            launch_rail_length=self.railLength,
            elevation=self.elevation,
            modelType=self.atmosphericModelType,
            modelTypeMaxExpectedHeight=self.maxExpectedHeight,
            windSpeed=self.windSpeed(self.elevation),
            windDirection=self.windDirection(self.elevation),
            windHeading=self.windHeading(self.elevation),
            surfacePressure=self.pressure(self.elevation) / 100,  # in hPa
            surfaceTemperature=self.temperature(self.elevation),
            surfaceAirDensity=self.density(self.elevation),
            surfaceSpeedOfSound=self.speedOfSound(self.elevation),
        )
        if self.datetime_date != None:
            info["launch_date"] = self.datetime_date.strftime("%Y-%d-%m %H:%M:%S")
        if self.latitude != None and self.longitude != None:
            info["lat"] = self.latitude
            info["lon"] = self.longitude
        if info["modelType"] in ["Forecast", "Reanalysis", "Ensemble"]:
            info["initDate"] = self.atmosphericModelInitDate.strftime(
                "%Y-%d-%m %H:%M:%S"
            )
            info["endDate"] = self.atmosphericModelEndDate.strftime("%Y-%d-%m %H:%M:%S")
            info["interval"] = self.atmosphericModelInterval
            info["initLat"] = self.atmosphericModelInitLat
            info["endLat"] = self.atmosphericModelEndLat
            info["initLon"] = self.atmosphericModelInitLon
            info["endLon"] = self.atmosphericModelEndLon
        if info["modelType"] == "Ensemble":
            info["numEnsembleMembers"] = self.numEnsembleMembers
            info["selectedEnsembleMember"] = self.ensembleMember
        return info

    def exportEnvironment(self, filename="environment"):
        """Export important attributes of Environment class to a .json file,
        saving all the information needed to recreate the same environment using
        customAtmosphere.

        Parameters
        ----------
        filename

        Return
        ------
        None
        """

        try:
            atmosphericModelFile = self.atmosphericModelFile
            atmosphericModelDict = self.atmosphericModelDict
        except AttributeError:
            atmosphericModelFile = ""
            atmosphericModelDict = ""

        self.exportEnvDictionary = {
            "railLength": self.railLength,
            "gravity": self.gravity(self.elevation),
            "date": [
                self.datetime_date.year,
                self.datetime_date.month,
                self.datetime_date.day,
                self.datetime_date.hour,
            ],
            "latitude": self.latitude,
            "longitude": self.longitude,
            "elevation": self.elevation,
            "datum": self.datum,
            "timeZone": self.timeZone,
            "maxExpectedHeight": float(self.maxExpectedHeight),
            "atmosphericModelType": self.atmosphericModelType,
            "atmosphericModelFile": atmosphericModelFile,
            "atmosphericModelDict": atmosphericModelDict,
            "atmosphericModelPressureProfile": ma.getdata(
                self.pressure.getSource()
            ).tolist(),
            "atmosphericModelTemperatureProfile": ma.getdata(
                self.temperature.getSource()
            ).tolist(),
            "atmosphericModelWindVelocityXProfile": ma.getdata(
                self.windVelocityX.getSource()
            ).tolist(),
            "atmosphericModelWindVelocityYProfile": ma.getdata(
                self.windVelocityY.getSource()
            ).tolist(),
        }

        f = open(filename + ".json", "w")

        # write json object to file
        f.write(
            json.dumps(self.exportEnvDictionary, sort_keys=False, indent=4, default=str)
        )

        # close file
        f.close()
        print("Your Environment file was saved, check it out: " + filename + ".json")
        print(
            "You can use it in the future by using the customAtmosphere atmospheric model."
        )

        return None

    def setEarthGeometry(self, datum):
        """Sets the Earth geometry for the Environment class based on the
        datum provided.

        Parameters
        ----------
        datum: str
            The datum to be used for the Earth geometry.

        Returns
        -------
        earthGeometry: namedtuple
            The namedtuple containing the Earth geometry.
        """
        geodesy = namedtuple("earthGeometry", "semiMajorAxis flattening")
        ellipsoid = {
            "SIRGAS2000": geodesy(6378137.0, 1 / 298.257223563),
            "SAD69": geodesy(6378160.0, 1 / 298.25),
            "NAD83": geodesy(6378137.0, 1 / 298.257024899),
            "WGS84": geodesy(6378137.0, 1 / 298.257223563),
        }
        try:
            return ellipsoid[datum]
        except KeyError:
            raise AttributeError(
                f"The reference system {datum} for Earth geometry " "is not recognized."
            )

    # Auxiliary functions - Geodesic Coordinates
    def geodesicToUtm(self, lat, lon):
        """Function which converts geodetic coordinates, i.e. lat/lon, to UTM
        projection coordinates. Can be used only for latitudes between -80.00°
        and 84.00°

        Parameters
        ----------
        lat : float
            The latitude coordinates of the point of analysis, must be contained
            between -80.00° and 84.00°
        lon : float
            The longitude coordinates of the point of analysis, must be contained
            between -180.00° and 180.00°

        Returns
        -------
        x: float
            East coordinate, always positive
        y:
            North coordinate, always positive
        utmZone: int
            The number of the UTM zone of the point of analysis, can vary between
            1 and 60
        utmLetter: string
            The letter of the UTM zone of the point of analysis, can vary between
            C and X, omitting the letters "I" and "O"
        hemis: string
            Returns "S" for southern hemisphere and "N" for Northern hemisphere
        EW: string
            Returns "W" for western hemisphere and "E" for eastern hemisphere
        """

        # Calculate the central meridian of UTM zone
        if lon != 0:
            signal = lon / abs(lon)
            if signal > 0:
                aux = lon - 3
                aux = aux * signal
                div = aux // 6
                lon_mc = div * 6 + 3
                EW = "E"
            else:
                aux = lon + 3
                aux = aux * signal
                div = aux // 6
                lon_mc = (div * 6 + 3) * signal
                EW = "W"
        else:
            lon_mc = 3
            EW = "W|E"

        # Select the desired datum (i.e. the ellipsoid parameters)
        flattening = self.ellipsoid.flattening
        semiMajorAxis = self.ellipsoid.semiMajorAxis

        # Evaluate the hemisphere and determine the N coordinate at the Equator
        if lat < 0:
            N0 = 10000000
            hemis = "S"
        else:
            N0 = 0
            hemis = "N"

        # Convert the input lat and lon to radians
        lat = lat * np.pi / 180
        lon = lon * np.pi / 180
        lon_mc = lon_mc * np.pi / 180

        # Evaluate reference parameters
        K0 = 1 - 1 / 2500
        e2 = 2 * flattening - flattening**2
        e2lin = e2 / (1 - e2)

        # Evaluate auxiliary parameters
        A = e2 * e2
        B = A * e2
        C = np.sin(2 * lat)
        D = np.sin(4 * lat)
        E = np.sin(6 * lat)
        F = (1 - e2 / 4 - 3 * A / 64 - 5 * B / 256) * lat
        G = (3 * e2 / 8 + 3 * A / 32 + 45 * B / 1024) * C
        H = (15 * A / 256 + 45 * B / 1024) * D
        I = (35 * B / 3072) * E

        # Evaluate other reference parameters
        n = semiMajorAxis / ((1 - e2 * (np.sin(lat) ** 2)) ** 0.5)
        t = np.tan(lat) ** 2
        c = e2lin * (np.cos(lat) ** 2)
        ag = (lon - lon_mc) * np.cos(lat)
        m = semiMajorAxis * (F - G + H - I)

        # Evaluate new auxiliary parameters
        J = (1 - t + c) * ag * ag * ag / 6
        K = (5 - 18 * t + t * t + 72 * c - 58 * e2lin) * (ag**5) / 120
        L = (5 - t + 9 * c + 4 * c * c) * ag * ag * ag * ag / 24
        M = (61 - 58 * t + t * t + 600 * c - 330 * e2lin) * (ag**6) / 720

        # Evaluate the final coordinates
        x = 500000 + K0 * n * (ag + J + K)
        y = N0 + K0 * (m + n * np.tan(lat) * (ag * ag / 2 + L + M))

        # Convert the output lat and lon to degrees
        lat = lat * 180 / np.pi
        lon = lon * 180 / np.pi
        lon_mc = lon_mc * 180 / np.pi

        # Calculate the UTM zone number
        utmZone = int((lon_mc + 183) / 6)

        # Calculate the UTM zone letter
        letters = "CDEFGHJKLMNPQRSTUVWXX"
        utmLetter = letters[int(80 + lat) >> 3]

        return x, y, utmZone, utmLetter, hemis, EW

    def utmToGeodesic(self, x, y, utmZone, hemis):
        """Function to convert UTM coordinates to geodesic coordinates
        (i.e. latitude and longitude). The latitude should be between -80°
        and 84°

        Parameters
        ----------
        x : float
            East UTM coordinate in meters
        y : float
            North UTM coordinate in meters
        utmZone : int
            The number of the UTM zone of the point of analysis, can vary between
            1 and 60
        hemis : string
            Equals to "S" for southern hemisphere and "N" for Northern hemisphere

        Returns
        -------
        lat: float
            latitude of the analyzed point
        lon: float
            latitude of the analyzed point
        """

        if hemis == "N":
            y = y + 10000000

        # Calculate the Central Meridian from the UTM zone number
        centralMeridian = utmZone * 6 - 183  # degrees

        # Select the desired datum
        flattening = self.ellipsoid.flattening
        semiMajorAxis = self.ellipsoid.semiMajorAxis

        # Calculate reference values
        K0 = 1 - 1 / 2500
        e2 = 2 * flattening - flattening**2
        e2lin = e2 / (1 - e2)
        e1 = (1 - (1 - e2) ** 0.5) / (1 + (1 - e2) ** 0.5)

        # Calculate auxiliary values
        A = e2 * e2
        B = A * e2
        C = e1 * e1
        D = e1 * C
        E = e1 * D

        m = (y - 10000000) / K0
        mi = m / (semiMajorAxis * (1 - e2 / 4 - 3 * A / 64 - 5 * B / 256))

        # Calculate other auxiliary values
        F = (3 * e1 / 2 - 27 * D / 32) * np.sin(2 * mi)
        G = (21 * C / 16 - 55 * E / 32) * np.sin(4 * mi)
        H = (151 * D / 96) * np.sin(6 * mi)

        lat1 = mi + F + G + H
        c1 = e2lin * (np.cos(lat1) ** 2)
        t1 = np.tan(lat1) ** 2
        n1 = semiMajorAxis / ((1 - e2 * (np.sin(lat1) ** 2)) ** 0.5)
        quoc = (1 - e2 * np.sin(lat1) * np.sin(lat1)) ** 3
        r1 = semiMajorAxis * (1 - e2) / (quoc**0.5)
        d = (x - 500000) / (n1 * K0)

        # Calculate other auxiliary values
        I = (5 + 3 * t1 + 10 * c1 - 4 * c1 * c1 - 9 * e2lin) * d * d * d * d / 24
        J = (
            (61 + 90 * t1 + 298 * c1 + 45 * t1 * t1 - 252 * e2lin - 3 * c1 * c1)
            * (d**6)
            / 720
        )
        K = d - (1 + 2 * t1 + c1) * d * d * d / 6
        L = (
            (5 - 2 * c1 + 28 * t1 - 3 * c1 * c1 + 8 * e2lin + 24 * t1 * t1)
            * (d**5)
            / 120
        )

        # Finally calculate the coordinates in lat/lot
        lat = lat1 - (n1 * np.tan(lat1) / r1) * (d * d / 2 - I + J)
        lon = centralMeridian * np.pi / 180 + (K + L) / np.cos(lat1)

        # Convert final lat/lon to Degrees
        lat = lat * 180 / np.pi
        lon = lon * 180 / np.pi

        return lat, lon

    def calculateEarthRadius(self, lat):
        """Simple function to calculate the Earth Radius at a specific latitude
        based on ellipsoidal reference model (datum). The earth radius here is
        assumed as the distance between the ellipsoid's center of gravity and a
        point on ellipsoid surface at the desired
        Pay attention: The ellipsoid is an approximation for the earth model and
        will obviously output an estimate of the perfect distance between earth's
        relief and its center of gravity.

        Parameters
        ----------
        lat : float
            latitude in which the Earth radius will be calculated

        Returns
        -------
        float:
            Earth Radius at the desired latitude in meters
        """
        # Select the desired datum (i.e. the ellipsoid parameters)
        flattening = self.ellipsoid.flattening
        semiMajorAxis = self.ellipsoid.semiMajorAxis

        # Calculate the semi minor axis length
        # semiMinorAxis = semiMajorAxis - semiMajorAxis*(flattening**(-1))
        semiMinorAxis = semiMajorAxis * (1 - flattening)

        # Convert latitude to radians
        lat = lat * np.pi / 180

        # Calculate the Earth Radius in meters
        eRadius = np.sqrt(
            (
                (np.cos(lat) * (semiMajorAxis**2)) ** 2
                + (np.sin(lat) * (semiMinorAxis**2)) ** 2
            )
            / ((np.cos(lat) * semiMajorAxis) ** 2 + (np.sin(lat) * semiMinorAxis) ** 2)
        )

        # Convert latitude to degrees
        lat = lat * 180 / np.pi

        return eRadius

    def decimalDegressToArcSeconds(self, angle):
        """Function to convert an angle in decimal degrees to deg/min/sec.
         Converts (°) to (° ' ")

        Parameters
        ----------
        angle : float
            The angle that you need convert to deg/min/sec. Must be given in
            decimal degrees.

        Returns
        -------
        deg: float
            The degrees.
        min: float
            The arc minutes. 1 arc-minute = (1/60)*degree
        sec: float
            The arc Seconds. 1 arc-second = (1/3600)*degree
        """

        if angle < 0:
            signal = -1
        else:
            signal = 1

        deg = (signal * angle) // 1
        min = abs(signal * angle - deg) * 60 // 1
        sec = abs((signal * angle - deg) * 60 - min) * 60
        # print("The angle {:f} is equals to {:.0f}º {:.0f}' {:.3f}'' ".format(
        #    angle, signal*deg, min, sec
        # ))

        return deg, min, sec
