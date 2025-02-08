
## This is intended to contain a revised set of default parameters that would be used after refactoring the codebase


## These parameters would be fed into _make_gscan_points function in nbs_bl.plans.scan_base with the format (start, stop, step, stop, step, etc.)
## In general, these are intended to recreate the energy lists from Eliot's old plan
## TODO: ideally, I would like to import _make_gscan_points locally to test these scan parameters
energyListParameters = {
    "carbon_NEXAFS":  (250, 282, 1.45, 297, 0.3, 350, 1.45), ## This is intended to recreate edge=(250, 282, 297, 350), ratios=(5, 1, 5), frames=112 often used for carbon-edge NEXAFS
    "oxygen_NEXAFS":  (500, 525, 1.1, 540, 0.2, 560, 1.1), ## Intended to recreate edge=(500, 525, 540, 560), ratios=(5, 1, 5), frames=112
    "fluorine_NEXAFS":  (650, 680, 1.5, 700, 0.3, 740, 1.5), ## Intended to recreate edge=(650, 680, 700, 740), ratios=(5, 1, 5), frames=112
    "sulfurL_NEXAFS":  (150, 160, 0.8, 170, 0.15, 200, 0.8), ## Intended to recreate edge=(150, 160, 170, 200), ratios=(5, 1, 5), frames=112
}