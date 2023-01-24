"""
This example demonstrates how to make a graphical interface, and uses
a random number generator to simulate data so that it does not require
an instrument to use. It also demonstrates the use of the sequencer module.

Run the program by changing to the directory containing this file and calling:

python gui_sequencer.py

"""

import logging
import sys

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import InstrumentControlWindow
from pymeasure.experiment import BooleanParameter, ListParameter
from pymeasure.instruments.mock import Mock as MockInstrument

import numpy as np

log = logging.getLogger("")
log.addHandler(logging.NullHandler())

bpar = BooleanParameter("Ext. Boolean", default=False)
listpar = ListParameter('Choice', choices=['A', 'B', 'C', 'D'], default='A')


def print_random_number():
    print(np.random.rand())


class MockInstrumentControlWindow(InstrumentControlWindow):
    def __init__(self):
        super().__init__(
            MockInstrument(),
            measurements=["wave", "voltage"],
            controls=["time"],
            settings=["output_voltage", listpar],
            options=[bpar, 'running'],
            functions=[print_random_number, 'start', 'stop']
        )
        self.setWindowTitle("Instrument Control")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MockInstrumentControlWindow()
    window.show()
    sys.exit(app.exec_())
