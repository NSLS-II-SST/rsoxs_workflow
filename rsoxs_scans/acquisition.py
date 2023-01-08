"""Handles conversion of the bar (list of sample dicts) into the output queue dict or dryrun printed text. 

Also estimates scan time at a high level, relying on constructor module functions to generate ranges. Also contains a dict of valid sample configurations.
"""

# imports
import datetime, warnings, uuid
from copy import deepcopy
from operator import itemgetter
import bluesky.plan_stubs as bps
from .constructor import construct_exposure_times, get_energies, get_nexafs_scan_params
from .defaults import (
    default_speed,
    default_frames,
    edge_names,
    rsoxs_edges,
    rsoxs_ratios_table,
    frames_table,
    nexafs_ratios_table,
    nexafs_edges,
    nexafs_speed_table,
    default_warning_step_time,
    default_exposure_time,
    default_diameter,
    default_spiral_step,
)
from .rsoxs import dryrun_rsoxs_plan
from .nexafs import dryrun_nexafs_plan
from .spirals import dryrun_spiral_plan

# List of Valid Measurement Configurations
config_list = [
    "WAXSNEXAFS",
    "WAXS",
    "SAXS",
    "SAXSNEXAFS",
    "SAXS_liquid",
    "WAXS_liquid",
]

### TODO sim_mode is unused, remove and update docstring?
### TODO sample maybe should be required always - remove default value and update docstring?
def dryrun_acquisition(acq, sample={}, sim_mode=True):
    """Generates the output queue elements corresponding to a single acquisition. 
    
    Steps include loading configuration, loading sample, assigning detector, and running the appropriate measurement dryrun (e..g, NEXAFS, RSoXS, Spiral). 

    Parameters
    ----------
    acq : dict
        acquisition dictionary entry containing all parameters needed to specify an acquisition (e.g., sample_id, configuration, type, priority, edge, etc.)
    sample : dict, optional
        sample dictionary containing sample metadata (from bar sheet) and all relevant acquisitions (from Acquisitions sheet), by default {}
    sim_mode : bool, optional
        _description_, by default True

    Returns
    -------
    list of dict
        Output queue entries from a single acquisition as a list of dictionaries
    """

    # runs an acquisition from a sample
    outputs = []
    # load the configuration
    outputs.append(
        {
            "description": f"load configuration {acq['configuration']}\n",
            "action": "load_configuration",
            "kwargs": {"configuration": acq["configuration"]},
        }
    )
    # load the sample
    samp_dict = deepcopy(sample)
    del samp_dict["acquisitions"]  # this becomes weirdly verbose
    outputs.append(
        {
            "description": f"load sample {sample['sample_name']}\n",
            "action": "load_sample",
            "kwargs": {"sample": samp_dict},
        }
    )

    # Assign the RSoXS Detector based on configuration specified
    if acq["configuration"] in ["WAXS", "WAXS_liquid", "WAXSNEXAFS"]:
        sample.update({"RSoXS_Main_DET": "waxs_det"})
    elif acq["configuration"] in ["SAXS", "SAXS_liquid", "SAXSNEXAFS"]:
        sample.update({"RSoXS_Main_DET": "saxs_det"})
    else:  # Invalid configuration string
        outputs.append({"description": f'\n\nError: {acq["configuration"]} is not valid\n\n', "action": "error"})

    # Run the appropriate dryrun function based on acquisition type and extend list to include their output queue dicts
    if "type" in acq:
        if acq["type"] == "rsoxs":
            outputs.extend(dryrun_rsoxs_plan(**acq, md=sample))
            return outputs
        elif acq["type"] == "nexafs":
            outputs.extend(dryrun_nexafs_plan(**acq, md=sample))
            return outputs
        elif acq["type"] == "spiral":
            outputs.extend(dryrun_spiral_plan(**acq, md=sample))
            return outputs
        elif acq["type"].lower() in ["wait", "sleep", "pause"]:
            outputs.append(
                {
                    "description": f"sleep for {acq['edge']} seconds\n",
                    "action": "sleep",
                    "kwargs": {"sleep_time": acq["edge"]},
                }
            )
            return outputs
        else:  # Invalid type string
            outputs.append({"description": f'\n\nError: {acq["type"]} is not valid\n\n', "action": "error"})
            return outputs
    else:  # No type specified
        outputs.append({"description": "\n\nError: no acquisition type specified\n\n", "action": "error"})
        return outputs


### TODO sort_by docstring explanation is confusing
def dryrun_bar(bar, sort_by=["sample_num"], rev=[False], print_dry_run=True, group="all"):
    """Generate output queue entries for all sample dicts in the bar list

    Parameters
    ----------
    bar : list of dict
        elements are unique dictionaries for each sample on the bar sheet with full metadata and acquisitions
    sort_by : list of str, optional
        specifies the sort priority to use when generating the acquisition queue, by default ["sample_num"]. 
        Valid options include: project, configuration, sample_id, plan, plan_args, spriority, apriority within which all of one acquisition, etc
    rev : list, optional
        whether to reverse the sort algorithm, list the same length of sort_by, or booleans, by default [False]
    print_dry_run : bool, optional
        whether to print the final scan queue to stdout, by default True
    group : str, optional
        subset of acquisitions to execute the dry-run for (excel column 'group'), by default "all". case-insensitive

    Returns
    -------
    list of dict
        all acquisition queue entries for the matched group of scans as a list of dictionaries
    """

    config_change_time = 120  # time to change between configurations, in seconds.
    list_out = []

    # Loop through sample dicts in the bar
    for samp_num, s in enumerate(bar):
        sample = s
        sample_id = s["sample_id"]
        sample_project = s["project_name"]
        # Loop through acquisitions within the sample
        for acq_num, a in enumerate(s["acquisitions"]):

            # Skip this acquisition unless any of these conditions are true
            if not (
                group.lower() == "all"  # true if user specified all to be evaluated
                or a.get("group", "").lower() == group.lower()  # true if group matches user selected group
            ):
                continue

            if "uid" not in a.keys():
                a["uid"] = str(uuid.uuid1())
            a["uid"] = str(a["uid"])

            if "priority" not in a.keys():
                a["priority"] = 50  ### TODO why 50?

            # Generate list of lists, where each sub-list is a single acquisition
            list_out.append(  # list everything we might possibly want for each acquisition
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
                    a["priority"],  # 13
                    a["uid"],  # 14
                    a.get("group", "all"),  # 15
                    a.get("slack_message_start", ""),  # 16
                    a.get("slack_message_end", ""),  # 17
                ]
            )  # 13 X

    # Prepare for sorting scans
    switcher = {  # all the possible things we might want to sort by
        "sample_id": 0,
        "project": 1,
        "config": 2,
        "type": 3,
        "edge": 9,
        "proposal": 11,
        "spriority": 12,
        "apriority": 13,  # TODO can just make this the default??
        "sample_num": 7,
    }
    # add anything to the above list, and make a key in the above dictionary,
    # using that element to sort by something else
    try:
        sort_by.reverse()  # we want to sort from the last to the first element to match people's expectations
        rev.reverse()
    except AttributeError:
        if isinstance(sort_by, str):  # accept that someone might just put a single string
            sort_by = [sort_by]
            rev = [rev]
        else:
            print(
                "sort_by needs to be a list of strings\n"
                "such as project, configuration, sample_id, plan, plan_args, spriority, apriority"
            )
            return

    # Generate list of properly sorted scans in list_out
    try:
        for k, r in zip(sort_by, rev):  # do all of the sorts in order
            list_out = sorted(list_out, key=itemgetter(switcher[k]), reverse=r)
    except KeyError:
        print(
            "sort_by needs to be a list of strings\n"
            "such as project, configuration, sample_id, plan, plan_args, spriority, apriority"
        )
        return

    # Generate the output acquisition queue
    failcount = 0
    text = ""  # Dry run output text for visual inspection
    total_time = 0
    previous_config = ""
    acq_queue = []  # output queue
    acqs_with_errors = []

    # Loop through sorted acquisition steps and build output acquisition queue and dryrun text message
    for i, step in enumerate(list_out):
        warnings.resetwarnings()
        text += f"________________________________________________\nAcquisition # {i} from sample {step[5]['sample_name']}, group {step[15]}\n\n"
        text += "Summary: load {} from {}, config {}, run {} priority( sample {} acquisition {}), starts @ {} takes {}\n".format(
            step[5]["sample_name"],
            step[1],
            step[2],
            step[3],
            step[12],
            step[13],
            time_sec(total_time),
            time_sec(step[4]),
        )

        # Check for config change
        if step[2] != previous_config:
            total_time += config_change_time
            text += f" (+{config_change_time} seconds for configuration change)\n"
        text += "\n"

        # Check if acquisition will take too long
        if step[4] > default_warning_step_time:
            warnings.warn(
                f"WARNING: acquisition # {i} will take {step[4]/60} minutes, which is more than {default_warning_step_time/60} minutes"
            )

        # Check if configuration is invalid
        if step[2] not in config_list:
            warnings.warn(
                f"WARNING: acquisition # {i} has an invalid configuration - no configuration will be loaded"
            )
            text += "Warning invalid configuration" + step[2]
        outputs = dryrun_acquisition(step[6], step[5])

        # if this step has a single output entry, we are done with this entry
        if not isinstance(outputs, list):
            outputs = [outputs]

        else:
            statements = []
            for j, out in enumerate(outputs):
                out["acq_index"] = i
                out["queue_step"] = j
                out["acq_time"] = step[4]
                out["total_acq"] = len(list_out)
                out["time_before"] = total_time
                out["priority"] = step[13]
                out["uid"] = step[14]
                out["group"] = step[15]
                out["slack_message_start"] = step[16]
                out["slack_message_end"] = step[17]
                statements.append(f'Step {j}: {out["description"]}')

                if (out["action"]) == "error":
                    warnings.warn(f"WARNING: acquisition # {i} has a step with and error\n{out['description']}")
                    acqs_with_errors.append((i, out["description"]))

            text += "".join(statements)

        acq_queue.extend(outputs)
        total_time += step[4]
        text += "\n________________________________________________\n"
        previous_config = step[2]
    for queue_step in acq_queue:
        queue_step["total_queue_time"] = total_time
        queue_step["time_after"] = total_time - queue_step["time_before"] - queue_step["acq_time"]

    text += f"\n\nTotal estimated time including config changes {time_sec(total_time)}"
    if print_dry_run:
        print(text)
    # Warn user about acquisitions that contained errors
    for index, error in acqs_with_errors:
        warnings.resetwarnings()
        warnings.warn(f"WARNING: acquisition # {index} has a step with an error\n{error}\n\n")
    return acq_queue


def est_scan_time(acq):
    """Estimates scan duration in seconds for a given acquisition.

    Parameters
    ----------
    acq : dict
        dictionary containing acquisition parameters

    Returns
    -------
    float
        estimated scan duration in seconds
    """
    if "type" in acq:
        if acq["type"] == "rsoxs":
            times, time = construct_exposure_times(
                get_energies(**acq, quiet=True),
                acq.get("exposure_time", default_exposure_time),
                acq.get("repeats", 1),
                quiet=True,
            )
            total_time = time * len(acq.get("polarizations", [0]))  # time is the estimate for a single energy scan
            total_time += 30 * len(acq.get("polarizations", [0]))  # 30 seconds for each polarization change
            if isinstance(acq.get("angles", None), list):
                total_time *= len(acq["angles"])
                total_time += 30 * len(acq["angles"])  # 30 seconds for each angle change
            if isinstance(acq.get("temperatures", None), list):
                total_time *= len(acq["temperatures"])
            return total_time
        elif acq["type"] == "nexafs":
            params, time = get_nexafs_scan_params(quiet=True, **acq)
            if acq.get("cycles", 0) > 0:
                time *= 2 * acq.get("cycles", 0)
            total_time = time * len(acq.get("polarizations", [0]))  # time is the estimate for a single energy scan
            total_time += 30 * len(acq.get("polarizations", [0]))  # 30 seconds for each polarization change
            if isinstance(acq.get("angles", None), list):
                total_time *= len(acq["angles"])
                total_time += 30 * len(acq["angles"])  # 30 seconds for each angle change
            if isinstance(acq.get("temperatures", None), list):
                total_time *= len(acq["temperatures"])
            return total_time
        elif acq["type"] == "spiral":
            exp = 1
            exptime = acq.get("exposure_time", default_exposure_time)
            if isinstance(exptime, (int, float)):
                if exptime > 0:
                    exp = exptime
            num = (
                round(acq.get("diameter", default_diameter) / acq.get("spiral_step", default_spiral_step)) + 1
            ) ** 2
            time = (exp + 5.0) * num
            total_time = time * len(acq.get("polarizations", [0]))  # time is the estimate for a single energy scan
            total_time += 30 * len(acq.get("polarizations", [0]))  # 30 seconds for each polarization change
            if isinstance(acq.get("angles", None), list):
                total_time *= len(acq["angles"])
                total_time += 30 * len(acq["angles"])  # 30 seconds for each angle change
            return total_time
        elif acq["type"].lower() in ["wait", "sleep", "pause"]:
            return float(acq["edge"])
        else:  # not a matching type that takes time
            return 0
    else:  # acquisition has no type key
        return 0


def time_sec(seconds):
    """Generates a formatted timestamp (hh:mm:ss) from the input number of seconds

    Parameters
    ----------
    seconds : float
        number of seconds

    Returns
    -------
    str
        timestamp formatted as hh:mm:ss
    """
    dt = datetime.timedelta(seconds=seconds)
    return str(dt).split(".")[0]
