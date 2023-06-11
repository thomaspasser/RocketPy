# -*- coding: utf-8 -*-
__author__ = "Franz Masatoshi Yuri, Lucas Kierulff Balabram, Guilherme Fernandes Alves"
__copyright__ = "Copyright 20XX, RocketPy Team"
__license__ = "MIT"

import traceback
import warnings

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

from .Environment import Environment
from .Function import Function
from .AeroSurface import TrapezoidalFins


# TODO: Needs tests
def compute_CdS_from_drop_test(
    terminal_velocity, rocket_mass, air_density=1.225, g=9.80665
):
    """Returns the parachute's CdS calculated through its final speed, air
    density in the landing point, the rocket's mass and the force of gravity
    in the landing point.

    Parameters
    ----------
    terminal_velocity : float
        Rocket's speed in m/s when landing.
    rocket_mass : float
        Rocket's dry mass in kg.
    air_density : float, optional
        Air density, in kg/m^3, right before the rocket lands. Default value is 1.225.
    g : float, optional
        Gravitational acceleration experienced by the rocket and parachute during
        descent in m/s^2. Default value is the standard gravity, 9.80665.

    Returns
    -------
    CdS : float
        Number equal to drag coefficient times reference area for parachute.

    """

    return 2 * rocket_mass * g / ((terminal_velocity**2) * air_density)


# TODO: Needs tests
def calculateEquilibriumAltitude(
    rocket_mass,
    CdS,
    z0,
    v0=0,
    env=None,
    eps=1e-3,
    max_step=0.1,
    see_graphs=True,
    g=9.80665,
    estimated_final_time=10,
):
    """Returns a dictionary containing the time, altitude and velocity of the
    system rocket-parachute in which the terminal velocity is reached.


    Parameters
    ----------
    rocket_mass : float
        Rocket's mass in kg.
    CdS : float
        Number equal to drag coefficient times reference area for parachute.
    z0 : float
        Initial altitude of the rocket in meters.
    v0 : float, optional
        Rocket's initial speed in m/s. Must be negative
    env : Environment, optional
        Environmental conditions at the time of the launch.
    eps : float, optional
        acceptable error in meters.
    max_step: float, optional
        maximum allowed time step size to solve the integration
    see_graphs : boolean, optional
        True if you want to see time vs altitude and time vs speed graphs,
        False otherwise.
    g : float, optional
        Gravitational acceleration experienced by the rocket and parachute during
        descent in m/s^2. Default value is the standard gravity, 9.80665.
    estimated_final_time: float, optional
        Estimative of how much time (in seconds) will spend until vertical terminal
        velocity is reached. Must be positive. Default is 10. It can affect the final
        result if the value is not high enough. Increase the estimative in case the
        final solution is not founded.


    Returns
    -------
    altitudeFunction: Function
        Altitude as a function of time. Always a Function object.
    velocityFunction:
        Vertical velocity as a function of time. Always a Function object.
    final_sol : dictionary
        Dictionary containing the values for time, altitude and speed of
        the rocket when it reaches terminal velocity.
    """
    final_sol = {}

    if not v0 < 0:
        print("Please set a valid negative value for v0")
        return None

    # TODO: Improve docs
    def check_constant(f, eps):
        """_summary_

        Parameters
        ----------
        f : array, list

            _description_
        eps : float
            _description_

        Returns
        -------
        int, None
            _description_
        """
        for i in range(len(f) - 2):
            if abs(f[i + 2] - f[i + 1]) < eps and abs(f[i + 1] - f[i]) < eps:
                return i
        return None

    if env == None:
        environment = Environment(
            railLength=5.0,
            latitude=0,
            longitude=0,
            elevation=1000,
            date=(2020, 3, 4, 12),
        )
    else:
        environment = env

    # TODO: Improve docs
    def du(z, u):
        """_summary_

        Parameters
        ----------
        z : float
            _description_
        u : float
            velocity, in m/s, at a given z altitude

        Returns
        -------
        float
            _description_
        """
        return (
            u[1],
            -g + environment.density(z) * ((u[1]) ** 2) * CdS / (2 * rocket_mass),
        )

    u0 = [z0, v0]

    us = solve_ivp(
        fun=du,
        t_span=(0, estimated_final_time),
        y0=u0,
        vectorized=True,
        method="LSODA",
        max_step=max_step,
    )

    constant_index = check_constant(us.y[1], eps)

    # TODO: Improve docs by explaining what is happening below with constant_index
    if constant_index is not None:
        final_sol = {
            "time": us.t[constant_index],
            "altitude": us.y[0][constant_index],
            "velocity": us.y[1][constant_index],
        }

    altitudeFunction = Function(
        source=np.array(list(zip(us.t, us.y[0])), dtype=np.float64),
        inputs="Time (s)",
        outputs="Altitude (m)",
        interpolation="linear",
    )

    velocityFunction = Function(
        source=np.array(list(zip(us.t, us.y[1])), dtype=np.float64),
        inputs="Time (s)",
        outputs="Vertical Velocity (m/s)",
        interpolation="linear",
    )

    if see_graphs:
        altitudeFunction()
        velocityFunction()

    return altitudeFunction, velocityFunction, final_sol


def fin_flutter_analysis(
    fin_thickness, shear_modulus, flight, see_prints=True, see_graphs=True
):
    """Calculate and plot the Fin Flutter velocity using the pressure profile
    provided by the selected atmospheric model. It considers the Flutter Boundary
    Equation that published in NACA Technical Paper 4197.
    These results are only estimates of a real problem and may not be useful for
    fins made from non-isotropic materials.
    Currently, this function works if only a single set of fins is added, otherwise
    it will use the last set of fins added to the rocket.

    Parameters
    ----------
    fin_thickness : float
        The fin thickness, in meters
    shear_modulus : float
        Shear Modulus of fins' material, must be given in Pascal
    flight : rocketpy.Flight
        Flight object containing the rocket's flight data
    see_prints : boolean, optional
        True if you want to see the prints, False otherwise.
    see_graphs : boolean, optional
        True if you want to see the graphs, False otherwise. If False, the
        function will return the vectors containing the data for the graphs.

    Return
    ------
    None
    """

    # First, we need identify if there is at least a fin set in the rocket
    for aero_surface in flight.rocket.aerodynamicSurfaces:
        if isinstance(aero_surface, TrapezoidalFins):
            # s: surface area; ar: aspect ratio; la: lambda
            root_chord = aero_surface.rootChord
            s = (aero_surface.tipChord + root_chord) * aero_surface.span / 2
            ar = aero_surface.span * aero_surface.span / s
            la = aero_surface.tipChord / root_chord

    # This ensures that a fin set was found in the rocket, if not, break
    try:
        s = s
    except NameError:
        print("There is no fin set in the rocket, can't run a Flutter Analysis.")
        return None

    # Calculate the Fin Flutter Mach Number
    flutter_mach = (
        (shear_modulus * 2 * (ar + 2) * (fin_thickness / root_chord) ** 3)
        / (1.337 * (ar**3) * (la + 1) * flight.pressure)
    ) ** 0.5

    safety_factor = _flutter_safety_factor(flight, flutter_mach)

    # Prints everything
    if see_prints:
        _flutter_prints(
            fin_thickness,
            shear_modulus,
            s,
            ar,
            la,
            flutter_mach,
            safety_factor,
            flight,
        )

    # Plots everything
    if see_graphs:
        _flutter_plots(flight, flutter_mach, safety_factor)
        return None
    else:
        return flutter_mach, safety_factor


def _flutter_safety_factor(flight, flutter_mach):
    """Calculates the safety factor for the fin flutter analysis.

    Parameters
    ----------
    flight : rocketpy.Flight
        Flight object containing the rocket's flight data
    flutter_mach : rocketpy.Function
        Mach Number at which the fin flutter occurs. See the
        `fin_flutter_analysis` function for more details.

    Returns
    -------
    rocketpy.Function
        The safety factor for the fin flutter analysis.
    """
    safety_factor = [[t, 0] for t in flutter_mach[:, 0]]
    for i in range(len(flutter_mach)):
        try:
            safety_factor[i][1] = flutter_mach[i][1] / flight.MachNumber[i][1]
        except ZeroDivisionError:
            safety_factor[i][1] = np.nan

    # Function needs to remove NaN and Inf values from the source
    safety_factor = np.array(safety_factor)
    safety_factor = safety_factor[~np.isnan(safety_factor).any(axis=1)]
    safety_factor = safety_factor[~np.isinf(safety_factor).any(axis=1)]

    safety_factor = Function(
        source=safety_factor,
        inputs="Time (s)",
        outputs="Fin Flutter Safety Factor",
        interpolation="linear",
    )

    return safety_factor


def _flutter_plots(flight, flutter_mach, safety_factor):
    """Plot the Fin Flutter Mach Number and the Safety Factor for the flutter.

    Parameters
    ----------
    flight : rocketpy.Flight
        Flight object containing the rocket's flight data
    flutter_mach : rocketpy.Function
        Function containing the Fin Flutter Mach Number, see fin_flutter_analysis
        for more details.
    safety_factor : rocketpy.Function
        Function containing the Safety Factor for the fin flutter. See
        fin_flutter_analysis for more details.

    Returns
    -------
    None
    """
    fig = plt.figure(figsize=(6, 6))
    ax1 = plt.subplot(211)
    ax1.plot(
        flutter_mach[:, 0],
        flutter_mach[:, 1],
        label="Fin flutter Mach Number",
    )
    ax1.plot(
        flight.MachNumber[:, 0],
        flight.MachNumber[:, 1],
        label="Rocket Freestream Speed",
    )
    ax1.set_xlim(0, flight.apogeeTime if flight.apogeeTime != 0.0 else flight.tFinal)
    ax1.set_title("Fin Flutter Mach Number x Time(s)")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Mach")
    ax1.legend()
    ax1.grid()

    ax2 = plt.subplot(212)
    ax2.plot(safety_factor[:, 0], safety_factor[:, 1])
    ax2.set_xlim(flight.outOfRailTime, flight.apogeeTime)
    ax2.set_ylim(0, 6)
    ax2.set_title("Fin Flutter Safety Factor")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Safety Factor")
    ax2.grid()

    plt.subplots_adjust(hspace=0.5)
    plt.show()

    return None


def _flutter_prints(
    fin_thickness,
    shear_modulus,
    s,
    ar,
    la,
    flutter_mach,
    safety_factor,
    flight,
):
    """Prints out the fin flutter analysis results. See fin_flutter_analysis for
    more details.

    Parameters
    ----------
    fin_thickness : float
        The fin thickness, in meters
    shear_modulus : float
        Shear Modulus of fins' material, must be given in Pascal
    s : float
        Fin surface area, in squared meters
    ar : float
        Fin aspect ratio
    la : float
        Fin lambda, defined as the tip_chord / root_chord ratio
    flutter_mach : rocketpy.Function
        The Mach Number at which the fin flutter occurs, considering the variation
        of the speed of sound with altitude. See fin_flutter_analysis for more
        details.
    safety_factor : rocketpy.Function
        The Safety Factor for the fin flutter. Defined as the Fin Flutter Mach
        Number divided by the Freestream Mach Number.
    flight : rocketpy.Flight
        Flight object containing the rocket's flight data

    Returns
    -------
    None
    """
    time_index = np.argmin(flutter_mach[:, 1])
    time_min_mach = flutter_mach[time_index, 0]
    min_mach = flutter_mach[time_index, 1]
    min_vel = min_mach * flight.speedOfSound(time_min_mach)

    time_index = np.argmin(safety_factor[:, 1])
    time_min_sf = safety_factor[time_index, 0]
    min_sf = safety_factor[time_index, 1]
    altitude_min_sf = flight.z(time_min_sf) - flight.env.elevation

    print("\nFin's parameters")
    print(f"Surface area (S): {s:.4f} m2")
    print(f"Aspect ratio (AR): {ar:.3f}")
    print(f"tip_chord/root_chord ratio = \u03BB = {la:.3f}")
    print(f"Fin Thickness: {fin_thickness:.5f} m")
    print(f"Shear Modulus (G): {shear_modulus:.3e} Pa")

    print("\nFin Flutter Analysis")
    print(f"Minimum Fin Flutter Velocity: {min_vel:.3f} m/s at {time_min_mach:.2f} s")
    print(f"Minimum Fin Flutter Mach Number: {min_mach:.3f} ")
    print(f"Minimum Safety Factor: {min_sf:.3f} at {time_min_sf:.2f} s")
    print(f"Altitude of minimum Safety Factor: {altitude_min_sf:.3f} m (AGL)\n")

    return None


def create_dispersion_dictionary(filename):
    """Creates a dictionary with the rocket data provided by a .csv file.
    File should be organized in four columns: attribute_class, parameter_name,
    mean_value, standard_deviation. The first row should be the header.
    It is advised to use ";" as separator, but "," should work on most of cases.
    The "," separator might cause problems if the data set contains lists where
    the items are separated by commas.

    Parameters
    ----------
    filename : string
        String with the path to the .csv file. The file should follow the
        following structure:

            attribute_class; parameter_name; mean_value; standard_deviation;
            environment; ensembleMember; [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];;
            motor; impulse; 1415.15; 35.3;
            motor; burnOut; 5.274; 1;
            motor; nozzleRadius; 0.021642; 0.0005;
            motor; throatRadius; 0.008; 0.0005;
            motor; grainSeparation; 0.006; 0.001;
            motor; grainDensity; 1707; 50;

    Returns
    -------
    dictionary
        Dictionary with all rocket data to be used in dispersion analysis. The
        dictionary will follow the following structure:
            analysis_parameters = {
                'environment': {
                    'ensembleMember': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
                },
                'motor': {
                    'impulse': (1415.15, 35.3),
                    'burnOut': (5.274, 1),
                    'nozzleRadius': (0.021642, 0.0005),
                    'throatRadius': (0.008, 0.0005),
                    'grainSeparation': (0.006, 0.001),
                    'grainDensity': (1707, 50),
                    }
            }
    """
    try:
        file = np.genfromtxt(
            filename, usecols=(1, 2, 3), skip_header=1, delimiter=";", dtype=str
        )
    except ValueError:
        warnings.warn(
            f"Error caught: the recommended delimiter is ';'. If using ',' instead, be "
            + "aware that some resources might not work as expected if your data "
            + "set contains lists where the items are separated by commas. "
            + "Please consider changing the delimiter to ';' if that is the case."
        )
        warnings.warn(traceback.format_exc())
        file = np.genfromtxt(
            filename, usecols=(1, 2, 3), skip_header=1, delimiter=",", dtype=str
        )
    analysis_parameters = dict()
    for row in file:
        if row[0] != "":
            if row[2] == "":
                try:
                    analysis_parameters[row[0].strip()] = float(row[1])
                except ValueError:
                    analysis_parameters[row[0].strip()] = eval(row[1])
            else:
                try:
                    analysis_parameters[row[0].strip()] = (float(row[1]), float(row[2]))
                except ValueError:
                    analysis_parameters[row[0].strip()] = ""
    return analysis_parameters
