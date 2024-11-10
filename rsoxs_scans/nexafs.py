"""Does the NEXAFS #TODO Docs

"""

# imports
import numpy as np
from copy import deepcopy
from .constructor import get_nexafs_scan_params, get_energies, construct_exposure_times_nexafs
from .rsoxs import rotate_sample, rotatedx, sanitize_angle

def nexafs_scan_enqueue(
    scan_params,
    cycles=0,
    pol=0,
    grating="best",
    angle=None,
    plan_name='nexafs',
    md=None,
    **kwargs,  # extraneous settings from higher level plans are ignored
):
    # grab locals
    if md is None:
        md={}
    if pol is None:
        pol = 0
    # validate inputs
    valid = True
    validation = ""
    energies = np.empty(0)
    speeds = []
    for scanparam in scan_params:
        (sten, enden, speed) = scanparam
        energies = np.append(energies, np.linspace(sten, enden, 10))
        speeds.append(speed)
    if len(energies) < 10:
        valid = False
        validation += f"scan parameters {scan_params} could not be parsed\n"
    if min(energies) < 70 or max(energies) > 2200:
        valid = False
        validation += "energy input is out of range for SST 1\n"
    if not isinstance(cycles, (int, float)):
        valid = False
        validation += f"invalid cycles input {cycles}\n"
    elif cycles < 0 or cycles > 1000:
        valid = False
        validation += f"invalid cycles number {cycles}\n"
    if grating in ["1200", 1200]:
        if min(energies) < 150:
            valid = False
            validation += "energy is to low for the 1200 l/mm grating\n"
    elif grating in ["250", 250]:
        if max(energies) > 1300:
            valid = False
            validation += "energy is too high for 250 l/mm grating\n"
    elif grating == "rsoxs":
        if max(energies) > 1300:
            valid = False
            validation += "energy is too high for 250 l/mm grating\n"
    else:
        valid = False
        validation += "invalid grating was chosen"
    if pol < -1 or pol > 180:
        valid = False
        validation += f"polarization of {pol} is not valid\n"
    if angle is not None:
        if -155 > angle or angle > 195:
            valid = False
            validation += f"angle of {angle} is out of range\n"
    retstr = ""
    if valid:
        if angle is not None:
            retstr += f"\n setting sample angle to {angle}"
        if pol is not None:
            retstr += f"\n setting polarization to {pol}"
        if grating is not None:
            retstr += f"\n setting grating to {grating}"
        retstr += f"\n fly nexafs scanning from {np.min(energies)} eV to {np.max(energies)} eV on the {grating} l/mm grating\n"
        retstr += f"    at speeds from {np.min(speeds)} to {np.max(speeds)} ev/second\n"
        if cycles:
            retstr += f"    cycling energy {cycles} times\n"

        kwargs["angle"] = angle
        kwargs["pol"] = pol
        kwargs["scan_params"] = scan_params
        kwargs["grating"] = grating
        kwargs["cycles"] = cycles
        kwargs["enscan_type"] = plan_name
        kwargs["md"] = md
        return {"description": retstr, "action": "nexafs_scan_core", "kwargs": kwargs}
    else:
        return {
            "description": f"\n\n\n\n_______________ERROR_____________________\n\n\n\n{validation}\n\n\n\n",
            "action": "error",
        }


def epu_angle_from_grazing(real_incident_angle, grazing_angle=20):
    return (
        np.arccos(np.cos(real_incident_angle * np.pi / 180) * 1 / (np.cos(grazing_angle * np.pi / 180)))
        * 180
        / np.pi
    )


def dryrun_nexafs_plan(
    edge,
    speed="normal",
    ratios=None,
    cycles=0,
    pol_mode="sample",
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
    # nexafs plan is a bit like rsoxs plan, in that it comprises a full experiment however each invdividual energy scan is going to be its own run (as it has been in the past)  this will make analysis much easier
    valid = True
    valid_text = ""
    outputs = []
    params, time = get_nexafs_scan_params(edge, speed, ratios, quiet=True)
    if not isinstance(params, list):
        valid = False
        valid_text = f"\n\nERROR - parameters from the given edge, speed, and speed_ratios are bad\n\n"
    if isinstance(temperatures, list):
        for temp in temperatures:
            if temp is not None:
                if not (0 < temp < 350):
                    valid = False
                    valid_text += f"\n\nERROR - temperature of {temp} is out of range\n\n"
                if temp_wait > 30:
                    valid = False
                    valid_text += f"\n\nERROR - temperature wait time of {temp_wait} minutes is too long\n\n"
                if 0.1 > temp_ramp_speed or temp_ramp_speed > 100:
                    valid = False
                    valid_text += f"\n\nERROR - temperature ramp speed of {temp_ramp_speed} is not valid\n\n"

    if not isinstance(angles, (list, redis_json_dict.redis_json_dict.ObservableSequence)):
        angles = [None]
    if not isinstance(polarizations, (list, redis_json_dict.redis_json_dict.ObservableSequence)):
        polarizations = [0]
    if not valid:
        # don't go any further, because we know the inputs are wrong
        # raise ValueError(valid_text)
        return {"description": valid_text, "action": "error"}
    # if we are still valid - try to continue

    # actually move things
    if isinstance(temperatures, list):
        outputs.append(
            {
                "description": f"setting the temperature ramp rate to{temp_ramp_speed}\n",
                "action": "move",
                "kwargs": {"motor": "temp_ramp_rate", "position": temp_ramp_speed},
            }
        )
    else:
        temperatures = [None]
    if diode_range == "high":
        outputs.append({"description": "set Diode range to high\n", "action": "diode_high"})
    elif diode_range == "low":
        outputs.append({"description": "set Diode range to low\n", "action": "diode_low"})

    if isinstance(temperatures, list):
        for temp in temperatures:
            if temp_wait and temp is not None:
                outputs.append(
                    {
                        "description": f"setting temperature stage to {temp} degrees and waiting\n",
                        "action": "temp",
                        "kwargs": {"temp": temp, "wait": temp_wait},
                    }
                )
            elif temp is not None:
                outputs.append(
                    {
                        "description": f"setting temperature stage to {temp} degrees and continuing\n",
                        "action": "temp",
                        "kwargs": {"temp": temp, "wait": temp_wait},
                    }
                )
            for grazing_angle in angles:
                for pol in polarizations:
                    if pol_mode == "sample":
                        if pol is not None and grazing_angle is not None:
                            if pol < grazing_angle:
                                outputs.append(
                                    {
                                        "description": "\nwarning - sample frame polarization less than grazing angle is not possible\n\n Skipping this scan",
                                        "action": "warning",
                                    }
                                )
                                continue
                            orig_pol = pol
                            pol = epu_angle_from_grazing(pol, grazing_angle)
                            outputs.append(
                                {
                                    "description": f"\ncalculating a lab-frame polarization of {pol} from the sample_frame polarization \n  input of {orig_pol} and a sample angle {grazing_angle}\n",
                                    "action": "message",
                                }
                            )
                    outputs.append(
                        nexafs_scan_enqueue(
                            scan_params=params,
                            cycles=cycles,
                            pol=pol,
                            angle=grazing_angle,
                            grating=grating,
                            plan_name=f'nexafs_{edge}',
                            md=md,
                            **kwargs
                        )
                    )

    return outputs


def dryrun_nexafs_step_plan(
    edge,
    exposure_time=1,
    frames="full",
    ratios=None,
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
    times, time = construct_exposure_times_nexafs(energies, exposure_time, quiet=True)
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
    if isinstance(angles, (list, redis_json_dict.redis_json_dict.ObservableSequence)):
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
        nexafs_step_scan_enqueue(
            grating=grating,
            energies=energies,
            times=times,
            polarizations=polarizations,
            locations=locations,
            temperatures=temperatures,
            temp_wait=temp_wait,
            md=md,
            plan_name=f"rsoxs_{edge}",
            **kwargs
        )
    )
    return outputs


def nexafs_step_scan_enqueue(
    # this function is very different as it touches a ton of hardware throughout, so I've just taken the validation parts from it here
    dets=None,  # a list of detectors to run at each step - get from md by default
    grating="no change",  # what grating to use for this scan
    energies=None,  # a list of energies to run through in the inner loop
    times=None,  # exposure times for each energy (same length as energies) (cycler add to energies)
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
        dets = ['Beamstop_SAXS_int','Beamstop_WAXS_int', 'Izero_Mesh_int','Sample_TEY_int']
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
        if isinstance(det,str):
            if det not in ['Beamstop_SAXS_int','Beamstop_WAXS_int', 'Izero_Mesh_int','Sample_TEY_int']:
                validation +=f"Warning, unknown detector {det} given"
        else:
            valid= False
            validation +=f"Error, detector {det} given, cannot be parsed as a detector name"
    if len(dets) < 1:
        valid = False
        validation += "No detectors are given\n"
    detnames = dets
    if isinstance(energies,(float,int)):
        energies = [energies]
    if np.min(energies) < 70 or max(energies) > 2200:
        valid = False
        validation += "energy input is out of range for SST 1\n"
    if grating in ["1200", 1200]:
        if np.min(energies) < 150:
            valid = False
            validation += "energy is to low for the 1200 l/mm grating\n"
    elif grating in ["250", 250]:
        if np.max(energies) > 1300:
            valid = False
            validation += "energy is too high for 250 l/mm grating\n"
    elif grating == "rsoxs":
        if np.max(energies) > 1300:
            valid = False
            validation += "energy is too high for 250 l/mm grating\n"
    else:
        valid = False
        validation += "invalid grating was chosen"
    if np.max(times) > 10:
        valid = False
        validation += "exposure times greater than 10 seconds are not valid\n"
    if np.min(polarizations) < -1 or np.max(polarizations) > 180:
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
        retstr += f"\n NEXAFS scanning {detnames} from {np.min(energies)} eV to {np.max(energies)} eV on the {grating} l/mm grating\n"
        retstr += (
            f"    in {len(times)} steps with exposure times from {np.min(times)} to {np.max(times)} seconds\n"
        )
        kwargs["times"] = times
        kwargs["dets"] = detnames
        kwargs["energies"] = energies
        kwargs["grating"] = grating
        kwargs["md"] = md
        kwargs["enscan_type"] = plan_name
        return {"description": retstr, "action": "nexafs_step_scan_core", "kwargs": kwargs}
    else:
        return {
            "description": f"\n\n\n\n_______________ERROR_____________________\n\n\n\n{validation}\n\n\n\n",
            "action": "error",
        }
