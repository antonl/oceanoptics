from PyQt4 import QtGui
from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QMainWindow, QColor
import pyqtgraph

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

        self.graphicsView.showGrid(x=True, y=True)
        self.graphicsView.setMenuEnabled(False)

        view = self.graphicsView.getViewBox()
        view.setMouseMode(pyqtgraph.ViewBox.PanMode)
        view.setRange(xRange=(0, 3660), padding=0)

        self.spinBox.setValue(0.001)
        self.spinBox.setOpts(bounds=(10*1e-6, 6553500*1e-6), suffix='s', siPrefix=True, \
                dec=True, step=1)

        self.spinBox.sigValueChanged.connect(self.change_integration_time)

        self.spectra_timer = QTimer()
        self.spectra_timer.timeout.connect(self.update_spectrum)

        self.temp_timer = QTimer()
        self.temp_timer.timeout.connect(self.update_temp)

        self.worker = Usb4000Thread()

        self.curves = []         
        self.change_persistence()
        self.persistenceBox.valueChanged.connect(self.change_persistence)

    def update_spectrum(self):
        self.data_stack.append(self.worker.get_spectrum())

        for i in xrange(len(self.data_stack)):
            d = self.data_stack[i]   
            if d != None: 
                log.debug('plotting curve %d', i)
                if i == len(self.data_stack)-1:
                    self.curves[i].setPen(color=(0, 255, 0))
                else:
                    self.curves[i].setPen(color=(0, (i+1)*self.alpha_inc, 0))
                self.curves[i].setData(d[3:3660])

    def update_temp(self):
        res = self.worker.get_temp()

        if res != None:
            self.lcdNumber.setProperty('value', res)

    def change_integration_time(self):
        self.worker.set_integration_time(int(self.spinBox.value()*1e6))

    def change_persistence(self):

        self.spectra_timer.stop()
        log.info('persistence changed')
        # remove all curves
        for i in self.curves: self.graphicsView.removeItem(i)

        self.curves = []
        # add new curves
        val = self.persistenceBox.value()
        alpha_inc = int(100/val)
        self.alpha_inc = alpha_inc
        log.info('alpha inc %d', alpha_inc)

        for i in xrange(val): 
            log.info('added %d item', i)
            self.curves.append(self.graphicsView.plot())

        self.data_stack = deque(maxlen=val)
        log.info('maxlen is %d', val)
        self.spectra_timer.start(25)

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
        self.cmd_q = deque(maxlen=100)

        self.data = None
        self.temp = None

        self.is_active = threading.Event()

    def get_spectrum(self):
        # add spectrum to queue
        self.cmd_q.append((self._spectrum, []))

        # and return a dataset
        return self.data
        
    def _spectrum(self):
        try:
            self.data = self.dev.request_spectra()
        except Exception as e:
            log.error('could not request spectrum')
            log.error(repr(e))

    def get_temp(self):
        self.cmd_q.clear()
        self.cmd_q.append((self._temp, []))
        
        return self.temp

    def _temp(self):
        self.temp = self.dev.read_temp()

    def set_integration_time(self, val):
        self.cmd_q.clear()
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
                cmd, args = self.cmd_q.popleft()
                cmd(*args)
                log.debug('executed command {}'.format(repr(cmd)))
            except IndexError:
                time.sleep(0.005)

    def join(self):
        self.is_active.clear()

# Try to create a worker thread that polls device
app = QtGui.QApplication(sys.argv)

try:
    ex = Ui_USB4000()
    ex.show()
    app.exec_()
except RuntimeError as e:
    print e

