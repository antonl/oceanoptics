import time 
import threading
import sys
from collections import deque

from PySide import QtGui
from PySide.QtCore import QTimer
from PySide.QtGui import QMainWindow, QGroupBox, QWidget, QHBoxLayout, QFormLayout
import pyqtgraph as pg

from oceanoptics import USB4000
import logging

import numpy as np

np.seterr(divide='ignore')

log = logging.getLogger('oceanoptics.gui')

log.setLevel(logging.CRITICAL)

class SpectrometerWindow(QMainWindow):
    def __init__(self, parent=None):
        # Set up everything
        QMainWindow.__init__(self, parent)
        self.setWindowTitle("USB4000 Control")

        self.make_main_frame()

        self.spectra_timer = QTimer()
        self.spectra_timer.timeout.connect(self.update_spectrum)

        self.temp_timer = QTimer()
        self.temp_timer.timeout.connect(self.update_temp)

        self.worker = Usb4000Thread()
        self.wavelength_mapping = self.worker.dev.get_wavelength_mapping()

        self.curves = []         
        self.persistence_sb.valueChanged.connect(self.change_persistence)
        self.change_persistence()
        
        self.background = 1
        self.bg_min = 0

        self.use_background = False

        self.abs645 = pg.InfiniteLine(angle=90, movable=False)
        self.abs663 = pg.InfiniteLine(angle=90, movable=False)

        self.plot.addItem(self.abs645, ignoreBounds=True)
        self.plot.addItem(self.abs663, ignoreBounds=True)
        
        self.abs645.setPos(645)
        self.abs663.setPos(663)
        
        self.conc_deque = deque(maxlen=20)

    def make_main_frame(self):
        self.main_frame = QWidget()
        win = pg.GraphicsWindow()
        self.crosshair_lb = pg.LabelItem(justify='right')
        win.addItem(self.crosshair_lb) 
        self.plot = win.addPlot(row=1, col=0) 
        self.plot.showGrid(x=True, y=True)
        self.right_panel = QGroupBox("Spectrometer Settings")
        
        hbox = QHBoxLayout()
        for w in [win, self.right_panel]:
            hbox.addWidget(w)

        form = QFormLayout()
        
        self.integration_sb = pg.SpinBox(value=0.001, bounds=(10*1e-6, 6553500*1e-6), suffix='s', siPrefix=True, \
                dec=True, step=1)
        self.integration_sb.valueChanged.connect(self.change_integration_time)

        self.persistence_sb = QtGui.QSpinBox()
        self.persistence_sb.setValue(7)
        self.persistence_sb.setRange(1,10)
        self.persistence_sb.valueChanged.connect(self.change_persistence)

        self.take_background_btn = QtGui.QPushButton('Take background')
        self.take_background_btn.clicked.connect(self.on_take_background)
        self.conc_lb = pg.ValueLabel()

        self.spec_temp_lb = pg.ValueLabel()

        self.use_background_cb = QtGui.QCheckBox("enabled")
        self.use_background_cb.stateChanged.connect(self.on_use_background)

        form.addRow("Integration time", self.integration_sb)
        form.addRow("Persistence",  self.persistence_sb)
        
        form.addRow("Background", self.take_background_btn)
        form.addRow("Use background", self.use_background_cb)
        self.right_panel.setLayout(form)
        self.main_frame.setLayout(hbox)
        self.setCentralWidget(self.main_frame)

    def on_use_background(self):
        if self.use_background_cb.isChecked():
            self.spectra_timer.stop()
            self.spectra_timer.start(500)
            self.persistence_sb.setValue(1)
            self.change_persistence()
            self.use_background = True
        else:
            self.spectra_timer.stop()
            self.spectra_timer.start(25)
            self.use_background = False

    def process_spectrum(self, data):
        if self.use_background:
            res =  np.log10(self.background) - np.log10(np.array(data, dtype='float'))
            self.conc_deque.append((res[1455]*20.2 + res[1539]*8.02)*0.2)
            self.crosshair_lb.setText("<span style='font-size: 12pt'>Abs645=%0.3f, <span style='color: red'>Abs663=%0.3f</span>, <span style='color: green'>Conc=%0.3f</span>" % (res[1455],res[1539], np.mean(np.array(self.conc_deque)))) 
            return res
        else:
            return np.array(data, dtype='float')
    
    def update_spectrum(self):
        self.data_stack.append(self.worker.get_spectrum())

        for i in xrange(len(self.data_stack)):
            d = self.data_stack[i]   
            if d != None: 
                log.debug('plotting curve %d', i)
                if i == len(self.data_stack)-1:
                    self.curves[i].setPen(color=(0, 255, 0, 255))
                else:
                    self.curves[i].setPen(color=(0, 255, 0, 50))
                self.curves[i].setData(self.wavelength_mapping, self.process_spectrum(d))

    def update_temp(self):
        res = self.worker.get_temp()

        if res != None:
            self.spec_temp_lb.setText("value")

    def change_integration_time(self):
        self.worker.set_integration_time(int(self.integration_sb.value()*1e6))

    def change_persistence(self):
        self.spectra_timer.stop()
        log.info('persistence changed')
        # remove all curves
        for i in self.curves: self.plot.removeItem(i)

        self.curves = []
        # add new curves
        val = self.persistence_sb.value()

        for i in xrange(val): 
            log.info('added %d item', i)
            self.curves.append(self.plot.plot())

        self.data_stack = deque(maxlen=val)
        log.info('maxlen is %d', val)
        self.spectra_timer.start(25)
    
    def on_take_background(self):
        self.spectra_timer.stop()
        self.data_stack.clear()

        bg = self.worker.get_spectrum()
        self.bg_min = np.amin(bg)
        self.background = np.array(bg, dtype='float')
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
        #self.cmd_q.clear()
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
                time.sleep(0.05)

    def join(self):
        self.is_active.clear()

# Try to create a worker thread that polls device
app = QtGui.QApplication(sys.argv)

try:
    ex = SpectrometerWindow()
    ex.show()
    app.exec_()
except RuntimeError as e:
    print e

