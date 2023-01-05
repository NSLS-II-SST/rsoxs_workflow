#imports
from copy import deepcopy

def spiralsearch(
    diameter=default_diameter,
    stepsize=default_spiral_step,
    energy=270,
    pol=0,
    angle=None,
    exposure=1,
    master_plan=None,
    grating='rsoxs',
    sim_mode=True,
    md=None,
    dets=None
):

    valid = True
    validation = ""
    
    if grating in ["1200",1200]:
        if energy < 150:
            valid = False
            validation += "energy is to low for the 1200 l/mm grating\n"
    elif grating in ["250",250]:
        if energy > 1000:
            valid = False
            validation += "energy is too high for 250 l/mm grating\n"
    elif grating == "rsoxs":
        if energy > 1000:
            valid = False
            validation += "energy is too high for 250 l/mm grating\n"
    else:
        valid = False
        validation += "invalid grating was chosen"
    if dets is None:
        if md['RSoXS_Main_DET'] == 'waxs_det':
            dets = ['waxs_det']
        else:
            dets = ['saxs_det']
    newdets = dets
    for det in dets:
        if det not in ['saxs_det','waxs_det']:
            valid = False
            validation += f"invalid detector {det} is given\n"
    if len(dets) < 1:
        valid = False
        validation += "No detectors are given\n"
    if angle is not None:
            if -155 > angle or angle > 195:
                valid = False
                validation += f"angle of {angle} is out of range\n"
    if valid:
        retstr = f"\nspiral scanning {newdets} at {energy} eV \n"
        retstr += f"    with a diameter of {diameter} mm  and stepsize of {stepsize} mm\n"
        return retstr
    else:
        return f'\n\n\n\n_______________ERROR_____________________\n\n\n\n{validation}\n\n\n\n'



def dryrun_spiral_plan(edge = 270,diameter = default_diameter, spiral_step = default_spiral_step,exposure_time = default_exposure_time,pol_mode='lab', polarizations = [0],
                       angles = None,grating='rsoxs',diode_range='high', md = None, **kwargs):
    sim_mode=True
    valid = True
    valid_text = ''
    if not isinstance(edge,(float,int)):
        if isinstance(edge,list):
            if isinstance(edge[0],(float,int)):
                edge = edge[0]
                valid_text += f'\n\nWARNING only a single energy {edge} will be used for the spiral search'
    if not isinstance(edge,(float,int)):
        valid = False
        valid_text += f'\n\nERROR a single energy should be entered in the "edge" column for spiral scans not {edge} '
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
    if not isinstance(exposure_time,(int,float)):
        valid = False
        valid_text += f'\n\nERROR - invalid exposure time for spiral scans was given {exposure_time}\n\n'
    if edge > 1200 and grating == 'rsoxs':
        valid = False
        valid_text += f'\n\nERROR - energy is not appropriate for this grating\n\n'
    if not valid:
        # don't go any further, even in simulation mode, because we know the inputs are wrong
        if not sim_mode:
            ...
            #NON-SIM #raise ValueError(valid_text)
        else:
            return valid_text
        # if we are still valid - try to continue
    if angles is None:
        angles = [None]
    for angle in angles:
        for pol in polarizations:
            valid_text += spiralsearch( #NON-SIM #yield from spiralsearch
                                diameter=diameter,
                                stepsize=spiral_step,
                                energy=edge,
                                pol=pol,
                                angle=angle,
                                exposure=exposure_time,
                                md=md,
                                sim_mode=True)
    return valid_text
        