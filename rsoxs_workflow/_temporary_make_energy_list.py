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
