## New spreadsheet loader and saver


import pandas as pd




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


def sanitizeSamples(configuration):
    for indexSample, sample in enumerate(configuration):
        if not isinstance(configuration["sample_id"], str):
            raise ValueError("sample_id for row " + str(indexSample) + " must be a string")
        configuration["acquisitions"] = []
    
    return configuration


def sanitizeAcquisitions(acquisitionsDict, configuration):
    ## TODO: not complete, add more sanitization here.  Check Eliot's code for anything I might want to add.
    sampleIDs = [sample["sample_id"] for sample in configuration]

    for indexAcquisition, acquisition in enumerate(acquisitionsDict):
        if acquisition["sample_id"] not in sampleIDs:
            raise ValueError("sample_id " + str(acquisition["sample_id"]) + " in row Acquisitions row " + str(indexAcquisition) + " was not found in Samples list")
        """
        if acquisition["sample_id"] == "spiral":
            if len(acquisition["spiralDimensions"]) != 3:
                raise ValueError("spiralDimensions must have 3 elements.")
        """
    return acquisitionsDict