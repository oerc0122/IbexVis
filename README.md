# IbexVis
Visualiser for IBEX runs

## Installation

Run
```
pip install .
```
from the root `ibex_vis` folder.

## Usage


### Through Python

With IbexVis installed, simply run:

```python
from pathlib import Path

from ibex_vis.vis import main

main(
    input_scripts=Path("/path/to/script.py"),
    parameters=Path("/path/to/config.json"),
)
```

### Through CLI (with installation)

With IbexVis installed, it provides a script called `ibex_vis` which can be run.

```
ibex_vis -h
```

The script requires a configuration file in `json` format to define the properties of the simulation.

IbexVis can then be run as:

```
ibex_vis -c path/to/config.json path/to/script.py
```

Which should render a plot of the predicted run.

### Through CLI (without installation)

Without installing IbexVis simply run

```
python -m ibex_vis -c path/to/config.json path/to/script.py
```
from the folder containing the `ibex_vis` directory.

## JSON Schema

The `config.json` file follows a particular schema mapping `genie` properties to virtual trackers.

```json
{
    "<property>": {
         "initial": 100.0,      // Initial value (default: 0.0)
         "rate": 1.0,           // Set rate up/down simultaneously to val, -val
         "rate": [1.0, -2.0],   // Set rate up/down simultaneously
         "rate_up": 1.0,        // Set rate up/down separately
         "rate_down": -2.0,     // Set rate up/down separately
         "units": "K",          // Units to use if sole display property (default: "")
         "always_advance": true // Whether the property always advances even if no target is set.
    }
}
```
Only one of `rate` or (`rate_up` and `rate_down`) may be provided.
