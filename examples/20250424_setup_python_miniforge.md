# Set up Python for data viewing and reduction

The instructions below are an example of how a Python environment can be set up to view and reduce data in a local JupyterLab notebook using Miniforge on a Windows computer.  In this example, all steps outlined here were run in a terminal command line interface, not a Jupyter notebook.  Some of these instructions *might* work on other platforms such as the NSLS II Jupyterhub, JupyterLab Desktop, or Google Colab, but there are no guarantees.

## Perform one-time installations
- Install Miniforge: https://github.com/conda-forge/miniforge/releases
- To aid this workflow, download Git (https://git-scm.com/download/win).  Then in the command prompt (not Anaconda Prompt), run `winget install --id Git.Git -e --source winget`.  Alternatively GitHub desktop can be donwloaded.  After this, if you are able to run ``git --version`` and have a version number outputted, the installation was successful.  If Miniforge Prompt was open, it may need to be restarted.

## Create a new environment and install desired packages (one-time)

The purpose of the conda environment is to contain the necessary package versions that will enable data reduction and not conflict with other packages.  Ideally, these steps should be performed once, and then this environment can be used again in the future.  In practice, packages versions may need to be adjusted, which may be done in the same environment or in a brand-new environment.

### Create and activate a new environment

- Open the Miniforge Prompt (or Command Prompt or Windows PowerShell).  Do not use the terminal feature after opening JupyterLab.

- Create a new environment.  Replace `YOUR_ENVIRONMENT_NAME` with a an environment name of choice that does not contain any spaces.  If needed, the `...` can be replaced with other conda packages to be installed in this environment separated by spaces.  In this example, `...` omitted.  After loading some packages, you will be asked if you want to proceed.  Enter y (yes).

  ```  
     conda create -n YOUR_ENVIRONMENT_NAME ipykernel jupyterlab ...
  ```
  The `-n` is used to identify the environment by its name.  Alternatively, `-p` can be used followed by a file path to identify an environment by a desired file path. 
  
- Activate the desired environment.
  
  ```
       conda activate YOUR_ENVIRONMENT_NAME
  ```
  After running this command, the selected environment name should appear in parentheses in the command prompt.  If it does not appear, run `conda info --envs`, and the active environment should be marked by an asterisk.
  
- Run the following to add the environment to your Jupyter notebook selection.  The display name and environment name do not have to be the same.

  ```  
     python -m ipykernel install --user --name YOUR_ENVIRONMENT_NAME --display-name YOUR_ENVIRONMENT_NAME
  ```


### Install Python

Check the Python version.  Use version 3.12 or lower for PyHyperScattering to work.

```  
   python --version
```
  
It may be necessary to downgrade to Python version 3.12 for PyHyperScattering (even though some users have had success with Python version 3.13).

```  
   conda install python==3.12
```
  
If a CondaSSL error is encountered during this step, the following solution can be run, and then Python installation can be retried: https://github.com/conda/conda/issues/8273

### Install PyHyperScattering

Install PyHyperScattering, which will be used to access and reduce data.

```
pip install pyhyperscattering[bluesky,ui]
```

The `bluesky` portion installs Bluesky-related dependencies needed to access the NSLS II Tiled database. The `ui` portion installs the necessary dependencies to draw a mask.  In some cases, it may be necessary to clone and check out a later PyHyperScattering commit or branch instead of the default version. Below are some examples.

- `pip install "git+https://github.com/usnistgov/PyHyperScattering.git#egg=PyHyperScattering[bluesky, ui]"` installs the latest commit on the main branch.

- `pip install "git+https://github.com/usnistgov/PyHyperScattering.git@Issue170_UpdateDatabrokerImports#egg=PyHyperScattering[bluesky, ui]"` installs the latest commit on the branch named `Issue170_UpdateDatabrokerImports`.

- `pip install "git+https://github.com/usnistgov/PyHyperScattering.git@6657973#egg=PyHyperScattering[bluesky, ui]"` installs commit `6657973`.

### Install rsoxs_workflow

Install rsoxs_workflow, which will be used to test the samples/acquisitions spreadsheet, perform some necessary sample alignment operations, and to view alignment scans.
TODO: add instructions


## Open JupyterLab

- Open the Miniforge Prompt and activate the desired environment if this has not been done yet.

  ```
       conda activate YOUR_ENVIRONMENT_NAME
  ```

  If you do not remember your environment, you can run `conda env list` to display a list of environments that currently exist.  You can run `conda info --envs` to check which environment is active.

- Start up JupyterLab.
  
  ```
     jupyter-lab
  ```
  
- When prompted to select a kernel, choose the desired environment.  If not prompted, ensure that the kernel on the top right-hand corner of the page is set to the correct environment name.

- Proceed to using a Jupyter notebook of choice to reduce and analyze data.


## Troubleshooting and other installs

If there are errors during installation or later on, it might be necessary to install additional packages and then retry the pip installs.  Below is a list of what might be needed.

- Microsoft C++ Build Tools (https://visualstudio.microsoft.com/visual-cpp-build-tools/).  This is installed outside the Anaconda prompt.  Computer should be restarted after this installation.

- `pip install --upgrade holoviews`  This may be necessary if mask drawing is not working.  The `--upgrade` is necessary to ensure that the package will get upgraded even if some version of it is currently installed.

- `pip install natsort` allows use of the natsort package, but is not necessary for the main functioning of PyHyperScattering.

Also note that some installs might not work on the same line as `conda create`.  These can be installed after activating the environment.

- `pyhyperscattering[bluesky,ui]` may not install the necessary dependencies and may result in an older version of PyHyperScattering to be imported.  This might be an issue if trying to use a GUI to install packages (e.g., JupyterLab Desktop).
  
- Installs involving git cloning, such as installing a specific commit or branch.


## Optional notes on environment management

To exit out of an environment, `conda activate base` can be run.  Running `conda deactivate` also can achieve a similar result, but this should not be run if you are already in the base environment.

If there is an environment you want to delete, first ensire it is not active and then run `conda remove -n YOUR_ENVIRONMENT_NAME --all`.  The flat `--all` removes the entire environment.

## Additional resources
- Full list of PyHyperScattering dependencies: https://github.com/usnistgov/PyHyperScattering/blob/main/pyproject.toml
- Further guidance on creating and managing environments: https://jupyter.nsls2.bnl.gov/hub/guide
- Conda documentation: https://docs.conda.io/projects/conda/en/stable/
- Xarray documentation: https://docs.xarray.dev/en/stable/
- Numpy documentation: https://numpy.org/doc/2.1/
- MatPlotLib documentation: https://matplotlib.org/stable/index.html
