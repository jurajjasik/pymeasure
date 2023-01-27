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

import logging

from functools import partial
from collections import ChainMap, OrderedDict

from ..inputs import BooleanInput, IntegerInput, ListInput, ScientificInput, StringInput
from ..Qt import QtCore, QtWidgets
from ...experiment import parameters
from ..thread import InstrumentThread, StoppableQThread

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class InstrumentControlWidget(QtWidgets.QWidget):
    """
    Widget for setting up an instrument control user interface.

    Currently implemented through the `InstrumentControlWindow` class, but can
    be inherited from to include in custom windows.
    """

    def __init__(
        self,
        instrument,
        measurements=None,
        controls=None,
        settings=None,
        functions=None,
        options=None,
        parent=None,
        auto_get=False,
        auto_set=True,
        auto_get_delay=0.5
    ):
        super().__init__(parent)

        self.instrument = instrument

        self.measurements = self.check_parameter_list(measurements, "measurement")
        self.controls = self.check_parameter_list(controls, "control")
        self.settings = self.check_parameter_list(settings, "setting")
        self.options = self.check_parameter_list(options, "option")
        self.functions = functions if isinstance(functions, list) else [functions]

        self.auto_read = auto_get
        self.auto_write = auto_set
        self.auto_read_delay = auto_get_delay

        self.update_list = []
        self.update_list.extend(
            [m for m in self.measurements.keys() if hasattr(self.instrument, str(m))])
        self.update_list.extend(
            [m for m in self.controls.keys() if hasattr(self.instrument, str(m))])
        self.update_list.extend(
            [m for m in self.options.keys() if hasattr(self.instrument, str(m))])
        self.update_list.extend(
            [m for m in self.settings.keys() if hasattr(self.instrument, str(m))])

        self.update_thread = InstrumentThread(self.instrument, self.update_list, delay=self.auto_read_delay)
        self.update_thread.new_value.connect(self.update_value)
        self.update_thread.error.connect(self.error)

        self._setup_ui()
        self._layout()
        self.get_and_update_all_values()
        self._auto_settings_changed()

    def _setup_ui(self):
        self._elements = []
        for name, param in self.measurements.items():
            element = self.input_from_parameter(param)
            setattr(self, name, element)
            element.setSizePolicy(
                QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding
            )

            element.setEnabled(False)

        for name, param in self.controls.items():
            element = self.input_from_parameter(param)
            setattr(self, name, element)
            element.setSizePolicy(
                QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding
            )
            if isinstance(param, parameters.FloatParameter):
                element.setButtonSymbols(QtWidgets.QAbstractSpinBox.UpDownArrows)
                element.stepEnabled = (
                    lambda: QtWidgets.QAbstractSpinBox.StepDownEnabled
                    | QtWidgets.QAbstractSpinBox.StepUpEnabled
                )

            element.stepType = lambda: QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType

            if self.auto_write:
                if isinstance(param, parameters.FloatParameter):
                    element.valueChanged.connect(partial(self.apply_setting, name))
                elif isinstance(param, parameters.ListParameter):
                    element.currentIndexChanged.connect(partial(self.apply_setting, name))

        for name, param in self.settings.items():
            element = self.input_from_parameter(param)
            setattr(self, name, element)
            element.setSizePolicy(
                QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding
            )

            if self.auto_write:
                if isinstance(param, parameters.FloatParameter):
                    element.valueChanged.connect(partial(self.apply_setting, name))
                elif isinstance(param, parameters.ListParameter):
                    element.currentIndexChanged.connect(partial(self.apply_setting, name))

        for name, param in self.options.items():
            element = self.input_from_parameter(param)
            setattr(self, name, element)
            element.setSizePolicy(
                QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding
            )

        for name in self.functions:
            element = QtWidgets.QPushButton()
            if hasattr(self.instrument, str(name)):
                setattr(self, name, element)
                element.setText(name)
                element.clicked.connect(getattr(self.instrument, name))
            else:
                setattr(self, name.__name__, element)
                element.setText(self._parse_function_name(name.__name__))
                element.clicked.connect(name)

        # Add a button for instant reading
        self.read_button = QtWidgets.QPushButton("Read", self)
        self.read_button.clicked.connect(self.get_and_update_all_values)
        self.read_button.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding
        )

        self.read_button.setEnabled(not self.auto_read)

        # Adding a button for instant writing
        self.write_button = QtWidgets.QPushButton("Write", self)
        self.write_button.clicked.connect(self.apply_all_settings)
        self.write_button.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding
        )

        self.write_button.setEnabled(not self.auto_write)

        # Adding a checkbox for changing auto_read property
        self.auto_read_box = QtWidgets.QCheckBox("Auto Read")
        self.auto_read_box.setChecked(self.auto_read)
        self.auto_read_box.stateChanged.connect(self._auto_settings_changed)

        # Adding a checkbox for changing auto_write property
        self.auto_write_box = QtWidgets.QCheckBox("Auto Write")
        self.auto_write_box.setChecked(self.auto_write)
        self.auto_write_box.stateChanged.connect(self._auto_settings_changed)
        
        # Adding status label
        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)

    def _layout(self):
        layout = QtWidgets.QGridLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Measurements
        measurements_widget = QtWidgets.QWidget()
        measurement_layout = QtWidgets.QGridLayout(measurements_widget)
        for idx, name in enumerate(self.measurements):
            measurement_layout.addWidget(QtWidgets.QLabel(name), idx, 0)
            measurement_layout.addWidget(getattr(self, name), idx, 1)

        # Controls
        for idx, name in enumerate(self.controls, len(self.measurements)):
            measurement_layout.addWidget(QtWidgets.QLabel(name), idx, 0)
            measurement_layout.addWidget(getattr(self, name), idx, 1)

        # Settings and options
        for idx, name in enumerate(self.settings, len(self.measurements)+len(self.controls)):
            measurement_layout.addWidget(QtWidgets.QLabel(name), idx, 0)
            measurement_layout.addWidget(getattr(self, name), idx, 1)

        idx0 = len(self.measurements)+len(self.controls)+len(self.settings)
        for idx, name in enumerate(self.options):
            measurement_layout.addWidget(getattr(self, name), idx0 + idx//2, idx % 2)

        measurements_widget.setLayout(measurement_layout)
        layout.addWidget(measurements_widget, 2, 0)

        # Functions
        function_widget = QtWidgets.QWidget()
        function_layout = QtWidgets.QVBoxLayout(function_widget)
        for idx, name in enumerate(self.functions):
            if hasattr(self.instrument, str(name)):
                function_layout.addWidget(getattr(self, name), idx)
            else:
                function_layout.addWidget(getattr(self, name.__name__), idx)

        function_widget.setLayout(function_layout)
        layout.addWidget(function_widget, 3, 0)

        # Global Options and controls
        global_widget = QtWidgets.QWidget()
        global_layout = QtWidgets.QGridLayout(global_widget)
        global_layout.addWidget(self.read_button, 0, 0)
        global_layout.addWidget(self.write_button, 0, 1)

        global_layout.addWidget(self.auto_read_box, 1, 0)
        global_layout.addWidget(self.auto_write_box, 1, 1)
        
        global_layout.addWidget(QtWidgets.QLabel("Status:"), 2, 0)
        global_layout.addWidget(self.status_label, 2, 1)

        global_widget.setLayout(global_layout)

        layout.addWidget(global_widget, 4, 0)

    def _parse_function_name(self, name):
        return name.replace('_', ' ')

    def update_value(self, name, value):
        """
        Set the value of an element
        :param name Name of the element
        :param value New value
        """
        QtWidgets.QApplication.processEvents()
        element = getattr(self, name)

        if not element.hasFocus():
            element.setValue(value)
        self.status_label.setText("OK")
            
    def error(self, err):
        self.status_label.setText(str(err))

    def get_and_update_all_values(self):
        """
        Method to read all parameter values from the instrument and
        updating them in the interface.
        """
        for name in self.measurements:
            if hasattr(self.instrument, name):
                value = getattr(self.instrument, name)
                self.update_value(name, value)
        for name in self.settings:
            if hasattr(self.instrument, name):
                value = getattr(self.instrument, name)
                self.update_value(name, value)
        for name in self.options:
            if hasattr(self.instrument, name):
                value = getattr(self.instrument, name)
                self.update_value(name, value)
        for name in self.controls:
            if hasattr(self.instrument, name):
                value = getattr(self.instrument, name)
                self.update_value(name, value)

    def apply_setting(self, name):
        """
        Apply a setting change of the instrument
        :param name Name of the setting attribute of the instrument
        """
        element = getattr(self, name)
        setattr(self.instrument, name, element.value())

    def apply_all_settings(self):
        """
        Apply all implemented settings by looping through all controls and
        settings and calling `apply_setting`
        """
        for name in self.controls:
            if hasattr(self.instrument, name):
                self.apply_setting(name)

        for name in self.settings:
            if hasattr(self.instrument, name):
                self.apply_setting(name)

    def _auto_settings_changed(self):
        self.auto_read = self.auto_read_box.isChecked()
        self.auto_write = self.auto_write_box.isChecked()
        self.read_button.setEnabled(not self.auto_read)
        self.write_button.setEnabled(not self.auto_write)

        self.update_thread.stop()
        self.update_thread.join()

        if self.auto_read:
            self.update_thread.start()

    def input_from_parameter(self, parameter):
        """Get the corresponding type of input for a given parameter.
        :param parameter: A parameter
        """
        if parameter.ui_class is not None:
            element = parameter.ui_class(parameter)

        elif isinstance(parameter, parameters.FloatParameter):
            element = ScientificInput(parameter)

        elif isinstance(parameter, parameters.IntegerParameter):
            element = IntegerInput(parameter)

        elif isinstance(parameter, parameters.BooleanParameter):
            element = BooleanInput(parameter)

        elif isinstance(parameter, parameters.ListParameter):
            element = ListInput(parameter)

        elif isinstance(parameter, parameters.Parameter):
            element = StringInput(parameter)

        else:
            raise TypeError(
                "parameter has to be an instance of Parameter or one "
                "of its subclasses."
            )

        return element

    @staticmethod
    def check_parameter_list(parameter_list, field_type=None):
        """
        Convert all elements of a list to valid `Parameters` or a subclass by either
        checking for an attribute of the instrument with a given name or
        checking the validity of a given parameter.

        :param parameter_list A list of strings, `Parameters` or `Parameter` subclasses
        :param field_type optional argument for options which require the parameter to be Boolean
        """
        # Ensure the parameters is a list
        if isinstance(parameter_list, (list, tuple)):
            parameter_list = list(parameter_list)
        elif parameter_list is None:
            parameter_list = []
        else:
            parameter_list = [parameter_list]

        for idx, param in enumerate(parameter_list):
            if isinstance(param, parameters.Parameter):
                pass
            # If a string is given, a float parameter is assumed
            elif isinstance(param, str):
                parameter_list[idx] = parameters.FloatParameter(param)
            else:
                raise TypeError(
                    "All parameters should be given as a Parameter, a \
                    Parameter subclass, or a string."
                )
            parameter_list[idx].field_type = field_type

        # if field_type == "option":
        #     # Convert all elements to BooleanParameters if given as a string
        #     for idx in range(len(parameter_list)):
        #         if isinstance(parameter_list[idx], parameters.BooleanParameter):
        #             pass
        #         elif isinstance(parameter_list[idx], str):
        #             parameter_list[idx] = parameters.BooleanParameter(parameter_list[idx])
        #         else:
        #             raise TypeError(
        #                 "All parameters (measurements, controls, & "
        #                 "settings) should be given as a BooleanParameter or a string."
        #             )
        #         parameter_list[idx].field_type = field_type

        # else:
        #     # Convert all elements to FloatParameter whenever given as
        #     # a string for everything but options
        #     for idx in range(len(parameter_list)):
        #         if isinstance(parameter_list[idx], parameters.Parameter):
        #             pass
        #         elif isinstance(parameter_list[idx], str):
        #             parameter_list[idx] = parameters.FloatParameter(parameter_list[idx])
        #         else:
        #             raise TypeError(
        #                 "All parameters (measurements, controls, & "
        #                 "settings) should be given as a Parameter, a "
        #                 "Parameter subclass, or a string."
        #             )

        #         parameter_list[idx].field_type = field_type

        params = OrderedDict((param.name, param) for param in parameter_list)

        return params
