# -*- coding: utf-8 -*-

__author__ = "Giovani Hidalgo Ceotto, Oscar Mauricio Prada Ramirez, João Lemes Gribel Soares, Mateus Stano, Pedro Henrique Marinho Bressan, Patrick Bales, Lakshman Peri, Gautam Yarramreddy, Curtis Hu, and William Bradford"
__copyright__ = "Copyright 20XX, RocketPy Team"
__license__ = "MIT"

import numpy as np
from functools import cached_property

from rocketpy.motors import Motor
from rocketpy.Function import funcify_method, Function


class LiquidMotor(Motor):
    """Class to specify characteristics and useful operations for Liquid
    motors."""

    def __init__(
        self,
        thrustSource,
        burnOut,
        nozzleRadius,
        nozzlePosition,
        throatRadius,
        reshapeThrustCurve=False,
        interpolationMethod="linear",
    ):
        """Initialize Motor class, process thrust curve and geometrical
        parameters and store results.

        Parameters
        ----------
        thrustSource : int, float, callable, string, array
            Motor's thrust curve. Can be given as an int or float, in which
            case the thrust will be considered constant in time. It can
            also be given as a callable function, whose argument is time in
            seconds and returns the thrust supplied by the motor in the
            instant. If a string is given, it must point to a .csv or .eng file.
            The .csv file shall contain no headers and the first column must
            specify time in seconds, while the second column specifies thrust.
            Arrays may also be specified, following rules set by the class
            Function. See help(Function). Thrust units are Newtons.
        burnOut : int, float
            Motor burn out time in seconds.
        nozzleRadius : int, float, optional
            Motor's nozzle outlet radius in meters. Its value does not impact
            trajectory simulation.
        nozzlePosition : float
            Motor's nozzle outlet position in meters, specified in the motor's
            coordinate system. See `Motor.coordinateSystemOrientation` for
            more information.
        throatRadius : int, float, optional
            Motor's nozzle throat radius in meters. Its value has very low
            impact in trajectory simulation, only useful to analyze
            dynamic instabilities, therefore it is optional.
        reshapeThrustCurve : boolean, tuple, optional
            If False, the original thrust curve supplied is not altered. If a
            tuple is given, whose first parameter is a new burn out time and
            whose second parameter is a new total impulse in Ns, the thrust
            curve is reshaped to match the new specifications. May be useful
            for motors whose thrust curve shape is expected to remain similar
            in case the impulse and burn time varies slightly. Default is
            False.
        interpolationMethod : string, optional
            Method of interpolation to be used in case thrust curve is given
            by data set in .csv or .eng, or as an array. Options are 'spline'
            'akima' and 'linear'. Default is "linear".
        """
        super().__init__(
            thrustSource,
            burnOut,
            nozzleRadius,
            nozzlePosition,
            throatRadius,
            reshapeThrustCurve,
            interpolationMethod,
        )
        self.positioned_tanks = []

    @funcify_method("time (s)", "mass (kg)")
    def mass(self):
        """Evaluates the mass of the motor as the sum of each tank mass.

        Parameters
        ----------
        t : float
            Time in seconds.

        Returns
        -------
        Function
            Mass of the motor, in kg.
        """
        totalMass = Function(0)

        for positioned_tank in self.positioned_tanks:
            totalMass += positioned_tank.get("tank").mass

        return totalMass

    @cached_property
    def propellantInitialMass(self):
        """Property to store the initial mass of the propellant.

        Returns
        -------
        float
            Initial mass of the propellant, in kg.
        """
        return self.mass(0)

    @funcify_method("time (s)", "mass flow rate (kg/s)", extrapolation="zero")
    def massFlowRate(self):
        """Evaluates the mass flow rate of the motor as the sum of each tank
        mass flow rate.

        Parameters
        ----------
        t : float
            Time in seconds.

        Returns
        -------
        Function
            Mass flow rate of the motor, in kg/s.
        """
        massFlowRate = Function(0)

        for positioned_tank in self.positioned_tanks:
            massFlowRate += positioned_tank.get("tank").netMassFlowRate

        return massFlowRate

    @funcify_method("time (s)", "center of mass (m)")
    def centerOfMass(self):
        """Evaluates the center of mass of the motor from each tank center of
        mass and positioning. The center of mass height is measured relative to
        the motor nozzle.

        Parameters
        ----------
        t : float
            Time in seconds.

        Returns
        -------
        Function
            Center of mass of the motor, in meters.
        """
        totalMass = 0
        massBalance = 0

        for positioned_tank in self.positioned_tanks:
            tank = positioned_tank.get("tank")
            tankPosition = positioned_tank.get("position")
            totalMass += tank.mass
            massBalance += tank.mass * (tankPosition + tank.centerOfMass)

        return massBalance / totalMass

    @cached_property
    def inertiaTensor(self):
        """Evaluates the principal moment of inertia of the motor from each
        tank by the parallel axis theorem. The moment of inertia is measured
        relative to the motor center of mass with the z-axis being the motor
        symmetry axis and the x and y axes completing the right-handed
        coordinate system.

        Parameters
        ----------
        t : float
            Time in seconds.

        Returns
        -------
        tuple (of Functions)
            Pricipal moment of inertia tensor of the motor, in kg*m^2.
        """
        self.inertiaI = self.inertiaZ = Function(0)
        centerOfMass = self.centerOfMass

        for positioned_tank in self.positioned_tanks:
            tank = positioned_tank.get("tank")
            tankPosition = positioned_tank.get("position")
            self.inertiaI += (
                tank.inertiaTensor
                + tank.mass * (tankPosition + tank.centerOfMass - centerOfMass) ** 2
            )

        # Set naming convention
        self.inertiaI.setInputs("time (s)")
        self.inertiaZ.setInputs("time (s)")
        self.inertiaI.setOutputs("inertia y (kg*m^2)")
        self.inertiaZ.setOutputs("inertia z (kg*m^2)")

        return self.inertiaI, self.inertiaI, self.inertiaZ

    def addTank(self, tank, position):
        """Adds a tank to the rocket motor.

        Parameters
        ----------
        tank : Tank
            Tank object to be added to the rocket motor.
        position : float
            Position of the tank relative to the motor nozzle, in meters.
            The position is measured from the nozzle tip to the tank
            geometry reference zero point.
        """
        self.positioned_tanks.append({"tank": tank, "position": position})

    def allInfo(self):
        """Prints out all data and graphs available about the Motor.

        Parameters
        ----------
        None

        Return
        ------
        None
        """
        # Print nozzle details
        print("Nozzle Details")
        print("Nozzle Radius: " + str(self.nozzleRadius) + " m")
        print("Nozzle Throat Radius: " + str(self.throatRadius) + " m")

        # Print motor details
        print("\nMotor Details")
        print("Total Burning Time: " + str(self.burnOutTime) + " s")
        print(
            "Total Propellant Mass: "
            + "{:.3f}".format(self.propellantInitialMass)
            + " kg"
        )
        print(
            "Propellant Exhaust Velocity: "
            + "{:.3f}".format(self.exhaustVelocity)
            + " m/s"
        )
        print("Average Thrust: " + "{:.3f}".format(self.averageThrust) + " N")
        print(
            "Maximum Thrust: "
            + str(self.maxThrust)
            + " N at "
            + str(self.maxThrustTime)
            + " s after ignition."
        )
        print("Total Impulse: " + "{:.3f}".format(self.totalImpulse) + " Ns")

        # Show plots
        print("\nPlots")
        self.thrust.plot(0, self.burnOutTime)
        self.mass.plot(0, self.burnOutTime)
        self.massFlowRate.plot(0, self.burnOutTime)
        self.centerOfMass.plot(0, self.burnOutTime, samples=50)
        self.inertiaTensor[0].plot(0, self.burnOutTime, samples=50)
        self.inertiaTensor[2].plot(0, self.burnOutTime, samples=50)