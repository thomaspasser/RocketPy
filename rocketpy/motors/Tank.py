# -*- coding: utf-8 -*-

__author__ = "Giovani Hidalgo Ceotto, Oscar Mauricio Prada Ramirez, João Lemes Gribel Soares, Mateus Stano, Pedro Henrique Marinho Bressan, Patrick Bales, Lakshman Peri, Gautam Yarramreddy, Curtis Hu, and William Bradford"
__copyright__ = "Copyright 20XX, RocketPy Team"
__license__ = "MIT"

from abc import ABC, abstractmethod

from rocketpy.Function import Function, funcify_method


class Tank(ABC):
    def __init__(self, name, geometry, gas, liquid=0):
        self.name = name
        self.geometry = geometry
        self.gas = gas
        self.liquid = liquid

    @property
    @abstractmethod
    def mass(self):
        """
        Returns the total mass of liquid and gases inside the tank as a
        function of time.

        Returns
        -------
        Function
            Mass of the tank as a function of time. Units in kg.
        """
        pass

    @property
    @abstractmethod
    def netMassFlowRate(self):
        """
        Returns the net mass flow rate of the tank as a function of time.
        Net mass flow rate is the mass flow rate exiting the tank minus the
        mass flow rate entering the tank, including liquids and gases.

        Returns
        -------
        Function
            Net mass flow rate of the tank as a function of time.
        """
        pass

    @property
    @abstractmethod
    def liquidVolume(self):
        """
        Returns the volume of the liquid as a function of time.

        Returns
        -------
        Function
            Volume of the liquid as a function of time.
        """
        pass

    @property
    @abstractmethod
    def gasVolume(self):
        """
        Returns the volume of the gas as a function of time.

        Returns
        -------
        Function
            Volume of the gas as a function of time.
        """
        pass

    @property
    @abstractmethod
    def liquidHeight(self):
        """
        Returns the liquid level as a function of time. This
        height is measured from the zero level of the tank
        geometry.

        Returns
        -------
        Function
            Height of the ullage as a function of time.
        """
        pass

    @property
    @abstractmethod
    def gasHeight(self):
        """
        Returns the gas level as a function of time. This
        height is measured from the zero level of the tank
        geometry.

        Returns
        -------
        Function
            Height of the ullage as a function of time.
        """
        pass

    @property
    @abstractmethod
    def liquidMass(self):
        """
        Returns the mass of the liquid as a function of time.

        Returns
        -------
        Function
            Mass of the liquid as a function of time.
        """
        pass

    @property
    @abstractmethod
    def gasMass(self):
        """
        Returns the mass of the gas as a function of time.

        Returns
        -------
        Function
            Mass of the gas as a function of time.
        """
        pass

    @funcify_method("Time (s)", "center of mass of liquid (m)")
    def liquidCenterOfMass(self):
        """
        Returns the center of mass of the liquid portion of the tank
        as a function of time. This height is measured from the zero
        level of the tank geometry.

        Returns
        -------
        Function
            Center of mass of the liquid portion of the tank as a
            function of time.
        """
        balance = self.geometry.balance(self.geometry.bottom, self.liquidHeight.max)
        liquid_balance = balance.compose(self.liquidHeight)
        return liquid_balance / self.liquidVolume

    @funcify_method("Time (s)", "center of mass of gas (m)")
    def gasCenterOfMass(self):
        """
        Returns the center of mass of the gas portion of the tank
        as a function of time. This height is measured from the zero
        level of the tank geometry.

        Returns
        -------
        Function
            Center of mass of the gas portion of the tank as a
            function of time.
        """
        balance = self.geometry.balance(self.geometry.bottom, self.gasHeight.max)
        upper_balance = balance.compose(self.gasHeight)
        lower_balance = balance.compose(self.liquidHeight)
        return (upper_balance - lower_balance) / self.gasVolume

    @funcify_method("Time (s)", "center of mass (m)")
    def centerOfMass(self):
        """Returns the center of mass of the tank's fluids as a function of
        time. This height is measured from the zero level of the tank
        geometry.

        Returns
        -------
        Function
            Center of mass of the tank's fluids as a function of time.
        """
        return (
            self.liquidCenterOfMass * self.liquidMass
            + self.gasCenterOfMass * self.gasMass
        ) / (self.mass)

    @funcify_method("Time (s)", "inertia tensor of liquid (kg*m^2)")
    def liquidInertiaTensor(self):
        """
        Returns the inertia tensor of the liquid portion of the tank
        as a function of time. The reference point is the center of
        mass of the tank.

        Returns
        -------
        Function
            Inertia tensor of the liquid portion of the tank as a
            function of time.
        """
        Ix_volume = self.geometry.Ix_volume(self.geometry.bottom, self.liquidHeight.max)
        Ix_volume = Ix_volume.compose(self.liquidHeight)

        # Steiner theorem to account for center of mass
        Ix_volume -= self.liquidVolume * self.liquidCenterOfMass**2
        Ix_volume += (
            self.liquidVolume * (self.liquidCenterOfMass - self.centerOfMass) ** 2
        )

        return self.liquid.density * Ix_volume

    @funcify_method("Time (s)", "inertia tensor of gas (kg*m^2)")
    def gasInertiaTensor(self):
        """
        Returns the inertia tensor of the gas portion of the tank
        as a function of time. The reference point is the center of
        mass of the tank.

        Returns
        -------
        Function
            Inertia tensor of the gas portion of the tank as a
            function of time.
        """
        Ix_volume = self.geometry.Ix_volume(self.geometry.bottom, self.gasHeight.max)
        lower_inertia_volume = Ix_volume.compose(self.liquidHeight)
        upper_inertia_volume = Ix_volume.compose(self.gasHeight)
        inertia_volume = upper_inertia_volume - lower_inertia_volume

        # Steiner theorem to account for center of mass
        inertia_volume -= self.gasVolume * self.gasCenterOfMass**2
        inertia_volume += (
            self.gasVolume * (self.gasCenterOfMass - self.centerOfMass) ** 2
        )

        return self.gas.density * inertia_volume

    @funcify_method("Time (s)", "inertia tensor (kg*m^2)")
    def inertiaTensor(self):
        """
        Returns the inertia tensor of the tank's fluids as a function of
        time. The reference point is the center of mass of the tank.

        Returns
        -------
        Function
            Inertia tensor of the tank's fluids as a function of time.
        """
        return self.liquidInertiaTensor + self.gasInertiaTensor


class MassFlowRateBasedTank(Tank):
    def __init__(
        self,
        name,
        geometry,
        liquid,
        gas,
        initial_liquid_mass,
        initial_gas_mass,
        liquid_mass_flow_rate_in,
        gas_mass_flow_rate_in,
        liquid_mass_flow_rate_out,
        gas_mass_flow_rate_out,
    ):
        super().__init__(name, geometry, gas, liquid)
        self.initial_liquid_mass = initial_liquid_mass
        self.initial_gas_mass = initial_gas_mass

        self.liquid_mass_flow_rate_in = Function(
            liquid_mass_flow_rate_in,
            inputs="Time",
            outputs="Mass Flow Rate",
            interpolation="linear",
            extrapolation="zero",
        )
        self.gas_mass_flow_rate_in = Function(
            gas_mass_flow_rate_in,
            inputs="Time",
            outputs="Mass Flow Rate",
            interpolation="linear",
            extrapolation="zero",
        )
        self.liquid_mass_flow_rate_out = Function(
            liquid_mass_flow_rate_out,
            inputs="Time",
            outputs="Mass Flow Rate",
            interpolation="linear",
            extrapolation="zero",
        )
        self.gas_mass_flow_rate_out = Function(
            gas_mass_flow_rate_out,
            inputs="Time",
            outputs="Mass Flow Rate",
            interpolation="linear",
            extrapolation="zero",
        )

    @funcify_method("Time (s)", "mass (kg)")
    def mass(self):
        return self.liquidMass + self.gasMass

    @funcify_method("Time (s)", "mass (kg)")
    def liquidMass(self):
        liquid_flow = self.netLiquidFlowRate.integralFunction()
        liquidMass = self.initial_liquid_mass + liquid_flow
        if (liquidMass < 0).any():
            raise ValueError(f"The tank {self.name} is underfilled.")
        return liquidMass

    @funcify_method("Time (s)", "mass (kg)")
    def gasMass(self):
        gas_flow = self.netGasFlowRate.integralFunction()
        gasMass = self.initial_gas_mass + gas_flow
        if (gasMass < 0).any():
            raise ValueError(f"The tank {self.name} is underfilled.")
        return gasMass

    @funcify_method("Time (s)", "liquid mass flow rate (kg/s)", extrapolation="zero")
    def netLiquidFlowRate(self):
        return self.liquid_mass_flow_rate_in - self.liquid_mass_flow_rate_out

    @funcify_method("Time (s)", "gas mass flow rate (kg/s)", extrapolation="zero")
    def netGasFlowRate(self):
        return self.gas_mass_flow_rate_in - self.gas_mass_flow_rate_out

    @funcify_method("Time (s)", "mass flow rate (kg/s)", extrapolation="zero")
    def netMassFlowRate(self):
        return self.netLiquidFlowRate + self.netGasFlowRate

    @funcify_method("Time (s)", "volume (m³)")
    def liquidVolume(self):
        return self.liquidMass / self.liquid.density

    @funcify_method("Time (s)", "volume (m³)")
    def gasVolume(self):
        return self.gasMass / self.gas.density

    @funcify_method("Time (s)", "height (m)")
    def liquidHeight(self):
        return self.geometry.inverse_volume.compose(self.liquidVolume)

    @funcify_method("Time (s)", "height (m)")
    def gasHeight(self):
        fluid_volume = self.gasVolume + self.liquidVolume
        gasHeight = self.geometry.inverse_volume.compose(fluid_volume)
        if (gasHeight > self.geometry.top).any():
            raise ValueError(f"The tank {self.name} is overfilled.")
        return gasHeight


class UllageBasedTank(Tank):
    def __init__(
        self,
        name,
        geometry,
        liquid,
        gas,
        ullage,
    ):
        super().__init__(name, geometry, gas, liquid)
        self.ullage = Function(ullage, "Time (s)", "Volume (m³)", "linear")

        if (self.ullage > self.geometry.total_volume).any() or (self.ullage < 0).any():
            raise ValueError("The ullage volume is out of bounds.")

    @funcify_method("Time (s)", "mass (kg)")
    def mass(self):
        return self.liquidMass + self.gasMass

    @funcify_method("Time (s)", "mass flow rate (kg/s)")
    def netMassFlowRate(self):
        return self.mass.derivativeFunction()

    @funcify_method("Time (s)", "volume (m³)")
    def liquidVolume(self):
        return -(self.ullage - self.geometry.total_volume)

    @funcify_method("Time (s)", "volume (m³)")
    def gasVolume(self):
        return self.ullage

    @funcify_method("Time (s)", "mass (kg)")
    def gasMass(self):
        return self.gasVolume * self.gas.density

    @funcify_method("Time (s)", "mass (kg)")
    def liquidMass(self):
        return self.liquidVolume * self.liquid.density

    @funcify_method("Time (s)", "height (m)")
    def liquidHeight(self):
        return self.geometry.inverse_volume.compose(self.liquidVolume)

    @funcify_method("Time (s)", "height (m)")
    def gasHeight(self):
        return self.geometry.top


class LevelBasedTank(Tank):
    def __init__(
        self,
        name,
        geometry,
        liquid,
        gas,
        liquid_height,
    ):
        super().__init__(name, geometry, gas, liquid)
        self.liquid_height = Function(
            liquid_height, "Time (s)", "volume (m³)", "linear"
        )

        if (self.liquid_height > self.geometry.top).any() or (
            self.liquid_height < self.geometry.bottom
        ).any():
            raise ValueError("The liquid level is out of bounds.")

    @funcify_method("Time (s)", "mass (kg)")
    def mass(self):
        return self.liquidMass + self.gasMass

    @funcify_method("Time (s)", "mass flow rate (kg/s)")
    def netMassFlowRate(self):
        return self.mass.derivativeFunction()

    @funcify_method("Time (s)", "volume (m³)")
    def liquidVolume(self):
        return self.geometry.volume.compose(self.liquidHeight)

    @funcify_method("Time (s)", "volume (m³)")
    def gasVolume(self):
        return self.geometry.total_volume - self.liquidVolume

    @funcify_method("Time (s)", "height (m)")
    def liquidHeight(self):
        return self.liquid_height

    @funcify_method("Time (s)", "mass (kg)")
    def gasMass(self):
        return self.gasVolume * self.gas.density

    @funcify_method("Time (s)", "mass (kg)")
    def liquidMass(self):
        return self.liquidVolume * self.liquid.density

    @funcify_method("Time (s)", "height (m)")
    def gasHeight(self):
        return self.geometry.top


class MassBasedTank(Tank):
    def __init__(
        self,
        name,
        geometry,
        liquid,
        gas,
        liquid_mass,
        gas_mass,
    ):
        super().__init__(name, geometry, gas, liquid)
        self.liquid_mass = Function(liquid_mass, "Time (s)", "mass (kg)", "linear")
        self.gas_mass = Function(gas_mass, "Time (s)", "mass (kg)", "linear")

    @funcify_method("Time (s)", "mass (kg)")
    def mass(self):
        return self.liquidMass + self.gasMass

    @funcify_method("Time (s)", "mass flow rate (kg/s)")
    def netMassFlowRate(self):
        return self.mass.derivativeFunction()

    @funcify_method("Time (s)", "mass (kg)")
    def liquidMass(self):
        return self.liquid_mass

    @funcify_method("Time (s)", "mass (kg)")
    def gasMass(self):
        return self.gas_mass

    @funcify_method("Time (s)", "volume (m³)")
    def gasVolume(self):
        return self.gasMass / self.gas.density

    @funcify_method("Time (s)", "volume (m³)")
    def liquidVolume(self):
        return self.liquidMass / self.liquid.density

    @funcify_method("Time (s)", "height (m)")
    def liquidHeight(self):
        return self.geometry.inverse_volume.compose(self.liquidVolume)

    @funcify_method("Time (s)", "height (m)")
    def gasHeight(self):
        fluid_volume = self.gasVolume + self.liquidVolume
        gasHeight = self.geometry.inverse_volume.compose(fluid_volume)
        # if gasHeight <= self.geometry.top:
        return gasHeight
        # else:
        #     raise ValueError(
        #         f"The tank {self.name}, is overfilled"
        #         f"with gas height {gasHeight} at time {t}"
        #     )