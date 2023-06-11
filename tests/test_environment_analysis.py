import copy
import os
from unittest.mock import patch

import ipywidgets as widgets
import matplotlib as plt
import pytest
from IPython.display import HTML

plt.rcParams.update({"figure.max_open_warning": 0})


@pytest.mark.slow
@patch("matplotlib.pyplot.show")
def test_allInfo(mock_show, env_analysis):
    """Test the EnvironmentAnalysis.allInfo() method, which already invokes
    several other methods. It is a good way to test the whole class in a first view.
    However, if it fails, it is hard to know which method is failing.

    Parameters
    ----------
    env_analysis : EnvironmentAnalysis
        A simple object of the Environment Analysis class

    Returns
    -------
    None
    """
    assert env_analysis.allInfo() == None
    # remove the files created by the method
    os.remove("wind_rose.gif")


@pytest.mark.slow
@patch("matplotlib.pyplot.show")
def test_distribution_plots(mock_show, env_analysis):
    """Tests the distribution plots method of the EnvironmentAnalysis class. It
    only checks if the method runs without errors. It does not check if the
    plots are correct, as this would require a lot of work and would be
    difficult to maintain.

    Parameters
    ----------
    env_analysis : EnvironmentAnalysis
        A simple object of the EnvironmentAnalysis class.

    Returns
    -------
    None
    """

    # Check distribution plots
    assert env_analysis.plots.wind_gust_distribution() == None
    assert env_analysis.plots.surface10m_wind_speed_distribution() == None
    assert env_analysis.plots.wind_gust_distribution_over_average_day() == None
    assert (
        env_analysis.plots.sustained_surface_wind_speed_distribution_over_average_day()
        == None
    )


@pytest.mark.slow
@patch("matplotlib.pyplot.show")
def test_average_plots(mock_show, env_analysis):
    """Tests the average plots method of the EnvironmentAnalysis class. It
    only checks if the method runs without errors. It does not check if the
    plots are correct, as this would require a lot of work and would be
    difficult to maintain.

    Parameters
    ----------
    env_analysis : EnvironmentAnalysis
        A simple object of the EnvironmentAnalysis class.

    Returns
    -------
    None
    """
    # Check "average" plots
    assert env_analysis.plots.average_temperature_along_day() == None
    assert env_analysis.plots.average_surface10m_wind_speed_along_day(False) == None
    assert env_analysis.plots.average_surface10m_wind_speed_along_day(True) == None
    assert (
        env_analysis.plots.average_sustained_surface100m_wind_speed_along_day() == None
    )
    assert env_analysis.plots.average_day_wind_rose_all_hours() == None
    assert env_analysis.plots.average_day_wind_rose_specific_hour(12) == None


@pytest.mark.slow
@patch("matplotlib.pyplot.show")
def test_profile_plots(mock_show, env_analysis):
    """Check the profile plots method of the EnvironmentAnalysis class. It
    only checks if the method runs without errors. It does not check if the
    plots are correct, as this would require a lot of work and would be
    difficult to maintain.

    Parameters
    ----------
    mock_show : Mock
        Mock of the matplotlib.pyplot.show() method
    env_analysis : EnvironmentAnalysis
        A simple object of the EnvironmentAnalysis class.
    """
    # Check profile plots
    assert env_analysis.plots.wind_heading_profile_over_average_day() == None
    assert (
        env_analysis.plots.average_wind_heading_profile(clear_range_limits=False)
        == None
    )
    assert (
        env_analysis.plots.average_wind_heading_profile(clear_range_limits=True) == None
    )
    assert (
        env_analysis.plots.average_wind_speed_profile(clear_range_limits=False) == None
    )
    assert (
        env_analysis.plots.average_wind_speed_profile(clear_range_limits=True) == None
    )
    assert env_analysis.plots.average_pressure_profile(clear_range_limits=False) == None
    assert env_analysis.plots.average_pressure_profile(clear_range_limits=True) == None
    assert env_analysis.plots.wind_profile_over_average_day() == None


@pytest.mark.slow
@patch("matplotlib.pyplot.show")
def test_animation_plots(mock_show, env_analysis):
    """Check the animation plots method of the EnvironmentAnalysis class. It
    only checks if the method runs without errors. It does not check if the
    plots are correct, as this would require a lot of work and would be
    difficult to maintain.

    Parameters
    ----------
    mock_show : Mock
        Mock of the matplotlib.pyplot.show() method
    env_analysis : EnvironmentAnalysis
        A simple object of the EnvironmentAnalysis class.
    """

    # Check animation plots
    assert isinstance(env_analysis.plots.animate_average_wind_rose(), widgets.Image)
    assert isinstance(
        env_analysis.plots.animate_wind_gust_distribution_over_average_day(), HTML
    )
    assert isinstance(
        env_analysis.plots.animate_wind_heading_profile_over_average_day(), HTML
    )
    assert isinstance(env_analysis.plots.animate_wind_profile_over_average_day(), HTML)
    assert isinstance(
        env_analysis.plots.animate_sustained_surface_wind_speed_distribution_over_average_day(),
        HTML,
    )


@pytest.mark.slow
def test_exports(env_analysis):
    """Check the export methods of the EnvironmentAnalysis class. It
    only checks if the method runs without errors. It does not check if the
    files are correct, as this would require a lot of work and would be
    difficult to maintain.

    Parameters
    ----------
    env_analysis : EnvironmentAnalysis
        A simple object of the EnvironmentAnalysis class.
    """

    assert env_analysis.exportMeanProfiles() == None
    assert env_analysis.save("EnvAnalysisDict") == None

    env2 = copy.deepcopy(env_analysis)
    env2.load("EnvAnalysisDict")
    assert env2.allInfo() == None

    # Delete file created by save method
    os.remove("EnvAnalysisDict")
