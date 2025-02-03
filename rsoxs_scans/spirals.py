"""Does the Spirals #TODO Docs

"""

# imports
import copy
from copy import deepcopy
from .defaults import *
import numpy as np




def pickLocationsFromSpirals( ## Intended to be an updated, data-security-compliant version of resolve_spirals.  Probably will just have this function pick spots for one sample and then it can be rerun for multiple samples.  That way, not all spirals have to be resolved in one go.
        configuration, ## Up-to-date spreadsheet with current sample locations.  TODO: maybe load sheet separately and then pick spots and then save out a new sheet
        sampleID,
        catalog,
        scanID_Survey, ## Maybe the more generic thing to call it is a survey scan
        locationsSelected_Indices,
        
):
    
    ## TODO: Consider making this a more generic function that picks a sample location from some series scan.  For spiral scans, it picks x and y location, but for an angle series, it could pick from there as well
    ## Can do something like try/except where I try to find the coordinate from primary but otherwise, find it from the baseline
    ## Otherwise, this is simple enough to make a separate function for an angle series and not have unnecessary errors due to extra checking

    
    ## Load spiral scan from tiled and gather location coordinates
    scanSurvey = catalog[int(scanID_Survey)]
    ## TODO: If sample_id from tiled does not equal the sample ID here, then give warning
    try: locations_OutboardInboard = scanSurvey["primary"]["data"]["RSoXS Sample Outboard-Inboard"].read()
    except KeyError: locations_OutboardInboard = scanSurvey["primary"]["data"]["manipulator_x"].read()
    
    try: locations_DownUp = scanSurvey["primary"]["data"]["RSoXS Sample Up-Down"].read()
    except KeyError: locations_DownUp = scanSurvey["primary"]["data"]["manipulator_y"].read()
    
    try: locations_UpstreamDownstream = scanSurvey["baseline"]["data"]["RSoXS Sample Downstream-Upstream"][0]
    except KeyError: locations_UpstreamDownstream = scanSurvey["baseline"]["data"]["manipulator_z"][0]

    try: locations_Theta = scanSurvey["baseline"]["data"]["RSoXS Sample Rotation"][0]
    except KeyError: locations_Theta = scanSurvey["baseline"]["data"]["manipulator_r"][0]
    
    
    ## Find the sample to update location
    ## TODO: probably better to deep copy configuration and search through the copy while updating the original configuration?
    for index_Configuration, sample in enumerate(configuration):
        if sample["sample_id"] == sampleID: 
            #locationInitial = sample["location"]
            for index_locationSelected_Indices, locationSelected_Indices in enumerate(locationsSelected_Indices):
                #locationNewFormatted = copy.deepcopy(locationInitial)
                locationNewFormatted = [{'motor':'x','position':locations_OutboardInboard[locationSelected_Indices]},
                                        {'motor':'y','position':locations_DownUp[locationSelected_Indices]},
                                        {'motor':'th','position':locations_Theta},
                                        {'motor':'z','position':locations_UpstreamDownstream}]
                if index_locationSelected_Indices==0: sample["location"] = locationNewFormatted
                else: 
                    sampleNew = copy.deepcopy(sample)
                    sampleNew["location"] = locationNewFormatted
                    sampleNew["sample_name"]+=f'_{index_locationSelected_Indices}'
                    sampleNew["sample_id"]+=f'_{index_locationSelected_Indices}'
                    configuration.append(sampleNew)
            break ## Exit after the sample is found and do not spend time looking through the other samples
    return configuration


## How to use pick_locations_from_spirals
"""
## Install rsoxs codebase and pyhyper

!pip install "git+https://github.com/NSLS-II-SST/rsoxs_scans.git@rsoxsIssue18_SimplifyScans"
!pip install "git+https://github.com/usnistgov/PyHyperScattering.git#egg=PyHyperScattering[bluesky]"
"""

"""
## Imports

from rsoxs_scans.spreadsheets import load_samplesxlsx, save_samplesxlsx
from rsoxs_scans.spirals import pickLocationsFromSpirals

import PyHyperScattering as phs
print(f'Using PyHyper Version: {phs.__version__}')


Loader = phs.load.SST1RSoXSDB(corr_mode="none") #Loader = phs.load.SST1RSoXSDB(corr_mode='none', catalog_kwargs={"username":"pketkar"}) #Loader = phs.load.SST1RSoXSDB(corr_mode='none')
Catalog = Loader.c
Catalog
"""


"""
## Use the function

pathConfiguration = r"/content/drive/Shareddrives/NISTPostdoc/CharacterizationData/BeamTime/20250123_SST1_Commissioning_Jordan-Sweet/DataAnalysis/in_2025-02-01_UpdatedBar.xlsx"
configuration = load_samplesxlsx(pathConfiguration) ## (load_spreadsheet with update_configuration=False in my new code)

configuration = pickLocationsFromSpirals(configuration=configuration,
                            sampleID="OpenBeam_NIST",
                            catalog=Catalog,
                            scanID_Survey=91532,
                            locationsSelected_Indices=[0, 8, 15]
                            )

save_samplesxlsx(bar=configuration, name="TestOut", path=r"/content/drive/Shareddrives/NISTPostdoc/CharacterizationData/BeamTime/20250123_SST1_Commissioning_Jordan-Sweet/DataAnalysis/")

"""






## Eliot's old code is below

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
