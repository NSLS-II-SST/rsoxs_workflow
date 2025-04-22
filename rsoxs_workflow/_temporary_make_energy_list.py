## This file is for drafting purposes and not meant to be imported elsewhere.

## This is Jamie's original function.
def _make_gscan_points(*args, shift: float = 0):
    if len(args) < 3:
        raise TypeError(
            f"gscan requires at least estart, estop, and delta, received {args}"
        )
    if len(args) % 2 == 0:
        raise TypeError(
            "gscan received an even number of arguments. Either a step or a step-size is missing" ## Is it meant to say "Either a stop or a step-size is missing"?
        )
    start = float(args[0])
    points = [start + shift]
    for stop, step in zip(args[1::2], args[2::2]): ## Bookmark: TODO: look up what zip does
        nextpoint = points[-1] + step
        while nextpoint < stop - step / 2.0 + shift:
            points.append(nextpoint)
            nextpoint += step
        points.append(stop + shift)
    return points



## Things I would like to change: 
## Be able to easily reverse energy list --> Scanning in forward and reverse direction can give informaiton about reproducibility of motor as well as sample damage
## Allow single-energy lists.  Currently, if I put a list such as [250, 250, 0], it makes a list of [250, 250]
## Reorganize the format such that it is [start, step, stop...] instead of [start, stop, step].  This would make it easier to reverse energy lists, as the parameter list can just be reversed and fed into the function.  This change would break the current energy lists Jamie has and possibly his GUI, so this requires significant coordination.


## Made the new function below with the help of chatgpt
def _make_gscan_points(*args, shift: float = 0):
    """
    Generate a sequence of energy scan points from a variable-length parameter list.

    Parameters should be passed in the following format:
        (estart1, delta1, estop1, delta2, estop2, ...)

    - Each segment defines a range starting from the given estart and ending at the estop,
      using the specified delta (step size).
    - Delta values must be positive. The function automatically determines the direction
      (increasing or decreasing) based on the estart and estop values.
    - A single energy value can be passed to return a single-point list.
    - Segments can be non-monotonic — i.e., you can mix increasing and decreasing ranges.
    - An optional `shift` parameter can be used to apply a constant offset to all values.

    Examples:
        _make_gscan_points(250)
            ➜ [250.0]

        _make_gscan_points(250, 5, 260)
            ➜ [250.0, 255.0, 260.0]

        _make_gscan_points(264, 2, 260, 5, 250)
            ➜ [264.0, 262.0, 260.0, 255.0, 250.0]  # reverse energy list

    Raises:
        TypeError if the number of arguments is incorrect
        ValueError if any delta is zero
    """
    if len(args) == 1:
        return [float(args[0]) + shift]

    if (len(args) - 1) % 2 != 0:
        raise TypeError(
            "gscan received an incomplete set of arguments. Either a stop or a step-size is missing.  Expected format: (estart1, delta1, estop1, delta2, estop2, ...)"
        )

    points = []

    for i in range(1, len(args) - 1, 2):
        estart = float(args[i - 1]) + shift
        delta = abs(args[i]) ## Ensures delta is positive in case users input negative delta for reverse energy list.
        estop = float(args[i + 1]) + shift

        if delta == 0:
            raise ValueError("Step size (delta) cannot be zero.")

        step = delta if estop > estart else -delta

        if not points or points[-1] != estart:
            points.append(estart)

        next_point = estart + step
        while (step > 0 and next_point < estop - step / 2.0) or (step < 0 and next_point > estop - step / 2.0):
            points.append(next_point)
            next_point += step

        points.append(estop)

    return points


## Draft issue
"""
Title: Modify _make_gscan_points to support reversibility, single-energy lists, and readability

Body:
There are a few changes that I would like to propose for _make_gscan_points based on my experience this past cycle, detailed below.
1. Updated parameter format.  The input format has been changed from (estart1, estart2, delta1, estop2, delta2, ...) to (estart1, delta1, estop1, delta2, estop2, ...), which I think might be more readable and also make it easier to reverse the energy list direction, as detailed in the next point below.
2. Support for reverse energy lists.  The function now correctly handles decreasing energy ranges without requiring negative delta values. It automatically determines the step direction based on the estart and estop values.  This combined with point 1 means we can just feed in the .reverse() version of *args to get the reverse energy list.  Technically, this can support non-monotonic energy lists too, though I do not plan to place emphasis on this.  In practice, I plan to encourage users to have the forward and reverse energy scans as separate scans and then to stack them during downstream data processing if needed.
3. Support for single-point energy lists.  The function now allows a single energy value as input (e.g., _make_gscan_points(250)) and returns [250.0]. This is useful for scans with only one point, especially if we would like multiple exposures/images at a single energy at RSoXS.
4. Added a docstring with examples for forward, reverse, and single-point energy lists.

I have drafted changes in a branch (XXX), and wanted to check what else might need to be updated before drafting a PR.  Below are a couple things I thought of, but I'm probably missing others.
- The XAS default energy list parameters .toml file would need to be modified.  Is that something we could run through a function that auto-updates to the new format and generates a new .toml file?
- The GUI might need updating so that the requested inputs are in the new format.

"""
