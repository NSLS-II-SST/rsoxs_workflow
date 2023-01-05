#imports
import datetime
from copy import deepcopy
from operator import itemgetter
import bluesky.plan_stubs as bps
from .constructor import construct_exposure_times, get_energies, get_nexafs_scan_params
from .defaults import *
from .rsoxs import dryrun_rsoxs_plan
from .nexafs import dryrun_nexafs_plan
from .spirals import dryrun_spiral_plan



def dryrun_acquisition(acq,sample={}):
    # runs an acquisition from a sample
    # load the configuration
        #NON SIM #yield from load_configuration(acq['configuration'])
    if acq['configuration']=='WAXS':
        sample.update({'RSoXS_Main_DET':'waxs_det'})
    else:
        sample.update({'RSoXS_Main_DET':'saxs_det'})
    # load the sample
        #NON SIM #yield from load_sample(sample)
    if 'type' in acq:
        if acq['type']== 'rsoxs':
            return dryrun_rsoxs_plan(**acq,md=sample)
        elif acq['type'] == 'nexafs':
            return dryrun_nexafs_plan(**acq,md=sample)
        elif acq['type'] == 'spiral':
            return dryrun_spiral_plan(**acq,md=sample)
        elif acq['type'] == 'wait':
            #yield from bps.sleep(acq['edge'])
            return f"sleep for {acq['edge']} seconds"
        else:
            return f'\n\nError: {acq["type"]} is not valid\n\n'
    else:
        return '\n\nError: no acquisition type specified\n\n'

config_list = [
    'WAXSNEXAFS',
    'WAXS',
    'SAXS',
    'SAXSNEXAFS',
    'SAXS_liquid',
    'WAXS_liquid',]
def time_sec(seconds):
    dt = datetime.timedelta(seconds=seconds)
    return str(dt).split(".")[0]
def dryrun_bar(
    bar,
    sort_by=["sample_num"],
    rev=[False],
):
    """
    dry run all sample dictionaries stored in the list bar
    @param bar: a list of sample dictionaries
    @param sort_by: list of strings determining the sorting of scans
                    strings include project, configuration, sample_id, plan, plan_args, spriority, apriority
                    within which all of one acquisition, etc
    @param rev: list the same length of sort_by, or booleans, wetierh to reverse that sort
    @return:
    """

    config_change_time = 120  # time to change between configurations, in seconds.
    list_out = []
    for samp_num, s in enumerate(bar):
        sample = s
        sample_id = s["sample_id"]
        sample_project = s["project_name"]
        for acq_num, a in enumerate(s["acquisitions"]):
            if "priority" not in a.keys():
                a["priority"] = 50
            list_out.append( # list everything we might possibly want for each acquisition
                [
                    sample_id,  # 0  X
                    sample_project,  # 1  X
                    a["configuration"],  # 2  X
                    a["type"],  # 3
                    est_scan_time(a),  # 4 calculated plan time
                    sample,  # 5 full sample dict
                    a,  # 6 full acquisition dict
                    samp_num,  # 7 sample index
                    acq_num,  # 8 acq index
                    a["edge"],  # 9  X
                    s["density"],  # 10
                    s["proposal_id"],  # 11 X
                    s["sample_priority"],  # 12 X
                    a["priority"],
                ]
            )  # 13 X
    switcher = { # all the possible things we might want to sort by
        "sample_id": 0,
        "project": 1,
        "config": 2,
        "type": 3,
        "edge": 9,
        "proposal": 11,
        "spriority": 12,
        "apriority": 13, # can just make this the default??
        "sample_num": 7,
    }
    # add anything to the above list, and make a key in the above dictionary,
    # using that element to sort by something else
    try:
        sort_by.reverse() # we want to sort from the last to the first element to match peopls expectations
        rev.reverse()
    except AttributeError:
        if isinstance(sort_by, str): # accept that someone might just put a single string
            sort_by = [sort_by]
            rev = [rev]
        else:
            print(
                "sort_by needs to be a list of strings\n"
                "such as project, configuration, sample_id, plan, plan_args, spriority, apriority"
            )
            return
    try:
        for k, r in zip(sort_by, rev): # do all of the sorts in order
            list_out = sorted(list_out, key=itemgetter(switcher[k]), reverse=r)
    except KeyError:
        print(
            "sort_by needs to be a list of strings\n"
            "such as project, configuration, sample_id, plan, plan_args, spriority, apriority"
        )
        return
    failcount=0
    text = ""
    total_time = 0
    previous_config = ""
    for i, step in enumerate(list_out):
        text += f"________________________________________________\nAcquisition # {i} from sample {step[5]['sample_name']}\n\n"
        text += "Summary: load {} from {}, config {}, run {} (p {} a {}), starts @ {} takes {}\n".format(
            step[5]["sample_name"],
            step[1],
            step[2],
            step[3],
            step[12],
            step[13],
            time_sec(total_time),
            time_sec(step[4]),
        )
        if step[2] != previous_config:
            total_time += config_change_time
            text += " (+2 minutes for configuration change)\n"
        text += "\n"
        if(step[2] not in config_list ):
            text += "Warning invalid configuration" + step[2]
        newtext = dryrun_acquisition(step[6],step[5])
        if isinstance(newtext,list):
            words = list(chain(*newtext))
            text += ''.join(words)
        else:
            text += newtext
        total_time += step[4]
        text += "\n________________________________________________\n"
        previous_config = step[2]
    text += (
        f"\n\nTotal estimated time including config changes {time_sec(total_time)}"
    )
    print( text )

    
def est_scan_time(acq):
    if 'type' in acq:
        if acq['type']== 'rsoxs':
            times, time = construct_exposure_times(get_energies(**acq,quiet=1),acq.get('exposure_time',default_exposure_time),acq.get('repeats',1),quiet=1)
            total_time = time * len(acq.get('polarizations',[0])) # time is the estimate for a single energy scan
            total_time += 30*len(acq.get('polarizations',[0])) # 30 seconds for each polarization change
            if isinstance(acq.get('angles',None),list):
                total_time *= len(acq['angles'])
                total_time += 30*len(acq['angles']) # 30 seconds for each angle change
            if isinstance(acq.get('temperatures',None),list):
                total_time *= len(acq['temperatures'])
            return total_time
        elif acq['type'] == 'nexafs':
            params, time = get_nexafs_scan_params(**acq,quiet=1)
            if acq.get('cycles',0) > 0:
                time *= 2*acq.get('cycles',0)
            total_time = time * len(acq.get('polarizations',[0])) # time is the estimate for a single energy scan
            total_time += 30*len(acq.get('polarizations',[0])) # 30 seconds for each polarization change
            if isinstance(acq.get('angles',None),list):
                total_time *= len(acq['angles'])
                total_time += 30*len(acq['angles']) # 30 seconds for each angle change
            if isinstance(acq.get('temperatures',None),list):
                total_time *= len(acq['temperatures'])
            return total_time
        elif acq['type'] == 'spiral':
            exp=1
            exptime = acq.get('exposure_time',default_exposure_time)
            if isinstance(exptime,(int,float)):
                if exptime >0:
                    exp = exptime
            num = (round(acq.get('diameter',default_diameter) / acq.get('spiral_step',default_spiral_step)) + 1)**2
            time = (exp+5.0)*num
            total_time = time * len(acq.get('polarizations',[0])) # time is the estimate for a single energy scan
            total_time += 30*len(acq.get('polarizations',[0])) # 30 seconds for each polarization change
            if isinstance(acq.get('angles',None),list):
                total_time *= len(acq['angles'])
                total_time += 30*len(acq['angles']) # 30 seconds for each angle change
            return total_time
        else:
            return 0
    else:
        return 0