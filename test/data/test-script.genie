import numpy as np
from genie_python import genie as g
import inst

def runscript():
    for tt in [150, 300]:
        g.cset(T_head = tt, lowlimit = tt-5, highlimit = tt+5, runcontrol = True)
        g.begin()
        g.change_title(f'Some random sample - {tt}K')
        g.waitfor(uamps = 750)
        g.end()
