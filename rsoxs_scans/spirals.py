"""Does the Spirals #TODO Docs

"""

# imports
from copy import deepcopy
from .defaults import *


def spiral_scan_enqueue(
    diameter=default_diameter,
    stepsize=default_spiral_step,
    energy=270,
    pol=0,
    angle=None,
    exposure=1,
    grating="rsoxs",
    md=None,
    dets=None,
    plan_name='spiral',
    **kwargs,
):

    valid = True
    validation = ""
    if md == None:
        md = []
    if grating in ["1200", 1200]:
        if energy < 150:
            valid = False
            validation += "energy is to low for the 1200 l/mm grating\n"
    elif grating in ["250", 250]:
        if energy > 1300:
            valid = False
            validation += "energy is too high for 250 l/mm grating\n"
    elif grating == "rsoxs":
        if energy > 1300:
            valid = False
            validation += "energy is too high for 250 l/mm grating\n"
    else:
        valid = False
        validation += "invalid grating was chosen"
    if dets is None:
        if "RSoXS_Main_DET" in md:
            if md["RSoXS_Main_DET"] == "waxs_det":
                dets = ["waxs_det"]
            else:
                dets = ["saxs_det"]
        else:
            valid = False
            validation += "No metadata was passed with detector information\n"
    for det in dets:
        if det not in ["saxs_det", "waxs_det"]:
            valid = False
            validation += f"invalid detector {det} is given\n"
    if len(dets) < 1:
        valid = False
        validation += "No detectors are given\n"
    if isinstance(angle,(float,int)):
        if -155 > angle or angle > 195:
            valid = False
            validation += f"angle of {angle} is out of range\n"
    if valid:
        retstr = f"\nspiral scanning {dets} at {energy} eV \n"
        retstr += f"    with a diameter of {diameter} mm  and stepsize of {stepsize} mm\n"
        retstr += f'    at grating {grating}\n'
        kwargs["dets"] = dets
        kwargs["energy"] = energy
        kwargs["diameter"] = diameter
        kwargs["stepsize"] = stepsize
        kwargs["grating"] = grating
        kwargs["angle"] = angle
        kwargs["pol"] = pol
        kwargs["exposure"] = exposure
        kwargs["enscan_type"] = plan_name
        kwargs['md'] = md
        return {"description": retstr, "action": "spiral_scan_core", "kwargs": kwargs}
    else:
        return {
            "description": f"\n\n\n\n_______________ERROR_____________________\n\n\n\n{validation}\n\n\n\n",
            "action": "error",
        }


def dryrun_spiral_plan(
    edge=270,
    diameter=default_diameter,
    spiral_step=default_spiral_step,
    exposure_time=default_exposure_time,
    polarizations=[0],
    angles=None,
    grating="rsoxs",
    diode_range="high",
    md=None,
    dets=None,
    **kwargs,
):
    valid = True
    valid_text = ""
    if not isinstance(edge, (float, int)):
        if isinstance(edge, list):
            if isinstance(edge[0], (float, int)):
                edge = edge[0]
                valid_text += f"\n\nWARNING only a single energy {edge} will be used for the spiral search"
    if not isinstance(edge, (float, int)):
        valid = False
        valid_text += (
            f'\n\nERROR a single energy should be entered in the "edge" column for spiral scans not {edge} '
        )

    if not isinstance(exposure_time, (int, float)):
        valid = False
        valid_text += f"\n\nERROR - invalid exposure time for spiral scans was given {exposure_time}\n\n"
    if edge > 1200 and grating == "rsoxs":
        valid = False
        valid_text += f"\n\nERROR - energy is not appropriate for this grating\n\n"
    if not valid:
        # don't go any further, even in simulation mode, because we know the inputs are wrong
        return {
            "description": f"\n\n\n\n_______________ERROR_____________________\n\n\n\n{valid_text}\n\n\n\n",
            "action": "error",
        }

    output = []
    # if valid, continue with other commands
    if diode_range == "high":
        output.append({"description": "set Diode range to high\n", "action": "diode_high"})
    elif diode_range == "low":
        output.append({"description": "set Diode range to low\n", "action": "diode_low"})
    if angles is None:
        angles = [None]
    for angle in angles:
        for pol in polarizations:
            output.append(
                spiral_scan_enqueue(
                    dets=dets,
                    diameter=diameter,
                    stepsize=spiral_step,
                    energy=edge,
                    pol=pol,
                    angle=angle,
                    grating=grating,
                    exposure=exposure_time,
                    md=md, # we need it to connect to the Run engine MD, which only happens if we DONT pass md down
                    plan_name=f"spiral_{edge}",
                    **kwargs
                )
            )
    return output
