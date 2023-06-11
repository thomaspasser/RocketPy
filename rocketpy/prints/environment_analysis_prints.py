__author__ = "Guilherme Fernandes Alves"
__copyright__ = "Copyright 20XX, RocketPy Team"
__license__ = "MIT"

import numpy as np

from rocketpy.units import convert_units


class _EnvironmentAnalysisPrints:
    """Class to print environment analysis results

    Parameters
    ----------
    env_analysis : EnvironmentAnalysis
        EnvironmentAnalysis object to be printed

    """

    def __init__(self, env_analysis):
        self.env_analysis = env_analysis
        return None

    def dataset(self):
        print("Dataset Information: ")
        print(
            f"Time Period: From {self.env_analysis.start_date} to {self.env_analysis.end_date}"
        )  # TODO: Improve Timezone
        print(
            f"Available hours: From {self.env_analysis.start_hour} to {self.env_analysis.end_hour}"
        )  # TODO: Improve Timezone
        print("Surface Data File Path: ", self.env_analysis.surfaceDataFile)
        print(
            "Latitude Range: From ",
            self.env_analysis.singleLevelInitLat,
            "° To ",
            self.env_analysis.singleLevelEndLat,
            "°",
        )
        print(
            "Longitude Range: From ",
            self.env_analysis.singleLevelInitLon,
            "° To ",
            self.env_analysis.singleLevelEndLon,
            "°",
        )
        print("Pressure Data File Path: ", self.env_analysis.pressureLevelDataFile)
        print(
            "Latitude Range: From ",
            self.env_analysis.pressureLevelInitLat,
            "° To ",
            self.env_analysis.pressureLevelEndLat,
            "°",
        )
        print(
            "Longitude Range: From ",
            self.env_analysis.pressureLevelInitLon,
            "° To ",
            self.env_analysis.pressureLevelEndLon,
            "°",
        )
        return None

    def launch_site(self):
        # Print launch site details
        print("\nLaunch Site Details")
        print("Launch Site Latitude: {:.5f}°".format(self.env_analysis.latitude))
        print("Launch Site Longitude: {:.5f}°".format(self.env_analysis.longitude))
        print(
            "Surface Elevation (from surface data file): ", self.env_analysis.elevation
        )  # TODO: Improve units
        print(
            "Max Expected Altitude: ",
            self.env_analysis.maxExpectedAltitude,
            " ",
            self.env_analysis.unit_system["length"],
        )
        return None

    def pressure(self):
        print("\nPressure Information")
        print(
            f"Average Surface Pressure: {self.env_analysis.average_surface_pressure:.2f} ± {self.env_analysis.std_surface_pressure:.2f} {self.env_analysis.unit_system['pressure']}"
        )
        print(
            f"Average Pressure at {convert_units(1000, 'ft', self.env_analysis.current_units['height_ASL']):.0f} {self.env_analysis.current_units['height_ASL']}: {self.env_analysis.average_pressure_at_1000ft:.2f} ± {self.env_analysis.std_pressure_at_1000ft:.2f} {self.env_analysis.unit_system['pressure']}"
        )
        print(
            f"Average Pressure at {convert_units(10000, 'ft', self.env_analysis.current_units['height_ASL']):.0f} {self.env_analysis.current_units['height_ASL']}: {self.env_analysis.average_pressure_at_10000ft:.2f} ± {self.env_analysis.std_pressure_at_1000ft:.2f} {self.env_analysis.unit_system['pressure']}"
        )
        print(
            f"Average Pressure at {convert_units(30000, 'ft', self.env_analysis.current_units['height_ASL']):.0f} {self.env_analysis.current_units['height_ASL']}: {self.env_analysis.average_pressure_at_30000ft:.2f} ± {self.env_analysis.std_pressure_at_1000ft:.2f} {self.env_analysis.unit_system['pressure']}"
        )
        return None

    def temperature(self):
        print("\nTemperature Information")
        print(
            f"Historical Maximum Temperature: {self.env_analysis.record_max_temperature:.2f} {self.env_analysis.unit_system['temperature']}"
        )
        print(
            f"Historical Minimum Temperature: {self.env_analysis.record_min_temperature:.2f} {self.env_analysis.unit_system['temperature']}"
        )
        print(
            f"Average Daily Maximum Temperature: {self.env_analysis.average_max_temperature:.2f} {self.env_analysis.unit_system['temperature']}"
        )
        print(
            f"Average Daily Minimum Temperature: {self.env_analysis.average_min_temperature:.2f} {self.env_analysis.unit_system['temperature']}"
        )
        return None

    def wind_speed(self):
        print(
            f"\nElevated Wind Speed Information ({convert_units(100, 'm', self.env_analysis.unit_system['length']):.0f} {self.env_analysis.unit_system['length']} above ground)"
        )
        print(
            f"\nSustained Surface Wind Speed Information ({convert_units(10, 'm', self.env_analysis.unit_system['length']):.0f} {self.env_analysis.unit_system['length']} above ground)"
        )
        print(
            f"Historical Maximum Wind Speed: {self.env_analysis.record_max_surface_10m_wind_speed:.2f} {self.env_analysis.unit_system['wind_speed']}"
        )
        print(
            f"Historical Minimum Wind Speed: {self.env_analysis.record_min_surface_10m_wind_speed:.2f} {self.env_analysis.unit_system['wind_speed']}"
        )
        print(
            f"Average Daily Maximum Wind Speed: {self.env_analysis.average_max_surface_10m_wind_speed:.2f} {self.env_analysis.unit_system['wind_speed']}"
        )
        print(
            f"Average Daily Minimum Wind Speed: {self.env_analysis.average_min_surface_10m_wind_speed:.2f} {self.env_analysis.unit_system['wind_speed']}"
        )
        print(
            f"Historical Maximum Wind Speed: {self.env_analysis.record_max_surface_100m_wind_speed:.2f} {self.env_analysis.unit_system['wind_speed']}"
        )
        print(
            f"Historical Minimum Wind Speed: {self.env_analysis.record_min_surface_100m_wind_speed:.2f} {self.env_analysis.unit_system['wind_speed']}"
        )
        print(
            f"Average Daily Maximum Wind Speed: {self.env_analysis.average_max_surface_100m_wind_speed:.2f} {self.env_analysis.unit_system['wind_speed']}"
        )
        print(
            f"Average Daily Minimum Wind Speed: {self.env_analysis.average_min_surface_100m_wind_speed:.2f} {self.env_analysis.unit_system['wind_speed']}"
        )
        return None

    def wind_gust(self):
        print("\nWind Gust Information")
        print(
            f"Historical Maximum Wind Gust: {self.env_analysis.max_wind_gust:.2f} {self.env_analysis.unit_system['wind_speed']}"
        )
        print(
            f"Average Daily Maximum Wind Gust: {self.env_analysis.average_max_wind_gust:.2f} {self.env_analysis.unit_system['wind_speed']}"
        )
        return None

    def precipitation(self):
        print("\nPrecipitation Information")
        print(
            f"Percentage of Days with Precipitation: {100*self.env_analysis.percentage_of_days_with_precipitation:.1f}%"
        )
        print(
            f"Maximum Precipitation: {max(self.env_analysis.precipitation_per_day):.1f} {self.env_analysis.unit_system['precipitation']}"
        )
        print(
            f"Average Precipitation: {np.mean(self.env_analysis.precipitation_per_day):.1f} {self.env_analysis.unit_system['precipitation']}"
        )
        return None

    def cloud_coverage(self):
        print("\nCloud Base Height Information")
        print(
            f"Average Cloud Base Height: {self.env_analysis.mean_cloud_base_height:.2f} {self.env_analysis.unit_system['length']}"
        )
        print(
            f"Minimum Cloud Base Height: {self.env_analysis.min_cloud_base_height:.2f} {self.env_analysis.unit_system['length']}"
        )
        print(
            f"Percentage of Days Without Clouds: {100*self.env_analysis.percentage_of_days_with_no_cloud_coverage:.1f} %"
        )
        return None

    def all(self):
        self.dataset()
        self.launch_site()
        self.pressure()
        self.temperature()
        self.wind_speed()
        self.wind_gust()
        self.precipitation()
        self.cloud_coverage()
        return None
