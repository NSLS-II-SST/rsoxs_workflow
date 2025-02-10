

## This file is intended to contain all default and frequently used instrument configurations instead of having them in rsoxs package
## The plan is to have a single dictionary with each key being the name of the configuration, and the values can be dictionaries of motor names, positions, and order to move.
## TODO: see how motor positions from spreadsheet are used to move to sample location, and follow that workflow for configurations.  I am entering things in that format, but I don't fully understand how to retrieve it just yet.
## TODO: I want to set it up so that when I feed these into rsoxs, I can have a function that moves the motors.  And then a separate function (viewPositions()) that prints the setpoint and readback values so that I can check that I have reached the desired positions.

configurations = {}


configurations["mirrorsRSoXS"] = [
  {"motor": "mir1.x", "position": -0.55, "order": 0}, ## Unsure how to store mir1.x and similar variable locally but I have an example below
  {"motor": "mir1.y", "position": -18, "order": 0},
  {"motor": "mir1.z", "position": 0, "order": 0},
  {"motor": "mir1.pitch", "position": 0.45, "order": 0}, 
  {"motor": "mir1.roll", "position": 0, "order": 0},
  {"motor": "mir1.yaw", "position": 0, "order": 0},

  {"motor": "mir3.x", "position": 22.1, "order": 0}, 
  {"motor": "mir3.y", "position": 18, "order": 0},
  {"motor": "mir3.z", "position": 0, "order": 0},
  {"motor": "mir3.pitch", "position": 7.93, "order": 0}, 
  {"motor": "mir3.roll", "position": 0, "order": 0},
  {"motor": "mir3.yaw", "position": 0, "order": 0},
]



"""
## Possible way/example in rsoxs package to convert device names into strings and then check if they are equal to the motor name above
import inspect

def get_var_name(var):
    ## Gets the name of a variable.
    ## Args: 
      ## var: The variable whose name you want to get.
    ## Returns:  The name of the variable as a string, or None if the name cannot be determined.

    for frame in inspect.stack():
        for key, value in frame.f_locals.items():
            if value is var:
                return key
    return None

x = 5
var_name = get_var_name(x) 
print(var_name)  # Output: 'x' 
"""
