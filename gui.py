from PyQt4 import QtGui
from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QMainWindow

import time
import threading
import sys
from collections import deque

from ui_oceanoptics import Ui_MainWindow
from oceanoptics import USB4000

import logging

log = logging.getLogger('oceanoptics.gui')

log.setLevel(logging.INFO)

class Ui_USB4000(QMainWindow, Ui_MainWindow):
    def __init__(self):
        # Set up everything
        QMainWindow.__init__(self)

        self.setupUi(self)

        self.curve = self.graphicsView.plot(pen='g')
        
        self.graphicsView.setXRange(0, 3840)
        self.graphicsView.enableAutoRange(axis='y')

        self.spinBox.sigValueChanged.connect(self.change_integration_time)
        self.spinBox.setOpts(bounds=(10*1e-6, 6553500*1e-6), suffix='s', siPrefix=True, \
                dec=True, step=1)
        self.spinBox.setValue(0.001)
        
        self.spectra_timer = QTimer()
        self.spectra_timer.timeout.connect(self.update_spectrum)

        self.temp_timer = QTimer()
        self.temp_timer.timeout.connect(self.update_temp)
        
        self.worker = Usb4000Thread()

    def update_spectrum(self):
            self.data = self.worker.get_spectrum()

            if self.data != None:
                self.curve.setData(self.data[3:3650])

    def update_temp(self):
        '''
            data = self.temp_q.get()
            self.lcdNumber.setProperty('value', data)
        '''
        pass

    def change_integration_time(self):
        self.worker.set_integration_time(int(self.spinBox.value()*1e6))

    def close(self):
        self.worker.join()

    def show(self):
        self.temp_timer.start(1000)
        self.spectra_timer.start(25)
        self.worker.start()
        super(QMainWindow, self).show()
        
    def closeEvent(self, event):
        super(QMainWindow, self).closeEvent(event)

class Usb4000Thread(threading.Thread):
    def __init__(self):
        super(Usb4000Thread, self).__init__()

        self.dev = USB4000()
        self.cmd_q = deque()

        self.data = None
        self.is_active = threading.Event()

    def get_spectrum(self):
        # add spectrum to queue
        self.cmd_q.append((self._spectrum, []))

        # and return a dataset
        return self.data
        
    def _spectrum(self):
        try:
            self.data = self.dev.request_spectra()
        except usb.USBError as e:
            log.error('could not request spectrum')
            log.error(repr(e))

    def set_integration_time(self, val):
        self.cmd_q.append((self._integration_time, [val]))

    def _integration_time(self, val):
        try:
            self.dev.set_integration_time(val)
        except Exception as e:
            log.error('could not set integration time')
            log.error(repr(e))

    def run(self):
        self.is_active.set()

        while self.is_active.is_set():
            try:
                cmd, args = self.cmd_q.pop()
                cmd(*args)
                log.info('executed command {}'.format(repr(cmd)))
            except IndexError:
                log.debug('empty queue')
                time.sleep(0.001)

    def join(self):
        self.is_active.clear()
        super(Usb4000Thread, self).join(self)

# Try to create a worker thread that polls device
app = QtGui.QApplication(sys.argv)

try:
    ex = Ui_USB4000()
    ex.show()
    sys.exit(app.exec_())
except RuntimeError as e:
    print e

