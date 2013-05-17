import numpy as np
from galry import *
from oceanoptics import USB4000

dev = USB4000()

dev.set_integration_time(50000)
int16 = np.dtype('<i2')

pix = np.arange(3840)

x = .1 * np.random.randn(3840)

p = plot(get_data(), constrain_navigation=True)

def get_data():
    a,b = dev.request_spectra()
    a = np.array(a, dtype=int16)
    b = np.array(b, dtype=int16)
    return np.concatenate([a,b])

def anim(fig, _):
    fig.set_data(x=get_data())


animate(anim, dt=0.125)

show()
