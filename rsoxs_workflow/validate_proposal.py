## Saving Eliot's proposal lookup code here to use separately

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
    # pass_client = httpx.Client(base_url="https://api-staging.nsls2.bnl.gov")
    pass_client = httpx.Client(base_url="https://api.nsls2.bnl.gov")
    responce = pass_client.get(f"/v1/proposal/{proposal}")
    # print(responce.json())
    res = responce.json()["proposal"]
    # return res
    if "safs" not in res:
        warnings.warn(f"proposal {proposal} does not appear to have any safs" + warn_text, stacklevel=2)
        pass_client.close()
        return None, None, None, None
    comissioning = 1
    if "cycles" in res:
        comissioning = 0
        if cycle not in res["cycles"]:
            warnings.warn(f"proposal {proposal} is not valid for the {cycle} cycle" + warn_text, stacklevel=2)
            pass_client.close()
            return None, None, None, None
    elif "Commissioning" not in res["type"]:
        warnings.warn(
            f"proposal {proposal} does not have a valid cycle, and does not appear to be a"
            " commissioning proposal" + warn_text,
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
            f"proposal {proposal} does not have a SAF for {beamline} active in the system" + warn_text,
            stacklevel=2,
        )
        pass_client.close()
        return None, None, None, None
    proposal_info = res
    dir_responce = pass_client.get(f"/v1/proposal/{proposal}/directories")
    dir_res = dir_responce.json()["directories"]
    if len(dir_res) < 1:
        warnings.warn(f"proposal{proposal} have any directories" + warn_text, stacklevel=2)
        pass_client.close()
        return None, None, None, None
    valid_path = ""
    for dir in dir_res:
        if (path_base in dir["path"]) and (("commissioning" in dir["path"]) or (cycle in dir["path"])):
            valid_path = dir["path"]
    if len(valid_path) == 0:
        warnings.warn(
            f"no valid paths (containing {path_base} and {cycle} were found for proposal"
            f" {proposal}" + warn_text,
            stacklevel=2,
        )
        pass_client.close()
        return None, None, None, None

    pass_client.close()
    return res["data_session"], valid_path, valid_SAF, proposal_info
