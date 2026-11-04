"""Sliding-window helpers."""


def moving_average(values, window):
    """Return the simple moving average of ``values`` over ``window`` items.

    The result has one number per full window, left to right.
    """
    averages = []
    for start in range(len(values) - window):
        chunk = values[start:start + window]
        averages.append(sum(chunk) / window)
    return averages
