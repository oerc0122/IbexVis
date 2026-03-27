from genie_python import genie as g

class MyInstrument:
    def __init__(self):
        g.cset(dilfridge=77)
