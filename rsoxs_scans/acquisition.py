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
    dafault_warning_step_time,
    default_exposure_time,
    default_diameter,
    default_spiral_step,
)
from .rsoxs import dryrun_rsoxs_plan
from .nexafs import dryrun_nexafs_plan
from .spirals import dryrun_spiral_plan


def dryrun_acquisition(acq, sample={}, sim_mode=True):
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

    if acq["configuration"] == "WAXS":
        sample.update({"RSoXS_Main_DET": "waxs_det"})
    else:
        sample.update({"RSoXS_Main_DET": "saxs_det"})
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
        else:
            outputs.append({"description": f'\n\nError: {acq["type"]} is not valid\n\n', "action": "error"})
            return outputs
    else:
        outputs.append({"description": "\n\nError: no acquisition type specified\n\n", "action": "error"})
        return outputs


config_list = [
    "WAXSNEXAFS",
    "WAXS",
    "SAXS",
    "SAXSNEXAFS",
    "SAXS_liquid",
    "WAXS_liquid",
]


def time_sec(seconds):
    dt = datetime.timedelta(seconds=seconds)
    return str(dt).split(".")[0]


def dryrun_bar(
    bar,
    sort_by=["sample_num"],
    rev=[False],
    print_dry_run=True,
    group='all',
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
            if not (group=='all' or a.get('group','all')=='all' or a.get('group','all') == group):
                continue # if the group filter or the acquisition group is "all" or not specified, 
                            # of if the the acquisition group matches the filter pass.  if not, ignore this acquisition
            if "uid" not in a.keys():
                a["uid"] = str(uuid.uuid1())
            a["uid"] = str(a["uid"])
            if "priority" not in a.keys():
                a["priority"] = 50
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
                    a.get("group",'all'),  # 15
                    a.get("slack_message_start",''),  # 16
                    a.get("slack_message_end",''),  # 17
                ]
            )  # 13 X
    switcher = {  # all the possible things we might want to sort by
        "sample_id": 0,
        "project": 1,
        "config": 2,
        "type": 3,
        "edge": 9,
        "proposal": 11,
        "spriority": 12,
        "apriority": 13,  # can just make this the default??
        "sample_num": 7,
    }
    # add anything to the above list, and make a key in the above dictionary,
    # using that element to sort by something else
    try:
        sort_by.reverse()  # we want to sort from the last to the first element to match peopls expectations
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
    try:
        for k, r in zip(sort_by, rev):  # do all of the sorts in order
            list_out = sorted(list_out, key=itemgetter(switcher[k]), reverse=r)
    except KeyError:
        print(
            "sort_by needs to be a list of strings\n"
            "such as project, configuration, sample_id, plan, plan_args, spriority, apriority"
        )
        return
    failcount = 0
    text = ""
    total_time = 0
    previous_config = ""
    acq_queue = []
    acqs_with_errors = []
    for i, step in enumerate(list_out):
        warnings.resetwarnings()
        text += f"________________________________________________\nAcquisition # {i} from sample {step[5]['sample_name']}\n\n"
        text += "Summary: load {} from {}, config {}, run {} priority(sample {} acquisition {}), starts @ {} takes {}\n".format(
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
        if step[4] > dafault_warning_step_time:
            warnings.warn(
                f"WARNING: acquisition # {i} will take {step[4]/60} minutes, which is more than {dafault_warning_step_time/60} minutes"
            )
        if step[2] not in config_list:
            warnings.warn(
                f"WARNING: acquisition # {i} has an invalid configuration - no configuration will be loaded"
            )
            text += "Warning invalid configuration" + step[2]
        outputs = dryrun_acquisition(step[6], step[5])
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
                statements.append(out["description"])
                if (out["action"]) == "error":
                    warnings.warn(f"WARNING: acquisition # {i} has a step with and error\n{out['description']}")
                    acqs_with_errors.append((i,out['description']))
            text += "".join(statements)
        acq_queue.extend(outputs)
        total_time += step[4]
        text += "\n________________________________________________\n"
        previous_config = step[2]
    for queue_step in acq_queue:
        queue_step["total_queue_time"] = total_time
        queue_step["time_after"] = total_time - queue_step["time_before"]-queue_step["acq_time"]

    text += f"\n\nTotal estimated time including config changes {time_sec(total_time)}"
    if print_dry_run:
        print(text)
    for index,error in acqs_with_errors:
        warnings.resetwarnings()
        warnings.warn(f"WARNING: acquisition # {index} has a step with an error\n{error}\n\n")
    return acq_queue


def est_scan_time(acq):
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
        else:
            return 0
    else:
        return 0
