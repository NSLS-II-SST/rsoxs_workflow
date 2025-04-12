import os
import numpy as np
import pandas as pd
import ast
import copy
import json
import datetime
import re, warnings, httpx
import uuid



def load_configuration_from_spreadsheet(file_path):
    """
    General map: Spreadsheet → sanitize spreadsheet → separate lists of dictionaries for samples and acquisitions → organize and combine dictionaries into rsoxs_config format → sanitize → return configuration
    Workflow is organized such that it should be easy to set up a different function in which configuraiton information can be entered directly into the terminal, and it would be sanitized in the same manner as information entered through the spreadsheet.
    
    Parameters
    ----------
    file_path : string
        Path to spreadsheet file that contains configuration parameters

    Returns
    -------
    configuration: list of dictionaries
        List of samples and acquisitions sorted into format that will be used in rsoxs codebase
    """
  
    ## Load and sanitize spreadsheet
    samples_df = pd.read_excel(file_path=file_path, sheet_name="Samples")
    samples_df = sanitize_spreadsheet(samples_df)
    acquisitions_df = pd.read_excel(file_path=file_path, sheet_name="Acquisitions")
    acquisitions_df = sanitize_spreadsheet(acquisitions_df)

    ## Convert dataframes to list of dictionaries.
    ## TODO: A separate function could be made later if a user prefers to create these separate dictionary lists in the Bluesky terminal or enter them as a text/toml file and skip the above steps.
    ## TODO: If a user prefers to create/import a single configuration dictionary list with the same format as rsoxs_config, acquisitions will need to be separated using gather_acquisitions_from_configuration, and then the acquisitions would need to be deleted from the configuration temporarily prior to sanitization.  See save_configuration_to_spreadsheet.
    configuration = samples_df.to_dict(orient="records")
    configuration = sanitize_samples(configuration)
    acquisitions_dict = acquisitions_df.to_dict(orient="records")
    acquisitions_dict = sanitize_acquisitions(acquisitions_dict, configuration) ## TODO: is it better to do as a loop here and loop through sanitize_acquisition?

    ## TODO: store acquisitions into its respective sample dictionary using update_configuration_with_acquisition
    ## ***Bookmark

    configuration = spreadsheet_to_configuration(file_path=file_path) ## Includes loading excel file, converting to dataframe then dictionary, and adding acquisitions into configuration


    return configuration


def sanitize_spreadsheet(df):
    """
    Sanitize spreadsheet data by converting strings to appropriate Python types.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing configuration data

    Returns
    -------
    pandas.DataFrame
        Sanitized DataFrame
    """
    
    # Define type conversion functions
    def safe_eval(val):
        if val is None:
            return None
        if isinstance(val, (bool, int, float)):
            return val
        try:
            ## Lists, etc. will get imported as strings, so need to convert to the intended data type.
            # Handle string representations of Python literals
            return ast.literal_eval(str(val))
        except (ValueError, SyntaxError) as e:
            # If not a Python literal, return as is
            print(f"Error evaluating {val}: {e}")
            return val

    # List of columns that should remain as strings
    ## TODO: energy_list_parameters is sometimes a string or sometimes a list.  Figure out a way to handle that.
    string_columns = [
        "location",
        "bar_loc",
        "acq_history",
        "acquire_status",
        "sample_id",
        "sample_name",
        "sample_state",
        "sample_set",
        "project_name",
        "project_desc",
        "institution",
        "configuration_instrument",
        "scan_type",
        "polarization_frame",
        "group_name",
        "uid_local",
        "notes",
        "proposal_id",
        "bar_spot",
        "notes",
        "bar_name",
        "analysis_dir",
        "data_session",
        "SAF",
    ]

    # Process each column
    for column in df.columns:
        if column in string_columns:
            continue

        try:
            df[column] = df[column].apply(safe_eval)
        except Exception as e:
            print(f"Error processing column {column}: {e}")
            continue
    ## TODO: this sanitization throws warning about energy list names.  Probably need if statement to handle energy list parameters.
    
    ## Blank cells are loaded as nan by default.  Replace with None.
    ## Need this line at the end rather than the beginning because the above sanitization somehow turns None back into NaN
    df = df.replace({np.nan: None})
    
    return df



## TODO: It may be an option to have configuration as either string or entering the dictionary itself, but probably don't want to extend that option to users.  Better to keep options limited to configurations that are known to work and be safe.
