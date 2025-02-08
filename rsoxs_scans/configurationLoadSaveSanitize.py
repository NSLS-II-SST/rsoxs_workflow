## New spreadsheet loader and saver


import pandas as pd
import copy
import json
import re, warnings, httpx
from .defaults import (
    CURRENT_CYCLE,
)




def loadSpreadsheet_Local(filePath):
    ## TODO: copy over eliot's code piece by piece and make comments
    ## TODO: Bar sheet should remain same but rename to samples maybe (see my partway done spreadsheet in rsoxs package)
    ## TODO: redo acquisitions
    ## TODO: use natsort to get things in order of bar location

    ## The following are items that were present in Eliot's spreadsheet loader, but I might not keep going forward.
    ## Eliot sets a version number for the Excel file and checks for this.  Not sure if this is necessary, because if anyone incorrectly changes anything, then it would still be wrong?
    ## Also, Eliot has the top few rows with instructions, but I might leave that aside for now.
    ## Most probably getting rid of the Parameter/Index


    ## Load list of samples and metadata, make a configuration dictionary, and sanitize
    samplesDF = pd.read_excel(filePath, sheet_name="Samples")
    configuration = samplesDF.to_dict(orient="records")
    configuration = sanitizeSamples(configuration)

    ## Load list of acquisitions, make a dictionary, and sanitize
    acquisitionsDF = pd.read_excel(filePath, sheet_name="Acquisitions")
    acquisitionsDict = acquisitionsDF.to_dict(orient="records")
    acquisitionsDict = sanitizeAcquisitions(acquisitionsDict, configuration)
    
    ## Store acquisitions into its respective sample dictionary.  Consider making this a separate function so that dictionaries written directly in Bluesky can be fed into this function.
    for indexAcquisition, acquisition in enumerate(acquisitionsDict):
        for indexSample, sample in enumerate(configuration):
            if sample["sample_id"] == acquisitionsDict["sample_id"]: configuration[indexSample]["acquisitions"].append(acquisition)

    ## TODO: bookmark for what I have copied over from Eliot's code: https://github.com/NSLS-II-SST/rsoxs_scans/blob/main/rsoxs_scans/spreadsheets.py#L451



    return configuration






## TODO: For now, I am keeping Sample/Bar parameters exactly the same as how Eliot had them, but I would like to refactor these later on.
samplesParameters_Required = [
    "bar_name", ## TODO: Would like to eliminate in the future
    "sample_id", ## TODO: Would like to rename to sampleID
    "sample_name", ## TODO: Would like to eliminate and consolidate with sample_id
    "project_name",
    "institution",
    "proposal_id",
    "bar_spot",
    "front",
    "grazing",
    "angle", ## TODO: Would like to refactor so that there is a single angle definition
    "height", ## Required for now to get z offset
    "sample_priority", ## TODO: Would like to eliminate, becasue in practice, Acquisitions priority is what matters
]
samplesParameters_Strings = [
    "bar_name", 
    "sample_id", 
    "sample_name",
    "project_name",
    "institution",
    "bar_spot",
]
samplesParameters_Booleans = [
    "front",
    "grazing",
]
samplesParameters_Ints = [
    "proposal_id",
    "sample_priority",
]

def sanitizeSamples(configuration):
    for indexSample, sample in enumerate(copy.deepcopy(configuration)): ## Making a copy so that I am not changing the configuration that I am iterating over
        
        ## There were a couple options on how to handle this:
        ## 1) Have a template, and make sure spreadsheets adhere exactly to that template.
        ## 2) Have some required parameters, but otherwise, users can have additional columns of their choosing.
        ## I am opting for option 2 becuase this way, users can decide what metadata matters to them and how they want to organize it.
        
        ## Check that required parameters exist
        ## For a spreadsheet, this would probably be more efficient to check once when the spreadsheet is loaded rather than one-by-one for each sample.  But it is good to have in case sample configuration is loaded as dictionary directly in Bluesky rather than using spreadsheet.
        for indexParameter, parameter in enumerate(samplesParameters_Required):
            if sample.get(parameter, "Not present") == "Not present":
                raise KeyError(parameter + " is a required parameter.  Please add " + parameter + " parameter with an appropriate value.")
        
        ## Then sanitize required parameters further to make sure they are correct type, value, etc.
        for indexParameter, parameter in enumerate(samplesParameters_Strings):
            if not isinstance(sample[parameter], str):
                raise ValueError(parameter + " for row " + str(indexSample) + " must be a string")
        for indexParameter, parameter in enumerate(samplesParameters_Booleans):
            if not isinstance(sample[parameter], bool):
                raise ValueError(parameter + " for row " + str(indexSample) + " must be TRUE or FALSE")
        for indexParameter, parameter in enumerate(samplesParameters_Ints):
            if (not isinstance(sample[parameter], int)) or (sample[parameter] < 0):
                raise ValueError(parameter + " for row " + str(indexSample) + " must be a positive integer")
        ## If sample angles are invalid, default to normal incidence
        if sample["grazing"]:
            if ((not isinstance(sample["angle"], (float, int))) 
                or (sample["angle"] < 20) 
                or (sample["angle"] > 90)):
                print("Invalid angle.  Defaulting to normal incidence.")
                configuration[indexSample]["angle"] = 90
        if not sample["grazing"]:
            if ((not isinstance(sample["angle"], (float, int))) 
                or (sample["angle"] < -14) 
                or (sample["angle"] > 90)):
                print("Invalid angle.  Defaulting to normal incidence.")
                configuration[indexSample]["angle"] = 0
        if not (sample["height"] >= 0):
            raise ValueError("Sample height in row " + str(indexSample) + " must be 0 or larger.")

        ## Sanitize location and acquisition history
        ## This is mostly copied from Eliot's code without much reorganization
        if sample.get("location", "Not present") == "Not present":
            configuration[indexSample]["location"] = "[]"
        configuration[indexSample]["location"] = json.loads(sample.get("location", "[]").replace("'", '"'))
        if sample.get("bar_loc", "Not present") == "Not present":
            configuration[indexSample]["bar_loc"] = "{}" ## TODO: need a better name, such as location_relative.  bar_loc stores information from bar image and offset values.
        configuration[indexSample]["bar_loc"] = json.loads(sample.get("bar_loc", "{}").replace("'", '"'))
        if sample.get("acq_history", "Not present") == "Not present":
            configuration[indexSample]["acq_history"] = "[]"
        configuration[indexSample]["acq_history"] = json.loads(
            sample.get("acq_history", "[]").replace("'", '"').rstrip('\\"').lstrip('\\"')
        )

        ## Grab proposal information from PASS.  Copied from Eliot's code.
        try:
            configuration[indexSample]["data_session"], configuration[indexSample]["analysis_dir"], configuration[indexSample]["SAF"], configuration[indexSample]["proposal"] = get_proposal_info(str(sample["proposal_id"]))
        except:
            warnings.warn("PASS lookup failed - trusting values", stacklevel=2)
            pass
        
        ## These parts are copied from Eliot's code
        configuration[indexSample]["bar_loc"]["spot"] = sample["bar_spot"]
        configuration[indexSample]["bar_loc"]["th"] = sample["angle"]
        ## Eliot: Get rid of the stupid unnamed columns thrown in by pandas
        for key in [key for key, value in sample.items() if "named" in key.lower() or "Index" in key]:
            del configuration[indexSample][key]

        ## TODO: In the future, might want to have this more flexible, so users could add acquisitions to this dictionary and feed it in directly through Bluesky, but for now, acquisitions have to be entered separately
        sample["acquisitions"] = []
        
    return configuration

## This is directly copied from Eliot's code
def get_proposal_info(proposal_id, beamline="SST1", path_base="/sst/", cycle=CURRENT_CYCLE):
    """Query the api PASS database, and get the info corresponding to a proposal ID

    Parameters
    ----------2
    proposal_id : str or int
        string of a number, a string including a "GU-", "PU-", "pass-", or  "C-" prefix and a number, or a number
    beamline : str, optional
        the beamline name from PASS, by default "SST1"
    path_base : str, optional
        the part of the path that indicates it's really for this beamline, by default "/sst/"
    cycle : str, optional
        the current cycle (or the cycle that is valid for this purpose), by default "2023-1"

    Returns
    -------
    tuple (res["data_session"], valid_path, valid_SAF, proposal_info)
         data_session ID which should be put into the run engine metadata of every scan, the path to write analyzed data to, the SAF, and all of the proposal information for the metadata if needed
    """

    warn_text = (
        "\n WARNING!!! no data taken with this proposal will be retrievable \n  it is HIGHLY"
        " suggested that you fix this \n if you are running this outside of the NSLS-II network,"
        " this is expected"
    )
    proposal_re = re.compile(r"^[GUCPpass]*-?(?P<proposal_number>\d+)$")
    if isinstance(proposal_id, str):
        proposal = proposal_re.match(proposal_id).group("proposal_number")
    else:
        proposal = proposal_id
    #pass_client = httpx.Client(base_url="https://api-staging.nsls2.bnl.gov")
    pass_client = httpx.Client(base_url="https://api.nsls2.bnl.gov")
    responce = pass_client.get(f"/v1/proposal/{proposal}")
    #print(responce.json())
    res = responce.json()['proposal']
    #return res
    if "safs" not in res:
        warnings.warn(
            f"proposal {proposal} does not appear to have any safs" + warn_text, stacklevel=2
        )
        pass_client.close()
        return None, None, None, None
    comissioning = 1
    if "cycles" in res:
        comissioning = 0
        if cycle not in res["cycles"]:
            warnings.warn(
                f"proposal {proposal} is not valid for the {cycle} cycle" + warn_text, stacklevel=2
            )
            pass_client.close()
            return None, None, None, None
    elif "Commissioning" not in res["type"]:
        warnings.warn(
            f"proposal {proposal} does not have a valid cycle, and does not appear to be a"
            " commissioning proposal"
            + warn_text,
            stacklevel=2,
        )
        pass_client.close()
        return -1
    if len(res["safs"]) < 0:
        warnings.warn(
            f"proposal {proposal} does not have a valid SAF in the system" + warn_text,
            stacklevel=2,
        )
        pass_client.close()
        return None, None, None, None
    valid_SAF = ""
    for saf in res["safs"]:
        if saf["status"] == "APPROVED" and beamline in saf["instruments"]:
            valid_SAF = saf["saf_id"]
    if len(valid_SAF) == 0:
        warnings.warn(
            f"proposal {proposal} does not have a SAF for {beamline} active in the system"
            + warn_text,
            stacklevel=2,
        )
        pass_client.close()
        return None, None, None, None
    proposal_info = res
    dir_responce = pass_client.get(f"/v1/proposal/{proposal}/directories")
    dir_res = dir_responce.json()['directories']
    if len(dir_res) < 1:
        warnings.warn(f"proposal{proposal} have any directories" + warn_text, stacklevel=2)
        pass_client.close()
        return None, None, None, None
    valid_path = ""
    for dir in dir_res:
        if (path_base in dir["path"]) and (('commissioning' in dir["path"]) or (cycle in dir["path"])):
            valid_path = dir["path"]
    if len(valid_path) == 0:
        warnings.warn(
            f"no valid paths (containing {path_base} and {cycle} were found for proposal"
            f" {proposal}"
            + warn_text,
            stacklevel=2,
        )
        pass_client.close()
        return None, None, None, None

    pass_client.close()
    return res["data_session"], valid_path, valid_SAF, proposal_info








## TODO: import this into rsoxs scans and set those as defaults in the functions so that the defaults are decided in one root place
acquisitionParameters_Default = {
    "sample_id": "",
    "configurationInstrument": "allRetracted",
    "scanType": "nexafs_step",
    "energyListParameters": "carbon_NEXAFS",
    "polarizationFrame": "lab",
    "polarizations": [0],
    "exposureTime": 0.01,
    "exposuresPerEnergy": 1,
    "sampleAngles": [0],
    "spiralDimensions": [0.3, 1.8, 1.8], ## [step_size, diameter_x, diameter_y], useful if our windows are rectangles, not squares
    "groupName": "Group",
    "priority": 1,
}
## TODO: would like a cycles-like parameter where I can sleep up and down in energy.  Lucas would want that.

def sanitizeAcquisitions(acquisitionsDict, configuration):
    ## TODO: not complete, add more sanitization here.  Check Eliot's code for anything I might want to add.
    sampleIDs = [sample["sample_id"] for sample in configuration]

    for indexAcquisition, acquisition in enumerate(copy.deepcopy(acquisitionsDict)):
        if acquisition["sample_id"] not in sampleIDs:
            raise ValueError("sample_id " + str(acquisition["sample_id"]) + " in Acquisitions row " + str(indexAcquisition) + " was not found in Samples list")
        
        ## TODO: try to define configurations in this local package as dictionaries and then just import into rsoxs package.  That way, I do not have to update list of valid configurations manually.  I can just auto-generate a list.

        ## Sanitize parameters for specific scan types
        if acquisition["scanType"]=="spiral": acquisitionsDict[indexAcquisition] = sanitizeSpirals(acquisition)
        if acquisition["scanType"]=="nexafs": acquisitionsDict[indexAcquisition] = sanitizeNEXAFS(acquisition)
        

    return acquisitionsDict


def sanitizeNEXAFS(acquisition):
    ## TODO: Most of the sanitization here can be reused for rsoxs scans.  This then would get called in sanitizeAcquisitions.
    return acquisition

def sanitizeSpirals(acquisition):
    if len(acquisition["spiralDimensions"]) != 3:
        raise ValueError("spiralDimensions must have 3 elements.")
    
    return acquisition


## TODO: Philosophical question: is dry running necessary if any errors can be captured through sanitization?
## It is still important to generate time estimates, but that could be separate.
## One of the features of dry running in the old code was that it could indicate if something might fall out of a motor range.  But if that is documented and sanitized here, that might be better?
