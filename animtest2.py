
"""
This example demonstrates many of the 2D plotting capabilities
in pyqtgraph. All of the plots may be panned/scaled by dragging with 
the left/right mouse buttons. Right click on any plot to show a context menu.
"""

from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg

from oceanoptics import USB4000


dev = USB4000()

dev.set_integration_time(40000)

app = QtGui.QApplication([])

win = pg.GraphicsWindow(title="Basic plotting examples")
win.resize(1000,600)

win.setWindowTitle('USB4000 spectrometer')

plt = win.addPlot()

curve = plt.plot(pen='g')

def update():
    global curve
    
    data = dev.request_spectra()
    curve.setData(data)

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(25)

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()

    dev.close()
