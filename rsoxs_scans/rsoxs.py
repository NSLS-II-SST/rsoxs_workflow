# imports
import numpy as np
from copy import deepcopy
from .constructor import get_energies, construct_exposure_times

# code for finding a rotated position of a sample - needed to test locations
def rotate_sample(samp, force=False):
    """
    rotate a sample position to the requested theta position
    the requested sample position is set in the angle metadata (sample['angle'])
    """
    sanatize_angle(samp, force)  # makes sure the requested angle is translated into a real angle for acquisition
    theta_new = samp["bar_loc"]["th"]
    x0 = samp["bar_loc"]["x0"]
    y0 = samp["bar_loc"]["y0"]
    xoff = samp["bar_loc"]["xoff"]
    zoff = samp["bar_loc"]["zoff"]

    newx = rotatedx(x0, theta_new, zoff, xoff=xoff)
    xwritten = False
    ywritten = False
    thwritten = False
    for motor in samp["location"]:
        if motor["motor"] == "x":
            motor["position"] = newx
            xwritten = True
        if motor["motor"] == "th":
            motor["position"] = theta_new
            thwritten = True
        if motor["motor"] == "y":
            motor["position"] = y0
            ywritten = True
    if not xwritten:
        samp["location"].append({"motor": "x", "position": newx})
    if not ywritten:
        samp["location"].append({"motor": "y", "position": y0})
    if not thwritten:
        samp["location"].append({"motor": "th", "position": theta_new})


def rotatedx(x0, theta, zoff, xoff=1.88, thoff=1.6):
    """
    given the x position at 0 rotation (from the image of the sample bar)
    and a rotation angle, the offset of rotation in z and x (as well as a potential theta offset)
    find the correct x position to move to at a different rotation angle
    """
    return float(
        xoff + (x0 - xoff) * np.cos((theta - thoff) * np.pi / 180) - zoff * np.sin((theta - thoff) * np.pi / 180)
    )


def sanatize_angle(samp, force=False):
    # translates a requested angle (something in sample['angle']) into an actual angle depending on the kind of sample
    if type(samp["angle"]) == int or type(samp["angle"]) == float:
        goodnumber = True  # make the number fall in the necessary range
    else:
        goodnumber = False  # make all transmission 90 degrees from the back, and all grading 20 deg
    if force and -155 < samp["angle"] < 195:
        samp["bar_loc"]["th"] = samp["angle"]
        return
    if samp["grazing"]:
        # the sample is intended for grazing incidence, so angles should be interpreted to mean
        # 0 - parallel with the face of the sample
        # 90 - normal to the sample
        # 110 - 20 degrees from normal in one direction
        # 70 - 20 degrees from normal in the other direction
        # valid input angles are 0 - 180
        if samp["front"]:
            # sample is on the front of the bar, so valid outputs are between -90 and 90
            if goodnumber:
                samp["bar_loc"]["th"] = float(90 - np.mod(samp["angle"] + 3600, 180))
            else:
                samp["bar_loc"]["th"] = 70  # default grazing incidence samples to 20 degrees incidence angle
                samp["angle"] = 70
                # front grazing sample angle is interpreted as grazing angle
        else:
            if goodnumber:
                angle = float(np.mod(435 - np.mod(-samp["angle"] + 3600, 180), 360) - 165)
                if angle < -155:
                    angle = float(np.mod(435 - np.mod(samp["angle"] + 3600, 180), 360) - 165)
                samp["bar_loc"]["th"] = angle
            else:
                samp["bar_loc"]["th"] = 110
                samp["angle"] = 110
            # back grazing sample angle is interpreted as grazing angle but subtracted from 180
    else:
        if samp["front"]:
            if goodnumber:
                samp["bar_loc"]["th"] = float(np.mod(345 - np.mod(90 + samp["angle"] + 3600, 180) + 90, 360) - 165)
                if samp["bar_loc"]["x0"] < -1.8 and np.abs(samp["angle"]) > 30:
                    # transmission from the left side of the bar at a incident angle more than 20 degrees,
                    # flip sample around to come from the other side - this can take a minute or two
                    samp["bar_loc"]["th"] = float(
                        np.mod(345 - np.mod(90 - samp["angle"] + 3600, 180) + 90, 360) - 165
                    )
                if samp["bar_loc"]["th"] >= 195:
                    samp["bar_loc"]["th"] = 180
                if samp["bar_loc"]["th"] <= -155:
                    samp["bar_loc"]["th"] = -150
            else:
                samp["bar_loc"]["th"] = 180
                samp["angle"] = 180
        else:
            if goodnumber:
                samp["bar_loc"]["th"] = float(np.mod(90 + samp["angle"] + 3600, 180) - 90)
                if samp["bar_loc"]["x0"] > -1.8 and np.abs(samp["angle"]) > 30:
                    # transmission from the right side of the bar at a incident angle more than 20 degrees,
                    # flip to come from the left side
                    samp["bar_loc"]["th"] = float(np.mod(90 - samp["angle"] + 3600, 180) - 90)
            else:
                samp["bar_loc"]["th"] = 0
                samp["angle"] = 0

    if samp["bar_loc"]["th"] >= 195:
        samp["bar_loc"]["th"] = 195
    if samp["bar_loc"]["th"] <= -155:
        samp["bar_loc"]["th"] = -155


def rsoxs_scan_enqueue(
    # this function is very different as it touches a ton of hardware throughout, so I've just taken the validation parts from it here
    dets=None,  # a list of detectors to run at each step - get from md by default
    grating="no change",  # what grating to use for this scan
    energies=None,  # a list of energies to run through in the inner loop
    times=None,  # exposure times for each energy (same length as energies) (cycler add to energies)
    repeats=1,
    polarizations=None,  # polarizations to run as an outer loop (cycler multiply with previous)
    locations=None,  # locations to run together as an outer loop  (cycler multiply with previous) list of location dicts
    temperatures=None,  # locations to run as an outer loop  (cycler multiply with previous generally, but optionally add to locations - see next)
    temps_with_locations=False,  # indicates to move locations and temperatures at the same time, not multiplying exposures (they must be the same length!)
    plan_name="rsoxs",
    md=None,
    **kwargs,  # extraneous settings from higher level plans are just passed along
):
    if md is None:
        md = {}
    if dets is None:
        if md["RSoXS_Main_DET"] == "waxs_det":
            dets = ["waxs_det"]
        else:
            dets = ["saxs_det"]
    if energies is None:
        energies = []
    if times is None:
        times = []
    if polarizations is None:
        polarizations = []
    if locations is None:
        locations = []

    # validate inputs
    valid = True
    validation = ""
    for det in dets:
        if det == None:
            if "RSoXS_Main_DET" in md:
                if md["RSoXS_Main_DET"] == "waxs_det":
                    dets = ["waxs_det"]
                else:
                    dets = ["saxs_det"]
            else:
                valid = False
                validation += "No metadata was passed with detector information\n"
    if len(dets) < 1:
        valid = False
        validation += "No detectors are given\n"
    newdets = dets
    detnames = dets
    repeats = int(repeats)
    if not 0 < repeats < 100:
        valid = False
        validation += "repeats must be a positive integer between 0 and 100\n"
    if min(energies) < 70 or max(energies) > 2200:
        valid = False
        validation += "energy input is out of range for SST 1\n"
    if grating in ["1200", 1200]:
        if min(energies) < 150:
            valid = False
            validation += "energy is to low for the 1200 l/mm grating\n"
    elif grating in ["250", 250]:
        if max(energies) > 1000:
            valid = False
            validation += "energy is too high for 250 l/mm grating\n"
    elif grating == "rsoxs":
        if max(energies) > 1000:
            valid = False
            validation += "energy is too high for 250 l/mm grating\n"
    else:
        valid = False
        validation += "invalid grating was chosen"
    if np.max(times) > 10:
        valid = False
        validation += "exposure times greater than 10 seconds are not valid\n"
    if min(polarizations) < -1 or max(polarizations) > 180:
        valid = False
        validation += f"a provided polarization is not valid\n"
    if temperatures is not None:
        if min(temperatures, default=35) < 20 or max(temperatures, default=35) > 300:
            valid = False
            validation += f"temperature out of range\n"
    motor_positions = []
    angles = None
    xs = None
    ys = None
    zs = None
    temzs = None
    if len(locations) > 0:
        motor_positions = [{d["motor"]: d["position"] for d in location} for location in locations]
        angles = {d.get("th", None) for d in motor_positions}
        angles.discard(None)
        xs = {d.get("x", None) for d in motor_positions}
        xs.discard(None)
        if min(xs, default=0) < -13 or max(xs, default=0) > 13:
            valid = False
            validation += f"X motor is out of vaild range\n"
        ys = {d.get("y", None) for d in motor_positions}
        ys.discard(None)
        if min(ys, default=0) < -190 or max(ys, default=0) > 355:
            valid = False
            validation += f"Y motor is out of vaild range\n"
        zs = {d.get("z", None) for d in motor_positions}
        zs.discard(None)
        if min(zs, default=0) < -13 or max(zs, default=0) > 13:
            valid = False
            validation += f"Z motor is out of vaild range\n"
        # temxs = {d.get('temx', None) for d in motor_positions}
        # temxs.discard(None)
        # if min(xs) < -13 or max(xs) > 13:
        #     valid = False
        #     validation += f"X motor is out of vaild range\n"
        # temys = {d.get('temy', None) for d in motor_positions}
        # temys.discard(None)
        # if min(xs) < -13 or max(xs) > 13:
        #     valid = False
        #     validation += f"X motor is out of vaild range\n"
        temzs = {d.get("temz", None) for d in motor_positions}
        temzs.discard(None)
        if min(temzs, default=0) < 0 or max(temzs, default=0) > 150:
            valid = False
            validation += f"TEMz motor is out of vaild range\n"
        if max(temzs, default=0) > 100 and min(ys, default=50) < 20:
            valid = False
            validation += f"potential clash between TEY and sample bar\n"
    if temps_with_locations:
        if len(temperatures) != len(locations):
            valid = False
            validation += f"temperatures and locations are different lengths, cannot be simultaneously changed\n"
    retstr = ""
    if valid:
        if len(polarizations) > 1:
            retstr += f"\n setting {len(polarizations)} polarizations from {np.min(polarizations)} to {np.max(polarizations)}"
            kwargs["polarizations"] = polarizations
        elif len(polarizations):
            retstr += f"\n setting polarization to {polarizations[0]}"
            kwargs["polarizations"] = polarizations
        if angles is not None:
            kwargs["locations"] = locations
            kwargs["temps_with_locations"] = temps_with_locations
            if len(angles) > 1:
                retstr += (
                    f"\n setting {len(list(angles))} angles from {np.min(list(angles))} to {np.max(list(angles))}"
                )
                retstr += f", x from {np.min(list(xs))} to {np.max(list(xs))}"
                retstr += f", y from {np.min(list(ys))} to {np.max(list(ys))}"
                if len(zs):
                    retstr += f", z from {np.min(list(zs))} to {np.max(list(zs))}"
                if len(temzs):
                    retstr += f", TEMz from {np.min(list(temzs))} to {np.max(list(temzs))}"
            else:
                retstr += f"\n setting angle to {angles}"
                retstr += f", x to {xs}"
                retstr += f", y to {ys}"
                if len(zs):
                    retstr += f", z to {zs}"
                if len(temzs):
                    retstr += f", and TEMz to {temzs}"
        if temperatures is not None:
            if len(temperatures) > 1:
                retstr += f"\n setting {len(temperatures)} temperatures from {np.min(temperatures)} to {np.max(temperatures)}"
                kwargs["temperatures"] = temperatures
            elif len(temperatures):
                retstr += f"\n setting temperature to {temperatures}"
                kwargs["temperatures"] = temperatures
        retstr += f"\n RSoXS scanning {detnames} from {np.min(energies)} eV to {np.max(energies)} eV on the {grating} l/mm grating\n"
        retstr += (
            f"    in {len(times)} steps with exposure times from {np.min(times)} to {np.max(times)} seconds\n"
        )
        kwargs["times"] = times
        kwargs["dets"] = detnames
        kwargs["energies"] = energies
        kwargs["grating"] = grating
        kwargs["md"] = md
        kwargs["enscan_type"] = plan_name
        if repeats > 1:
            retstr += f"    repeating each exposure {repeats} times\n"
            kwargs["repeats"] = repeats
        return {"description": retstr, "action": "rsoxs_scan_core", "kwargs": kwargs}
    else:
        return {
            "description": f"\n\n\n\n_______________ERROR_____________________\n\n\n\n{validation}\n\n\n\n",
            "action": "error",
        }


def dryrun_rsoxs_plan(
    edge,
    exposure_time=1,
    frames="full",
    ratios=None,
    repeats=1,
    polarizations=[0],
    angles=None,
    grating="rsoxs",
    diode_range="high",
    temperatures=None,
    temp_ramp_speed=10,
    temp_wait=True,
    md=None,
    **kwargs,
):
    energies = get_energies(edge, frames, ratios, quiet=True)
    times, time = construct_exposure_times(energies, exposure_time, repeats, quiet=True)
    outputs = []

    # actually set things up
    if isinstance(temperatures, list):
        outputs.append(
            {
                "description": f"setting the temperature ramp rate to{temp_ramp_speed}\n",
                "action": "move",
                "kwargs": {"motor": "temp_ramp_rate", "position": temp_ramp_speed},
            }
        )
    else:
        temperatures = None
    if diode_range == "high":
        outputs.append({"description": "set Diode range to high\n", "action": "diode_high"})
    elif diode_range == "low":
        outputs.append({"description": "set Diode range to low\n", "action": "diode_low"})

    # construct the locations list
    locations = []
    if isinstance(angles, list):
        for angle in angles:
            md["angle"] = angle
            md["bar_loc"]["x0"] = md["bar_loc"].get(
                "x0", 0
            )  # need to initialize these locations for the dry run...
            md["bar_loc"]["y0"] = md["bar_loc"].get("y0", 0)
            md["bar_loc"]["xoff"] = md["bar_loc"].get("xoff", 0)
            md["bar_loc"]["zoff"] = md["bar_loc"].get("zoff", 0)

            rotate_sample(
                md
            )  # doesn't rotate the actual sample yet, just does the math to update the location of the sample
            locations += [deepcopy(md["location"])]  # read that rotated location as a location for the acquisition
    outputs.append(
        rsoxs_scan_enqueue(
            grating=grating,
            energies=energies,
            times=times,
            repeats=repeats,
            polarizations=polarizations,
            locations=locations,
            temperatures=temperatures,
            temp_wait=temp_wait,
            md=md,
            plan_name=f"rsoxs_{edge}",
        )
    )
    return outputs
