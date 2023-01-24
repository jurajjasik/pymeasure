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

import os
import platform
import subprocess

import pyqtgraph as pg

from ..browser import BrowserItem
from ..manager import Manager, Experiment
from ..Qt import QtCore, QtWidgets
from ..widgets import (
    PlotWidget,
    BrowserWidget,
    InputsWidget,
    LogWidget,
    ResultsDialog,
    SequencerWidget,
    DirectoryLineEdit,
    EstimatorWidget,
    InstrumentControlWidget,
)
from ..thread import InstrumentThread, StoppableQThread
from ...experiment import Results, Procedure
from ..curves import ResultsCurve

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class InstrumentControlWindow(QtWidgets.QMainWindow):
    """
    Class for instrument control GUI.

    The InstrumentControlWindow provides an interface for controlling
    instruments. It allows the user to choose instrument attributes and
    automatically chooses the right widget type for its control.

    The user has to distinguish between read-only variables (measurements),
    write-only variables (settings), read/writable variables (settings for
    non-boolean variables, options for boolean variables), and functions.
    Alternatively to instrument attributes the user can provide
    :class:`~pymeasure.experiment.parameters.Parameter` instance variables.

    Parameters for :code:`__init__` constructor.

    :param instrument: Instrument instance which should be controlled
    :param measurements: List of measurement variables of the instrument
        (strings) and/or :class:`~pymeasure.experiment.parameters.Parameter` instance variables
    :param settings: List of setting variables of the instrument
        (strings) and/or :class:`~pymeasure.experiment.parameters.Parameter` instance variables
    :param controls: List of control variables of the instrument
        (strings) and/or :class:`~pymeasure.experiment.parameters.Parameter` instance variables
    :param functions: List of member functions of the instrument
    :param options: List of boolean variables of the instrument or
        :class:`~pymeasure.experiment.parameters.BooleanParameter`
    :param parent: Parent widget or :code:`None`
    """

    def __init__(
        self,
        instrument,
        measurements=None,
        settings=None,
        controls=None,
        functions=None,
        options=None,
        parent=None,
    ):
        super().__init__(parent)
        app = QtCore.QCoreApplication.instance()
        app.aboutToQuit.connect(self.quit)

        self.inst_widget = InstrumentControlWidget(
            instrument,
            measurements=measurements,
            settings=settings,
            controls=controls,
            functions=functions,
            options=options
        )

        self._setup_ui()
        self._layout()

    def _setup_ui(self):
        pass

    def _layout(self):
        self.main = QtWidgets.QWidget(self)

        self.layout = QtWidgets.QVBoxLayout(self.main)
        self.layout.addWidget(self.inst_widget, 0)
        self.main.setLayout(self.layout)
        self.setCentralWidget(self.main)
        self.main.show()

    def quit(self, evt=None):
        self.close()
