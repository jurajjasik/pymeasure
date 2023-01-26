#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2023 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import time

from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import strict_discrete_set
from pymeasure.instruments.validators import truncated_range, truncated_discrete_set


byteorder = 'little'
encoding = 'utf-8'
termination_character = "\r"
reflection_limit_map = {0: 0, 1: 100, 2: 150, 3: 180, 4: 200, 5: 230}


def _has_correct_termination_character(b):
    return b[-1] == termination_character.encode(encoding=encoding)[0]


def _err_msg_invalid_termination_character(b):
    return f"Invalid termination character received: {hex(b[-1])}"


def _is_expecting_acknowledgement(command):
    if command in ["v", "5", "8", "6", "7", "T"]:
        return False
    if command.endswith("?"):
        return False
    return True


class Kusg245_250A(Instrument):
    """Represents KU SG 2.45 250 A the 2.45 GHz ISM-Band Microwave Generator
    and provides a high-level interface for interacting with the instrument.

    :param power_limit: power set-point limit in Watts.
                        See :attr:`~.Kusg245_250A.power_setpoint`
                        and :meth:`~.Kusg245_250A.tune()`.

    Usage example:

    .. code-block:: python

        from pymeasure.instruments.kuhneelectronic import Kusg245_250A

        generator = Kusg245_250A("ASRL3::INSTR", power_limit=100) # limits the output
                                                                  # power set-point to 100 W

        generator.external_enabled = False      # biasing and RF output controlled by serial comm
        generator.power = 20                    # Sets the output power to 20 Watts
        generator.bias_enabled = True           # Enables amplifier biasing
        generator.rf_enabled = True             # Enables the RF output

        p_fwd = generator.power_forward         # Reads forward power in Watts
        p_rev = generator.power_reverse         # Reads reflected power in Watts
    """

    def __init__(self, adapter, name="KU SG 2.45 250 A", power_limit=250, **kwargs):
        kwargs.setdefault("baud_rate", 115200)
        kwargs.setdefault("read_termination", termination_character)
        kwargs.setdefault("write_termination", termination_character)

        super().__init__(adapter, name, **kwargs)

        assert 0 < power_limit <= 250
        self._power_limit = power_limit
        self.power_setpoint_values = [0, power_limit]

    version = Instrument.measurement("v", """Readout of the firmware version.""")

    @property
    def voltage_5v(self):
        """Readout of internal 5V supply voltage in Volts."""
        self.write("5")
        b = self.read_bytes(3)
        if _has_correct_termination_character(b):
            return 103.0 / 4700.0 * int.from_bytes(b[:2])
        raise ConnectionError(_err_msg_invalid_termination_character(b))

    @property
    def voltage_32v(self):
        """Readout of 32V supply voltage in Volts."""
        self.write("8")
        b = self.read_bytes(3)
        if _has_correct_termination_character(b):
            return 1282.0 / 8200.0 * int.from_bytes(b[:2])
        raise ConnectionError(_err_msg_invalid_termination_character(b))

    @property
    def power_forward(self):
        """Readout of forward power in Watts."""
        self.write("6")
        b = self.read_bytes(2)
        if _has_correct_termination_character(b):
            return int.from_bytes(b[:1])
        raise ConnectionError(_err_msg_invalid_termination_character(b))

    @property
    def power_reverse(self):
        """Readout of reverse power in Watts."""
        self.write("7")
        b = self.read_bytes(2)
        if _has_correct_termination_character(b):
            return int.from_bytes(b[:1])
        raise ConnectionError(_err_msg_invalid_termination_character(b))

    temperature = Instrument.measurement(
        "T",
        """Readout of temperature sensor near the final transistor in °C."""
    )

    @property
    def external_enabled(self):
        """Control the whether the amplifier enabling is done
        via external inputs on 8-pin connector
        or via the serial interface (boolean).
        """
        self.write("r?")
        b = self.read_bytes(2)
        if _has_correct_termination_character(b):
            return bool.from_bytes(b[:1])
        raise ConnectionError(_err_msg_invalid_termination_character(b))

    @external_enabled.setter
    def external_enabled(self, value):
        if value:
            self.write("R")
        else:
            self.write("r")

    @property
    def bias_enabled(self):
        """Transistor biasing (boolean).

        Biasing must be enabled before switching RF on
        (see :attr:`~.Kusg245_250A.rf_enabled`).
        """
        self.write("x?")
        b = self.read_bytes(2)
        if _has_correct_termination_character(b):
            return bool.from_bytes(b[:1])
        raise ConnectionError(_err_msg_invalid_termination_character(b))

    @bias_enabled.setter
    def bias_enabled(self, value):
        if value:
            self.write("X")
        else:
            self.write("x")

    @property
    def rf_enabled(self):
        """Enable RF output (boolean).

        .. note::

            Bias must be enabled before RF is enabled
            (see :attr:`~.Kusg245_250A.bias_enabled`)
        """
        self.write("o?")
        b = self.read_bytes(2)
        if _has_correct_termination_character(b):
            return bool.from_bytes(b[:1])
        raise ConnectionError(_err_msg_invalid_termination_character(b))

    @rf_enabled.setter
    def rf_enabled(self, value):
        if value:
            self.write("O")
        else:
            self.write("o")

    @property
    def pulse_mode_enabled(self):
        """Enable RF output (boolean).

        .. note::

            Bias must be enabled before RF is enabled
            (see :attr:`~.Kusg245_250A.bias_enabled`)
        """
        self.write("p?")
        b = self.read_bytes(2)
        if _has_correct_termination_character(b):
            return bool.from_bytes(b[:1])
        raise ConnectionError(_err_msg_invalid_termination_character(b))

    @pulse_mode_enabled.setter
    def pulse_mode_enabled(self, value):
        if value:
            self.write("P")
        else:
            self.write("p")

    @property
    def freq_steps_fine_enabled(self):
        """Enables fine frequency steps (boolean)."""
        self.write("fm?")
        b = self.read_bytes(2)
        if _has_correct_termination_character(b):
            return bool.from_bytes(b[:1])
        raise ConnectionError(_err_msg_invalid_termination_character(b))

    @freq_steps_fine_enabled.setter
    def freq_steps_fine_enabled(self, value):
        if value:
            self.write("fm1")
        else:
            self.write("fm0")

    freq_steps_fine_enabled = Instrument.control(
        "fm?",
        "fm%d",
        """Enables fine frequency steps (boolean).""",
        validator=strict_discrete_set,
        values=[False, True],
        set_process=lambda v: {True: 1, False: 0}[v],
        get_process=lambda v: bool.from_bytes(v.encode(encoding), byteorder=byteorder),
    )

    frequency_coarse = Instrument.control(
        "f?",
        "f%04d",
        """Coarse frequency in MHz (integer from 2400 to 2500).

        Fine frequency mode must be disabled
        (see :attr:`~.Kusg245_250A.freq_steps_fine_enabled`).
        Resolution: 1 MHz. Invalid values are truncated.
        """,
        validator=truncated_range,
        values=[2400, 2500],
        get_process=lambda v: int(v[:-3]) if v.endswith("MHz") else None,
    )

    frequency_fine = Instrument.control(
        "f?",
        "f%07d",
        """Fine frequency in kHz (integer from 2400000 to 2500000).

        Fine frequency mode must be enabled
        (see :attr:`~.Kusg245_250A.freq_steps_fine_enabled`).
        Resolution: 10 kHz. Invalid values are truncated.
        Values are rounded to tens.
        """,
        validator=truncated_range,
        values=[2400000, 2500000],
        set_process=lambda v: round(v, -1),
        get_process=lambda v: int(v[:-3]) if v.endswith("kHz") else None,
    )

    power_setpoint = Instrument.control(
        "A?",
        "A%03d",
        """Output power set-point in Watts (integer from 0 to :attr:`power_limit`
        parameter - see constructor).

        Resolution: 1 W. Invalid values are truncated.
        """,
        validator=truncated_range,
        values=[0, 250],
        dynamic=True,
    )

    pulse_width = Instrument.control(
        "C?",
        "C%04d",
        """Pulse width in ms (integer from 10 to 1000).

        Resolution: 5 ms. Invalid values are truncated.
        Values are rounded to multipliers of 5.
        """,
        validator=truncated_range,
        values=[10, 1000],
        set_process=lambda v: round(2 * v, -1) / 2,
    )

    off_time = Instrument.control(
        "c?",
        "c%04d",
        """Off time for the pulse mode in ms (integer from 10 to 1000).

        Resolution: 5 ms. Invalid values are truncated.
        Values are rounded to multipliers of 5.
        """,
        validator=truncated_range,
        values=[10, 1000],
        set_process=lambda v: round(2 * v, -1) / 2,
    )

    @property
    def phase_shift(self):
        """Phase shift in degrees (float from 0 to 358.6).

        Resolution: 8-bits. Values out of range are truncated.
        """
        self.write("H?")
        b = self.read_bytes(2)
        if _has_correct_termination_character(b):
            return int.from_bytes(b[:1]) / 256.0 * 360.0
        raise ConnectionError(_err_msg_invalid_termination_character(b))

    @phase_shift.setter
    def phase_shift(self, value):
        value = int(round(truncated_range(value, [0, 358.6])) / 360.0 * 256.0)
        self.write(f"H{value:03d}")

    @property
    def reflection_limit(self):
        "B%d",
        """Limit of reflection in Watts (integer in 0 - no limit, 100, 150, 180, 200, 230).

        .. note::

            If the limit for the reflected power is reached, the forward power
            is reduced to the specified value and the power control mechanism
            is locked until the alarm has been cleared by the user via
            :meth:`~.Kusg245_250A.clear_VSWR_error()`.
        """
        self.write("B?")
        b = self.read_bytes(2)
        if _has_correct_termination_character(b):
            return reflection_limit_map[b[0]]
        raise ConnectionError(_err_msg_invalid_termination_character(b))

    @reflection_limit.setter
    def reflection_limit(self, value):
        value = truncated_discrete_set(value, reflection_limit_map.values())
        inv_reflection_limit_map = {v: k for k, v in reflection_limit_map.items()}
        value = inv_reflection_limit_map[value]
        self.write(f"B{value:d}")

    def tune(self, power):
        """
        Find and set the frequency with lowest reflection
        at a given power.

        :param power: A power set-point for tuning (in Watts).
                      (integer from 0 to :attr:`power_limit`
                      parameter - see constructor).
        """
        power = truncated_range(power, [0, self._power_limit])
        self.write(f"b{power:03d}")

    def clear_VSWR_error(self):
        """
        Clears the VSWR error.

        See: :attr:`~.Kusg245_250A.reflection_limit`.
        """
        self.write("z")

    def store_settings(self):
        """
        Save actual settings to EEPROM.

        The following parameters are saved:
        frequency mode (see :attr:`~.Kusg245_250A.freq_steps_fine_enabled`),
        frequency (see :attr:`~.Kusg245_250A.frequency_coarse`
        or :attr:`~.Kusg245_250A.frequency_fine`),
        output power set-point (see :attr:`~.Kusg245_250A.power_setpoint`),
        ON/OFF control setting (see :attr:`~.Kusg245_250A.external_enabled`),
        reflection limit (see :attr:`~.Kusg245_250A.reflection_limit`),
        on time for pulse mode (see :attr:`~.Kusg245_250A.pulse_width`) and
        off time for pulse mode (see :attr:`~.Kusg245_250A.off_time`).
        """
        self.write("SE")

    def shutdown(self):
        """
        Safe shut-down the generator.

        1. Disable RF output.
        2. Deactivate biasing.
        """
        self.rf_enabled = False
        self.bias_enabled = False

    def turn_on(self):
        """
        Safe turn-on the generator.

        1. Activate biasing.
        2. Enable RF output.
        """
        self.bias_enabled = True
        time.sleep(0.500)  # not sure if needed
        self.rf_enabled = True

    def write(self, command, **kwargs):
        self.adapter.write(command, **kwargs)
        if _is_expecting_acknowledgement(command) and self.read() != "A":
            raise ConnectionError("Expected acknowledgment.")
