#imports
import numpy as np
from copy import deepcopy
from .constructor import get_nexafs_scan_params

def NEXAFS_fly_scan_core_sim(
    scan_params,
    openshutter=False,
    pol=0,
    grating="best",
    enscan_type=None,
    master_plan=None,
    angle=None,
    cycles=0,
    locked = True,
    md=None,
    sim_mode=False,
    **kwargs #extraneous settings from higher level plans are ignored
):
    # grab locals
    if pol is None:
        pol = 0
    if md is None:
        md = {}
    arguments = dict(locals())
    del arguments["md"]  # no recursion here!
    if md is None:
        md = {}
    md.setdefault("plan_history", [])
    md["plan_history"].append(
        {"plan_name": "NEXAFS_fly_scan_core", "arguments": arguments}
    )
    md.update({"plan_name": enscan_type, "master_plan": master_plan})
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
    if grating in ["1200",1200]:
        if min(energies) < 150:
            valid = False
            validation += "energy is to low for the 1200 l/mm grating\n"
    elif grating in ["250",250]:
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
    if pol < -1 or pol > 180:
        valid = False
        validation += f"polarization of {pol} is not valid\n"
    if angle is not None:
        if -155 > angle or angle > 195:
            valid = False
            validation += f"angle of {angle} is out of range\n"
    retstr = ''
    if sim_mode:
        if valid:
            if angle is not None:
                retstr += f"\n setting sample angle to {angle}"
            if pol is not None:
                 retstr += f"\n setting polarization to {pol}"
            if grating is not None:
                 retstr += f"\n setting grating to {grating}"
            retstr += f"\n fly nexafs scanning from {np.min(energies)} eV to {np.max(energies)} eV on the {grating} l/mm grating\n"
            retstr += f"    at speeds from {np.min(speeds)} to {np.max(speeds)} ev/second\n"
            return retstr
        else:
            return f'\n\n\n\n_______________ERROR_____________________\n\n\n\n{validation}\n\n\n\n'
    if not valid:
        raise ValueError(validation)



def epu_angle_from_grazing(real_incident_angle, grazing_angle=20):
    return (
        np.arccos(
            np.cos(real_incident_angle * np.pi / 180)
            * 1
            / (np.cos(grazing_angle * np.pi / 180))
        )
        * 180
        / np.pi
    )



def dryrun_nexafs_plan(edge, speed='normal', ratios=None, cycles=0, pol_mode="sample", polarizations = [0],
                       angles = None,grating='rsoxs',diode_range='high',temperatures=None,temp_ramp_speed=10,temp_wait=True, md = None, **kwargs):
    # nexafs plan is a bit like rsoxs plan, in that it comprises a full experiment however each invdividual energy scan is going to be its own run (as it has been in the past)  this will make analysis much easier
    sim_mode=1
    valid = True
    valid_text = ""
    params, time = get_nexafs_scan_params(edge,speed,ratios,quiet=1)
    if not isinstance(params,list):
        valid = False
        valid_text = f'\n\nERROR - parameters from the given edge, speed, and speed_ratios are bad\n\n'
    if isinstance(temperatures,list):
        for temp in temperatures:
            if temp is not None:
                if not (0<temp<350):
                    valid = False
                    valid_text += f"\n\nERROR - temperature of {temp} is out of range\n\n"
                if temp_wait > 30:
                    valid = False
                    valid_text += f"\n\nERROR - temperature wait time of {temp_wait} minutes is too long\n\n"
                if 0.1 > temp_ramp_speed or temp_ramp_speed > 100:
                    valid = False
                    valid_text += f"\n\nERROR - temperature ramp speed of {temp_ramp_speed} is not valid\n\n"
    
    
    if isinstance(temperatures,list) and not sim_mode:
        if(sim_mode):
            valid_text += f'setting the temperature ramp rate to{temp_ramp_speed}\n'
        else:
            ...
            #yield from bps.mv(tem_tempstage.ramp_rate,temp_ramp_speed)
    else:
        temperatures = [None]
    if not isinstance(angles,list):
        angles = [None]
    if not isinstance(polarizations,list):
        polarizations = [0]
    if diode_range=='high':
        if(sim_mode):
            valid_text += 'set Diode range to high\n'
        else:
            ...
            #NON-SIM #yield from setup_diode_i400()
    elif diode_range=='low':
        if(sim_mode):
            valid_text += 'set Diode range to low\n'
        else:
            ...
            #NON-SIM #yield from High_Gain_diode_i400() 
    if not valid:
        # don't go any further, even in simulation mode, because we know the inputs are wrong
        if not sim_mode:
            ...
            #NON-SIM #raise ValueError(valid_text)
        else:
            ...
            return valid_text
        # if we are still valid - try to continue
    
    if isinstance(temperatures,list):
        for temp in temperatures:
            if temp_wait and temp is not None:
                if sim_mode:
                    valid_text += f'setting temperature stage to {temp} degrees and waiting\n'
                else:
                    ...
                   #NON-SIM # yield from bps.mv(tem_tempstage,temp)
            elif not sim_mode and temp is not None:
                if sim_mode:
                    valid_text += f'setting temperature stage to {temp} degrees and continuing\n'
                else:
                    ...
                    #NON-SIM #yield from bps.mv(tem_tempstage.setpoint,temp)
            for grazing_angle in angles:
                for pol in polarizations:
                    if pol_mode == "sample":
                        if pol is not None and grazing_angle is not None:
                            if pol < grazing_angle:
                                valid = False
                                valid_text += "\n\nERROR - sample frame polarization less than grazing angle is not possible\n\n"
                                if not sim_mode:
                                    print('\n\nERROR - sample frame polarization less than grazing angle is not possible\n\n Skipping this scan')
                                    next
                            orig_pol = pol
                            pol=epu_angle_from_grazing(pol, grazing_angle)
                            valid_text += f'calculating a lab-frame polarization of {pol} from the sample_frame polarization \n  input of {orig_pol} and a sample angle {grazing_angle}\n'
                    valid_text += NEXAFS_fly_scan_core_sim( #NON-SIM #yield from NEXAFS_fly_scan_core
                                        scan_params=params,
                                        cycles=cycles,
                                        openshutter=True,
                                        pol=pol,
                                        angle=grazing_angle,
                                        grating=grating,
                                        sim_mode=True,
                                        md=md,)
    
    return valid_text