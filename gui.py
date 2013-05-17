
from PyQt4 import QtGui
from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QMainWindow


from ui_oceanoptics import Ui_MainWindow
from oceanoptics import USB4000
import sys

class USB4000Dialog(QMainWindow, Ui_MainWindow):
    def __init__(self):
        # Set up everything
        QMainWindow.__init__(self)

        self.setupUi(self)

        self.curve = self.graphicsView.plot(pen='g')
        
        self.graphicsView.setXRange(0, 3840)
        self.graphicsView.enableAutoRange(axis='y')

        self.dev = USB4000()

        self.spinBox.sigValueChanged.connect(self.change_integration_time)
        self.spinBox.setOpts(bounds=(10*1e-6, 6553500*1e-6), suffix='s', siPrefix=True, \
                dec=True, step=1)
        self.spinBox.setValue(0.001)
        
        self.spectra_timer = QTimer()
        self.spectra_timer.timeout.connect(self.update_spectrum)

        self.temp_timer = QTimer()
        self.temp_timer.timeout.connect(self.update_temp)

    def show(self):
        self.temp_timer.start(1000)
        self.spectra_timer.start(25)
        super(QMainWindow, self).show()
        
    def update_spectrum(self):
        self.data = self.dev.request_spectra()
        self.curve.setData(self.data[3:])
        
    def update_temp(self):
        data = self.dev.read_temp()
        self.lcdNumber.setProperty('value', data)

    def change_integration_time(self):
        self.dev.set_integration_time(int(self.spinBox.value()*1e6))

    def closeEvent(self, event):
        self.dev.close()
        super(QMainWindow, self).closeEvent(event)

app = QtGui.QApplication(sys.argv)

ex = USB4000Dialog()
ex.show()
sys.exit(app.exec_())

