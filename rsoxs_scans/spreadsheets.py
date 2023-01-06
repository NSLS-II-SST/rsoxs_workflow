#imports
import numpy as np
from copy import deepcopy
import pandas as pd
import json
import re, warnings, httpx
import numpy as np

def load_samplesxlsx(filename):
    df = pd.read_excel(
        filename,
        na_values="",
        engine="openpyxl",
        keep_default_na=True,
        converters={"sample_date": str},
        sheet_name="Bar",
        skiprows=[1,2,3,4],
        verbose=True,
    )
    df.replace(np.nan, "", regex=True, inplace=True)
    new_bar = df.to_dict(orient="records")
    if not isinstance(new_bar, list): # if the bar has one element, it's not a list
        new_bar = [new_bar]
    for samp in new_bar:
        samp["acquisitions"] = [] # blank out any acquisitions elements which might be therer (they shouldn't be there unless someone added a column for some reason
    acqsdf = pd.read_excel(
        filename,
        na_values="",
        engine="openpyxl",
        keep_default_na=True,
        sheet_name="Acquisitions",
        skiprows=[1,2,3,4],
        #usecols="A:U",
        verbose=True,
    )
    #acqsdf.replace(np.nan, "", regex=True, inplace=True)
    acqs = acqsdf.to_dict(orient="records")
    if not isinstance(acqs, list): # is there only one acquistion?
        acqs = [acqs]
    for acq in acqs:
        for key in acq:
            if isinstance(acq[key],str):
                acq[key] = acq[key].replace('(','[').replace(')',']').replace("'",'"')
                try:
                    acq[key] = json.loads(acq[key])
                except:
                    pass
            if isinstance(acq[key],str):
                if ',' in acq[key]: # if the string looks like a list
                    try:
                        acq[key] = [float(num) for num in acq[key].split(',')] # cast it as a list of floating point numbers instead
                    except:
                        pass
        if np.isnan(acq["priority"]):
            break # force priority in every row, if missing, stop
        samp = next(dict for dict in new_bar if dict["sample_id"] == acq["sample_id"]) # get the sample that corresponds to the sample_id... the first one that matches it takes
        acq = {key:val for key, val in acq.items() if val == val and val != ''}
        try:
            acq['edge'] = json.loads(acq["edge"])
        except: # if edge isn't json parsable, it's probably just a string, and that's fine
            pass
        if isinstance(acq['edge'],str):
            if ',' in acq['edge']: # if the string looks like a list
                acq['edge'] = [float(num) for num in acq['edge'].split(',')] # cast it as a list of floating point numbers instead
        if 'polarizations' in acq:
            if isinstance(acq['polarizations'],(int,float)):
                acq['polarizations'] = [acq['polarizations']]
        if 'angles' in acq:
            if isinstance(acq['angles'],(int,float)):
                acq['angles'] = [acq['angles']]
        if 'temperatures' in acq:
            if isinstance(acq['temperatures'],(int,float)):
                acq['temperatures'] = [acq['temperatures']]
        samp["acquisitions"].append(acq) # no checking for validity here?
    for i, sam in enumerate(new_bar):
        new_bar[i]["location"] = json.loads(sam.get("location",'[]'))

        new_bar[i]["bar_loc"] = json.loads(sam.get("bar_loc",'{}'))
        
        if 'proposal_id' in sam:
            proposal = sam['proposal_id']
        elif 'data_session' in sam:
            proposal = sam['data_session']
        else:
            warnings.warn('no valid proposal was located - please add that and try again')
            proposal = 0
        sam['data_session'],sam['analysis_dir'],sam['SAF'],sam['proposal'] = get_proposal_info(proposal)
        if sam['SAF'] ==None:
            print(f'line {i}, sample {sam["sample_name"]} - data will not be accessible')
        if "acq_history" in sam.keys():
            new_bar[i]["acq_history"] = json.loads(sam["acq_history"])
        else:
            new_bar[i]["acq_history"] = []
        new_bar[i]["bar_loc"]["spot"] = sam["bar_spot"]
        for key in [key for key, value in sam.items() if "named" in key.lower()]: # get rid of the stupid unnamed columns thrown in by pandas
            del new_bar[i][key]
    return new_bar
            
def get_proposal_info(proposal_id, beamline='SST1', path_base='/sst/', cycle='2023-1'):
    '''
    proposal_id is either a string of a number, a string including a "GU-", "PU-", "pass-", or  "C-" prefix and a number, or a number
    beamline is the beamline name from PASS,
    path_base is the part of the path that indicates it's really for this beamline
    cycle is the current cycle (or the cycle that is valid for this purpose)

    queury the api PASS database, and get the info corresponding to a proposal ID
    returns:
    the data_session ID which should be put into the run engine metadata of every scan
    the path to write analyzed data to
    all of the proposal information for the metadata if needed
    '''
    warn_text = "\n WARNING!!! no data taken with this proposal will be retrievable \n  it is HIGHLY suggested that you fix this"
    proposal_re = re.compile(r"^[GUCPpass]*-?(?P<proposal_number>\d+)$")
    if isinstance(proposal_id, str):
        proposal = proposal_re.match(proposal_id).group("proposal_number")
    else:
        proposal = proposal_id
    pass_client = httpx.Client(base_url="https://api-staging.nsls2.bnl.gov")
    responce = pass_client.get(f"/proposal/{proposal}")
    res = responce.json()
    if "safs" not in res:
        warnings.warn(f'proposal {proposal} does not appear to have any safs'+warn_text)
        return None, None, None, None
    comissioning = 1
    if "cycles" in res:
        comissioning = 0
        if cycle not in res['cycles']:
            warnings.warn(f'proposal {proposal} is not valid for the {cycle} cycle'+warn_text)
            return None, None, None, None
    elif "Commissioning" not in res['type']:
        warnings.warn(
            f'proposal {proposal} does not have a valid cycle, and does not appear to be a commissioning proposal'+warn_text)
        return -1
    if len(res['safs']) < 0:
        warnings.warn(f'proposal {proposal} does not have a valid SAF in the system'+warn_text)
        return None, None, None, None
    valid_SAF = ""
    for saf in res['safs']:
        if saf['status'] == 'APPROVED' and beamline in saf['instruments']:
            valid_SAF = saf['saf_id']
    if len(valid_SAF) == 0:
        warnings.warn(f'proposal {proposal} does not have a SAF for {beamline} active in the system'+warn_text)
        return None, None, None, None
    proposal_info = res
    dir_responce = pass_client.get(f"/proposal/{proposal}/directories")
    dir_res = dir_responce.json()
    if len(dir_res) < 1:
        warnings.warn(f'proposal{proposal} have any directories'+warn_text)
        return None, None, None, None
    valid_path = ""
    for dir in dir_res:
        if comissioning and (path_base in dir['path']):
            valid_path = dir['path']
        elif (path_base in dir['path']) and (cycle in dir['path']):
            valid_path = dir['path']
    if len(valid_path) == 0:
        warnings.warn(f'no valid paths (containing {path_base} and {cycle} were found for proposal {proposal}'+warn_text)
        return None, None, None, None
    return res['data_session'], valid_path, valid_SAF, proposal_info


def save_samplesxls(bar, filename):
    switch = {
        'RSoXS Sample Outboard-Inboard': "x",
        'RSoXS Sample Up-Down': "y",
        'RSoXS Sample Downstream-Upstream': "z",
        'RSoXS Sample Rotation': "th",
        "x": "x",
        "y": "y",
        "z": "z",
        "th": "th",
    }
    acqlist = []
    for i, sam in enumerate(bar):
        for j, loc in enumerate(sam["location"]):
            if isinstance(loc["motor"], Device):
                bar[i]["location"][j]["motor"] = switch[loc["motor"].name]
        for acq in sam["acquisitions"]:
            acq.update({"sample_id": sam["sample_id"]})
            cleanacq = {}
            for key in acq:
                cleanacq[key] = json.dumps(acq[key])
            acqlist.append(cleanacq)
    sampledf = pd.DataFrame.from_dict(bar, orient="columns")
    df = deepcopy(sampledf)
    testdict = df.to_dict(orient="records")
    for i, sam in enumerate(testdict):
        if "acq_history" not in testdict[i].keys():
            testdict[i]["acq_history"] = []
        elif testdict[i]["acq_history"] == "":
            testdict[i]["acq_history"] = []
        # json dump the pythonic parts
        # including sample: bar_loc,location, proposal,acq_history
        testdict[i]["acq_history"] = json.dumps(testdict[i]["acq_history"])
        testdict[i]["bar_loc"] = json.dumps(testdict[i]["bar_loc"])
        testdict[i]["location"] = json.dumps(testdict[i]["location"])
        testdict[i]["proposal"] = json.dumps(testdict[i]["proposal"])
        
        testdict[i]["acq_history"] = json.dumps(testdict[i]["acq_history"])
        
    sampledf = pd.DataFrame.from_dict(testdict, orient="columns")
    sampledf = sampledf.loc[:, df.columns != "acquisitions"]
    acqdf = pd.DataFrame.from_dict(acqlist, orient="columns")
    writer = pd.ExcelWriter(filename)
    sampledf.to_excel(writer, index=False, sheet_name="Samples")
    acqdf.to_excel(writer, index=False, sheet_name="Acquisitions")
    writer.close()
