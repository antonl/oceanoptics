from PyQt4 import QtGui
from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QMainWindow

from Queue import Queue
import threading

from ui_oceanoptics import Ui_MainWindow
from oceanoptics import USB4000

class Ui_USB4000(QMainWindow, Ui_MainWindow):
    def __init__(self, data_q):
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

    def update_spectrum(self):
            self.data = self.data_q.get()
            self.curve.setData(self.data[3:3650])

    def update_temp(self):
            data = self.temp_q.get()
            self.lcdNumber.setProperty('value', data)

    def change_integration_time(self):
        self.dev.set_integration_time(int(self.spinBox.value()*1e6))

    def close(self):
        self.dev.close()

    def show(self):
        self.temp_timer.start(1000)
        self.spectra_timer.start(100)
        super(QMainWindow, self).show()
        
    def closeEvent(self, event):
        super(QMainWindow, self).closeEvent(event)

class Usb4000Thread(threading.Thread):
    def __init__(self):
        self.dev = USB4000()

        self.data_q = Queue()
        self.temp_q = Queue()
        self.cmd_q = Queue()
        
        self.is_active = threading.Event()

    def run(self):
        while self.is_active.is_set():
            try:
                cmd, args = self.cmd_q.get()
                res = cmd(*args)
            except queue.Empty as e:
                time.sleep(10)

    def test(self):
        
        
# Try to create a worker thread that polls device
try:
    self.dev = USB4000()
except:
    raise RuntimeError('Could not initialize device')

app = QtGui.QApplication(sys.argv)

try:
    ex = Ui_USB4000()
    ex.show()
    sys.exit(app.exec_())
except RuntimeError as e:
    print e

