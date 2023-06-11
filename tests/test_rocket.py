from unittest.mock import patch

import numpy as np
import pytest

from rocketpy import Rocket, SolidMotor
from rocketpy.AeroSurface import NoseCone


@patch("matplotlib.pyplot.show")
def test_rocket(mock_show):
    test_motor = SolidMotor(
        thrustSource="data/motors/Cesaroni_M1670.eng",
        burnOut=3.9,
        grainNumber=5,
        grainSeparation=5 / 1000,
        grainDensity=1815,
        grainOuterRadius=33 / 1000,
        grainInitialInnerRadius=15 / 1000,
        grainInitialHeight=120 / 1000,
        nozzleRadius=33 / 1000,
        throatRadius=11 / 1000,
        interpolationMethod="linear",
        grainsCenterOfMassPosition=0.39796,
        nozzlePosition=0,
        coordinateSystemOrientation="nozzleToCombustionChamber",
    )

    test_rocket = Rocket(
        radius=127 / 2000,
        mass=19.197 - 2.956,
        inertiaI=6.60,
        inertiaZ=0.0351,
        powerOffDrag="data/calisto/powerOffDragCurve.csv",
        powerOnDrag="data/calisto/powerOnDragCurve.csv",
        centerOfDryMassPosition=0,
        coordinateSystemOrientation="tailToNose",
    )

    test_rocket.addMotor(test_motor, position=-1.255)

    test_rocket.setRailButtons(0.2, -0.5)

    NoseCone = test_rocket.addNose(
        length=0.55829, kind="vonKarman", position=1.278, name="NoseCone"
    )
    FinSet = test_rocket.addTrapezoidalFins(
        4, span=0.100, rootChord=0.120, tipChord=0.040, position=-1.04956
    )
    Tail = test_rocket.addTail(
        topRadius=0.0635, bottomRadius=0.0435, length=0.060, position=-1.194656
    )

    def drogueTrigger(p, h, y):
        # p = pressure
        # y = [x, y, z, vx, vy, vz, e0, e1, e2, e3, w1, w2, w3]
        # activate drogue when vz < 0 m/s.
        return True if y[5] < 0 else False

    def mainTrigger(p, h, y):
        # p = pressure
        # y = [x, y, z, vx, vy, vz, e0, e1, e2, e3, w1, w2, w3]
        # activate main when vz < 0 m/s and z < 800 m.
        return True if y[5] < 0 and h < 800 else False

    Main = test_rocket.addParachute(
        "Main",
        CdS=10.0,
        trigger=mainTrigger,
        samplingRate=105,
        lag=1.5,
        noise=(0, 8.3, 0.5),
    )

    Drogue = test_rocket.addParachute(
        "Drogue",
        CdS=1.0,
        trigger=drogueTrigger,
        samplingRate=105,
        lag=1.5,
        noise=(0, 8.3, 0.5),
    )

    static_margin = test_rocket.staticMargin(0)

    # Check if allInfo and static_method methods are working properly
    assert test_rocket.allInfo() == None or not abs(static_margin - 2.05) < 0.01
    # Check if NoseCone allInfo() is working properly
    assert NoseCone.allInfo() == None
    # Check if FinSet allInfo() is working properly
    assert FinSet.allInfo() == None
    # Check if Tail allInfo() is working properly
    assert Tail.allInfo() == None
    # Check if draw method is working properly
    assert FinSet.draw() == None


@patch("matplotlib.pyplot.show")
def test_coordinate_system_orientation(mock_show):
    motor_nozzleToCombustionChamber = SolidMotor(
        thrustSource="data/motors/Cesaroni_M1670.eng",
        burnOut=3.9,
        grainNumber=5,
        grainSeparation=5 / 1000,
        grainDensity=1815,
        grainOuterRadius=33 / 1000,
        grainInitialInnerRadius=15 / 1000,
        grainInitialHeight=120 / 1000,
        nozzleRadius=33 / 1000,
        throatRadius=11 / 1000,
        interpolationMethod="linear",
        grainsCenterOfMassPosition=0.39796,
        nozzlePosition=0,
        coordinateSystemOrientation="nozzleToCombustionChamber",
    )

    motor_combustionChamberToNozzle = SolidMotor(
        thrustSource="data/motors/Cesaroni_M1670.eng",
        burnOut=3.9,
        grainNumber=5,
        grainSeparation=5 / 1000,
        grainDensity=1815,
        grainOuterRadius=33 / 1000,
        grainInitialInnerRadius=15 / 1000,
        grainInitialHeight=120 / 1000,
        nozzleRadius=33 / 1000,
        throatRadius=11 / 1000,
        interpolationMethod="linear",
        grainsCenterOfMassPosition=-0.39796,
        nozzlePosition=0,
        coordinateSystemOrientation="combustionChamberToNozzle",
    )

    rocket_tail_to_nose = Rocket(
        radius=127 / 2000,
        mass=19.197 - 2.956,
        inertiaI=6.60,
        inertiaZ=0.0351,
        powerOffDrag="data/calisto/powerOffDragCurve.csv",
        powerOnDrag="data/calisto/powerOnDragCurve.csv",
        centerOfDryMassPosition=0,
        coordinateSystemOrientation="tailToNose",
    )

    rocket_tail_to_nose.addMotor(motor_nozzleToCombustionChamber, position=-1.255)

    NoseCone = rocket_tail_to_nose.addNose(
        length=0.55829, kind="vonKarman", position=1.278, name="NoseCone"
    )
    FinSet = rocket_tail_to_nose.addTrapezoidalFins(
        4, span=0.100, rootChord=0.120, tipChord=0.040, position=-1.04956
    )

    static_margin_tail_to_nose = rocket_tail_to_nose.staticMargin(0)

    rocket_nose_to_tail = Rocket(
        radius=127 / 2000,
        mass=19.197 - 2.956,
        inertiaI=6.60,
        inertiaZ=0.0351,
        powerOffDrag="data/calisto/powerOffDragCurve.csv",
        powerOnDrag="data/calisto/powerOnDragCurve.csv",
        centerOfDryMassPosition=0,
        coordinateSystemOrientation="noseToTail",
    )

    rocket_nose_to_tail.addMotor(motor_combustionChamberToNozzle, position=1.255)

    NoseCone = rocket_nose_to_tail.addNose(
        length=0.55829, kind="vonKarman", position=-1.278, name="NoseCone"
    )
    FinSet = rocket_nose_to_tail.addTrapezoidalFins(
        4, span=0.100, rootChord=0.120, tipChord=0.040, position=1.04956
    )

    static_margin_nose_to_tail = rocket_nose_to_tail.staticMargin(0)

    assert (
        rocket_tail_to_nose.allInfo() == None
        or rocket_nose_to_tail.allInfo() == None
        or not abs(static_margin_tail_to_nose - static_margin_nose_to_tail) < 0.0001
    )


@patch("matplotlib.pyplot.show")
def test_elliptical_fins(mock_show):
    test_motor = SolidMotor(
        thrustSource="data/motors/Cesaroni_M1670.eng",
        burnOut=3.9,
        grainNumber=5,
        grainSeparation=5 / 1000,
        grainDensity=1815,
        grainOuterRadius=33 / 1000,
        grainInitialInnerRadius=15 / 1000,
        grainInitialHeight=120 / 1000,
        nozzleRadius=33 / 1000,
        throatRadius=11 / 1000,
        interpolationMethod="linear",
        grainsCenterOfMassPosition=0.39796,
        nozzlePosition=0,
        coordinateSystemOrientation="nozzleToCombustionChamber",
    )

    test_rocket = Rocket(
        radius=127 / 2000,
        mass=19.197 - 2.956,
        inertiaI=6.60,
        inertiaZ=0.0351,
        powerOffDrag="data/calisto/powerOffDragCurve.csv",
        powerOnDrag="data/calisto/powerOnDragCurve.csv",
        centerOfDryMassPosition=0,
        coordinateSystemOrientation="tailToNose",
    )

    test_rocket.addMotor(test_motor, position=-1.255)

    test_rocket.setRailButtons(0.2, -0.5)

    NoseCone = test_rocket.addNose(
        length=0.55829, kind="vonKarman", position=1.278, name="NoseCone"
    )
    FinSet = test_rocket.addEllipticalFins(
        4, span=0.100, rootChord=0.120, position=-1.04956
    )
    Tail = test_rocket.addTail(
        topRadius=0.0635, bottomRadius=0.0435, length=0.060, position=-1.194656
    )

    def drogueTrigger(p, h, y):
        # p = pressure
        # y = [x, y, z, vx, vy, vz, e0, e1, e2, e3, w1, w2, w3]
        # activate drogue when vz < 0 m/s.
        return True if y[5] < 0 else False

    def mainTrigger(p, h, y):
        # p = pressure
        # y = [x, y, z, vx, vy, vz, e0, e1, e2, e3, w1, w2, w3]
        # activate main when vz < 0 m/s and z < 800 m.
        return True if y[5] < 0 and h < 800 else False

    Main = test_rocket.addParachute(
        "Main",
        CdS=10.0,
        trigger=mainTrigger,
        samplingRate=105,
        lag=1.5,
        noise=(0, 8.3, 0.5),
    )

    Drogue = test_rocket.addParachute(
        "Drogue",
        CdS=1.0,
        trigger=drogueTrigger,
        samplingRate=105,
        lag=1.5,
        noise=(0, 8.3, 0.5),
    )

    static_margin = test_rocket.staticMargin(0)

    assert test_rocket.allInfo() == None or not abs(static_margin - 2.30) < 0.01
    assert FinSet.draw() == None


@patch("matplotlib.pyplot.show")
def test_airfoil(mock_show):
    test_motor = SolidMotor(
        thrustSource="data/motors/Cesaroni_M1670.eng",
        burnOut=3.9,
        grainNumber=5,
        grainSeparation=5 / 1000,
        grainDensity=1815,
        grainOuterRadius=33 / 1000,
        grainInitialInnerRadius=15 / 1000,
        grainInitialHeight=120 / 1000,
        nozzleRadius=33 / 1000,
        throatRadius=11 / 1000,
        interpolationMethod="linear",
        grainsCenterOfMassPosition=0.39796,
        nozzlePosition=0,
        coordinateSystemOrientation="nozzleToCombustionChamber",
    )

    test_rocket = Rocket(
        radius=127 / 2000,
        mass=19.197 - 2.956,
        inertiaI=6.60,
        inertiaZ=0.0351,
        powerOffDrag="data/calisto/powerOffDragCurve.csv",
        powerOnDrag="data/calisto/powerOnDragCurve.csv",
        centerOfDryMassPosition=0,
        coordinateSystemOrientation="tailToNose",
    )

    test_rocket.addMotor(test_motor, position=-1.255)

    test_rocket.setRailButtons(0.2, -0.5)

    NoseCone = test_rocket.addNose(
        length=0.55829, kind="vonKarman", position=1.278, name="NoseCone"
    )
    FinSetNACA = test_rocket.addTrapezoidalFins(
        2,
        span=0.100,
        rootChord=0.120,
        tipChord=0.040,
        position=-1.04956,
        airfoil=("tests/fixtures/airfoils/NACA0012-radians.txt", "radians"),
    )
    FinSetE473 = test_rocket.addTrapezoidalFins(
        2,
        span=0.100,
        rootChord=0.120,
        tipChord=0.040,
        position=-1.04956,
        airfoil=("tests/fixtures/airfoils/e473-10e6-degrees.csv", "degrees"),
    )
    Tail = test_rocket.addTail(
        topRadius=0.0635, bottomRadius=0.0435, length=0.060, position=-1.194656
    )

    def drogueTrigger(p, h, y):
        # p = pressure
        # y = [x, y, z, vx, vy, vz, e0, e1, e2, e3, w1, w2, w3]
        # activate drogue when vz < 0 m/s.
        return True if y[5] < 0 else False

    def mainTrigger(p, h, y):
        # p = pressure
        # y = [x, y, z, vx, vy, vz, e0, e1, e2, e3, w1, w2, w3]
        # activate main when vz < 0 m/s and z < 800 m.
        return True if y[5] < 0 and h < 800 else False

    Main = test_rocket.addParachute(
        "Main",
        CdS=10.0,
        trigger=mainTrigger,
        samplingRate=105,
        lag=1.5,
        noise=(0, 8.3, 0.5),
    )

    Drogue = test_rocket.addParachute(
        "Drogue",
        CdS=1.0,
        trigger=drogueTrigger,
        samplingRate=105,
        lag=1.5,
        noise=(0, 8.3, 0.5),
    )

    static_margin = test_rocket.staticMargin(0)

    assert test_rocket.allInfo() == None or not abs(static_margin - 2.03) < 0.01


def test_evaluate_static_margin_assert_cp_equals_cm(kg, m, dimensionless_rocket):
    rocket = dimensionless_rocket
    rocket.evaluateStaticMargin()

    burnOutTime = rocket.motor.burnOutTime

    assert rocket.centerOfMass(0) / (2 * rocket.radius) == rocket.staticMargin(0)
    assert pytest.approx(
        rocket.centerOfMass(burnOutTime) / (2 * rocket.radius), 1e-12
    ) == pytest.approx(rocket.staticMargin(burnOutTime), 1e-12)
    assert rocket.totalLiftCoeffDer == 0
    assert rocket.cpPosition == 0


@pytest.mark.parametrize(
    "k, type",
    (
        [2 / 3, "conical"],
        [0.466, "ogive"],
        [0.563, "lvhaack"],
        [0.5, "default"],
        [0.5, "not a mapped string, to show default case"],
    ),
)
def test_add_nose_assert_cp_cm_plus_nose(k, type, rocket, dimensionless_rocket, m):
    rocket.addNose(length=0.55829, kind=type, position=1.278)
    cpz = 1.278 - k * 0.55829  # Relative to the center of dry mass
    clalpha = 2

    static_margin_initial = (rocket.centerOfMass(0) - cpz) / (2 * rocket.radius)
    assert static_margin_initial == pytest.approx(rocket.staticMargin(0), 1e-12)

    static_margin_final = (rocket.centerOfMass(np.inf) - cpz) / (2 * rocket.radius)
    assert static_margin_final == pytest.approx(rocket.staticMargin(np.inf), 1e-12)

    assert clalpha == pytest.approx(rocket.totalLiftCoeffDer, 1e-12)
    assert rocket.cpPosition == pytest.approx(cpz, 1e-12)

    dimensionless_rocket.addNose(length=0.55829 * m, kind=type, position=1.278 * m)
    assert pytest.approx(dimensionless_rocket.staticMargin(0), 1e-12) == pytest.approx(
        rocket.staticMargin(0), 1e-12
    )
    assert pytest.approx(
        dimensionless_rocket.staticMargin(np.inf), 1e-12
    ) == pytest.approx(rocket.staticMargin(np.inf), 1e-12)
    assert pytest.approx(
        dimensionless_rocket.totalLiftCoeffDer, 1e-12
    ) == pytest.approx(rocket.totalLiftCoeffDer, 1e-12)
    assert pytest.approx(dimensionless_rocket.cpPosition / m, 1e-12) == pytest.approx(
        rocket.cpPosition, 1e-12
    )


def test_add_tail_assert_cp_cm_plus_tail(rocket, dimensionless_rocket, m):
    rocket.addTail(
        topRadius=0.0635,
        bottomRadius=0.0435,
        length=0.060,
        position=-1.194656,
    )

    clalpha = -2 * (1 - (0.0635 / 0.0435) ** (-2)) * (0.0635 / (rocket.radius)) ** 2
    cpz = -1.194656 - (0.06 / 3) * (
        1 + (1 - (0.0635 / 0.0435)) / (1 - (0.0635 / 0.0435) ** 2)
    )

    static_margin_initial = (rocket.centerOfMass(0) - cpz) / (2 * rocket.radius)
    assert static_margin_initial == pytest.approx(rocket.staticMargin(0), 1e-12)

    static_margin_final = (rocket.centerOfMass(np.inf) - cpz) / (2 * rocket.radius)
    assert static_margin_final == pytest.approx(rocket.staticMargin(np.inf), 1e-12)
    assert np.abs(clalpha) == pytest.approx(np.abs(rocket.totalLiftCoeffDer), 1e-8)
    assert rocket.cpPosition == cpz

    dimensionless_rocket.addTail(
        topRadius=0.0635 * m,
        bottomRadius=0.0435 * m,
        length=0.060 * m,
        position=-1.194656 * m,
    )
    assert pytest.approx(dimensionless_rocket.staticMargin(0), 1e-12) == pytest.approx(
        rocket.staticMargin(0), 1e-12
    )
    assert pytest.approx(
        dimensionless_rocket.staticMargin(np.inf), 1e-12
    ) == pytest.approx(rocket.staticMargin(np.inf), 1e-12)
    assert pytest.approx(
        dimensionless_rocket.totalLiftCoeffDer, 1e-12
    ) == pytest.approx(rocket.totalLiftCoeffDer, 1e-12)
    assert pytest.approx(dimensionless_rocket.cpPosition / m, 1e-12) == pytest.approx(
        rocket.cpPosition, 1e-12
    )


@pytest.mark.parametrize(
    "sweep_angle, expected_fin_cpz, expected_clalpha, expected_cpz_cm",
    [(39.8, 2.51, 3.16, 1.65), (-10, 2.47, 3.21, 1.63), (29.1, 2.50, 3.28, 1.66)],
)
def test_add_trapezoidal_fins_sweep_angle(
    rocket, sweep_angle, expected_fin_cpz, expected_clalpha, expected_cpz_cm
):
    # Reference values from OpenRocket
    Nose = rocket.addNose(length=0.55829, kind="vonKarman", position=1.278)

    FinSet = rocket.addTrapezoidalFins(
        n=3,
        span=0.090,
        rootChord=0.100,
        tipChord=0.050,
        sweepAngle=sweep_angle,
        position=-1.182,
    )

    # Check center of pressure
    translate = 0.55829 + 0.71971
    cpz = -1.182 - FinSet.cpz  # Should be - 1.232
    assert translate - cpz == pytest.approx(expected_fin_cpz, 0.01)

    # Check lift coefficient derivative
    cl_alpha = FinSet.cl(1, 0.0)
    assert cl_alpha == pytest.approx(expected_clalpha, 0.01)

    # Check rocket's center of pressure (just double checking)
    assert translate - rocket.cpPosition == pytest.approx(expected_cpz_cm, 0.01)


@pytest.mark.parametrize(
    "sweep_length, expected_fin_cpz, expected_clalpha, expected_cpz_cm",
    [(0.075, 2.51, 3.16, 1.65), (-0.0159, 2.47, 3.21, 1.63), (0.05, 2.50, 3.28, 1.66)],
)
def test_add_trapezoidal_fins_sweep_length(
    rocket, sweep_length, expected_fin_cpz, expected_clalpha, expected_cpz_cm
):
    # Reference values from OpenRocket
    Nose = rocket.addNose(length=0.55829, kind="vonKarman", position=1.278)

    FinSet = rocket.addTrapezoidalFins(
        n=3,
        span=0.090,
        rootChord=0.100,
        tipChord=0.050,
        sweepLength=sweep_length,
        position=-1.182,
    )

    # Check center of pressure
    translate = 0.55829 + 0.71971
    cpz = -FinSet.cp[2] - 1.182
    assert translate - cpz == pytest.approx(expected_fin_cpz, 0.01)

    # Check lift coefficient derivative
    cl_alpha = FinSet.cl(1, 0.0)
    assert cl_alpha == pytest.approx(expected_clalpha, 0.01)

    # Check rocket's center of pressure (just double checking)
    assert translate - rocket.cpPosition == pytest.approx(expected_cpz_cm, 0.01)

    assert isinstance(rocket.aerodynamicSurfaces[0].component, NoseCone)


def test_add_fins_assert_cp_cm_plus_fins(rocket, dimensionless_rocket, m):
    rocket.addTrapezoidalFins(
        4,
        span=0.100,
        rootChord=0.120,
        tipChord=0.040,
        position=-1.04956,
    )

    cpz = -1.04956 - (
        ((0.120 - 0.040) / 3) * ((0.120 + 2 * 0.040) / (0.120 + 0.040))
        + (1 / 6) * (0.120 + 0.040 - 0.120 * 0.040 / (0.120 + 0.040))
    )

    clalpha = (4 * 4 * (0.1 / (2 * rocket.radius)) ** 2) / (
        1
        + np.sqrt(
            1
            + (2 * np.sqrt((0.12 / 2 - 0.04 / 2) ** 2 + 0.1**2) / (0.120 + 0.040))
            ** 2
        )
    )
    clalpha *= 1 + rocket.radius / (0.1 + rocket.radius)

    static_margin_initial = (rocket.centerOfMass(0) - cpz) / (2 * rocket.radius)
    assert static_margin_initial == pytest.approx(rocket.staticMargin(0), 1e-12)

    static_margin_final = (rocket.centerOfMass(np.inf) - cpz) / (2 * rocket.radius)
    assert static_margin_final == pytest.approx(rocket.staticMargin(np.inf), 1e-12)

    assert np.abs(clalpha) == pytest.approx(np.abs(rocket.totalLiftCoeffDer), 1e-12)
    assert rocket.cpPosition == pytest.approx(cpz, 1e-12)

    dimensionless_rocket.addTrapezoidalFins(
        4,
        span=0.100 * m,
        rootChord=0.120 * m,
        tipChord=0.040 * m,
        position=-1.04956 * m,
    )
    assert pytest.approx(dimensionless_rocket.staticMargin(0), 1e-12) == pytest.approx(
        rocket.staticMargin(0), 1e-12
    )
    assert pytest.approx(
        dimensionless_rocket.staticMargin(np.inf), 1e-12
    ) == pytest.approx(rocket.staticMargin(np.inf), 1e-12)
    assert pytest.approx(
        dimensionless_rocket.totalLiftCoeffDer, 1e-12
    ) == pytest.approx(rocket.totalLiftCoeffDer, 1e-12)
    assert pytest.approx(dimensionless_rocket.cpPosition / m, 1e-12) == pytest.approx(
        rocket.cpPosition, 1e-12
    )


def test_add_cm_eccentricity_assert_properties_set(rocket):
    rocket.addCMEccentricity(x=4, y=5)

    assert rocket.cpEccentricityX == -4
    assert rocket.cpEccentricityY == -5

    assert rocket.thrustEccentricityY == -4
    assert rocket.thrustEccentricityX == -5


def test_add_thrust_eccentricity_assert_properties_set(rocket):
    rocket.addThrustEccentricity(x=4, y=5)

    assert rocket.thrustEccentricityY == 4
    assert rocket.thrustEccentricityX == 5


def test_add_cp_eccentricity_assert_properties_set(rocket):
    rocket.addCPEccentricity(x=4, y=5)

    assert rocket.cpEccentricityX == 4
    assert rocket.cpEccentricityY == 5


def test_set_rail_button(rocket):
    rail_buttons = rocket.setRailButtons(0.2, -0.5, 30)
    # assert buttons_distance
    assert (
        rail_buttons.buttons_distance
        == rocket.rail_buttons[0].component.buttons_distance
        == pytest.approx(0.7, 1e-12)
    )
    # assert buttons position on rocket
    assert rocket.rail_buttons[0].position == -0.5
    # assert angular position
    assert (
        rail_buttons.angular_position
        == rocket.rail_buttons[0].component.angular_position
        == 30
    )
    # assert upper button position
    assert rocket.rail_buttons[0].component.buttons_distance + rocket.rail_buttons[
        0
    ].position == pytest.approx(0.2, 1e-12)
