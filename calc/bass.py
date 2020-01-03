import pandas as pd
import math
import scipy.optimize
from numba import jit


@jit(nopython=True)
def _bass_diffuse(t, m, p, q):
    e1 = math.e ** (-(p + q) * t)
    res = ((p + q) ** 2) / p
    res *= e1 / ((1 + q / p * e1) ** 2)
    res *= m
    return res


@jit(nopython=True)
def _generate_bass_series(t, y0, m, p, q):
    y = y0
    vals = []
    for t in range(0, t):
        f = _bass_diffuse(t, m, p, q)
        y *= 1 + f
        vals.append(y)
    return vals


@jit(nopython=True)
def _test_bass(x, t, y_start, y_end):
    m, p, q = x
    s = _generate_bass_series(t + 10, y_start, m, p, q)
    summed = 0
    for i in range(1, 10):
        summed += (y_end - s[-i]) ** 2
        summed += (s[0] - y_start) ** 2
    return summed


def generate_bass_diffusion(x_start, x_end, y_start, y_end, p=None, q=None):
    x_diff = x_end - x_start

    x0 = [1, 0.03, 0.38]
    if p is not None:
        p_bounds = (p, p)
    else:
        p_bounds = (0.001, 1)
    if q is not None:
        q_bounds = (q, q)
    else:
        q_bounds = (0.001, 1)
    res = scipy.optimize.minimize(
        _test_bass, x0, args=(x_diff, y_start, y_end),
        bounds=[(0, None), p_bounds, q_bounds]
    )
    m, p, q = res.x
    s = _generate_bass_series(x_diff, y_start, m, p, q)
    return pd.Series(data=[y_start] + s, index=range(x_start, x_end + 1))


if __name__ == '__main__':
    print(generate_bass_diffusion(2019, 2035, 0.01, 0.90))
