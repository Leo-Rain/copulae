from typing import Optional, Union
from warnings import warn

import numpy as np
import pandas as pd
from scipy.stats import beta

from copulae.copula import BaseCopula
from copulae.copula import Summary
from copulae.core import rank_data
from copulae.special import log_sum
from copulae.types import Array, EPSILON, Matrix, Ties
from copulae.utility.array import array_io_mcd
from .distribution import emp_dist_func

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

Smoothing = Literal['none', 'beta', 'checkerboard']


class EmpiricalCopula(BaseCopula[None]):
    """
    Given pseudo-observations from a distribution with continuous margins and copula, the empirical copula is
    the (default) empirical distribution function of these pseudo-observations. It is thus a natural nonparametric
    estimator of the copula.

    Examples
    --------
    >>> from copulae import EmpiricalCopula
    >>> from copulae.datasets import load_marginal_data
    >>> df = load_marginal_data()
    >>> df.head(3)
        STUDENT      NORM       EXP
    0 -0.485878  2.646041  0.393322
    1 -1.088878  2.906977  0.253731
    2 -0.462133  3.166951  0.480696
    >>> emp_cop = EmpiricalCopula(3, df, smoothing="beta")
    >>> data = emp_cop.data  # getting the pseudo-observation data (this is the converted df)
    >>> data[:3]
    array([[0.32522493, 0.1886038 , 0.55781406],
           [0.15161613, 0.39953349, 0.40953016],
           [0.33622126, 0.65611463, 0.62645785]])
    # must feed pseudo-observations into cdf
    >>> emp_cop.cdf(data[:2])
    array([0.06865595, 0.06320104])
    >>> emp_cop.pdf([[0.5, 0.5, 0.5]])
    0.009268568506099015
    >>> emp_cop.random(3, seed=10)
    array([[0.59046984, 0.98467178, 0.16494502],
           [0.31989337, 0.28090636, 0.09063645],
           [0.60379873, 0.61779407, 0.54215262]])
    """

    def __init__(self,
                 data: Matrix,
                 smoothing: Optional[Smoothing] = None,
                 ties: Ties = "average",
                 offset: float = 0):
        """
        Creates an empirical copula

        Parameters
        ----------
        data
            The margins data set for the empirical copula. This data need not be the pseudo-observations.
            The data set dimension must match the copula's dimension. If dim is not set, the dimension of
            the copula will be derived from the data's dimension. Data must be a matrix

        smoothing
            If not specified (default), the empirical distribution function or copula is computed. If "beta", the
            empirical beta copula is computed. If "checkerboard", the empirical checkerboard copula is computed.

        ties
            The method used to assign ranks to tied elements. The options are 'average', 'min', 'max', 'dense'
            and 'ordinal'.
            'average': The average of the ranks that would have been assigned to all the tied values is assigned
                to each value.
            'min': The minimum of the ranks that would have been assigned to all the tied values is assigned to
                each value. (This is also referred to as "competition" ranking.)
            'max': The maximum of the ranks that would have been assigned to all the tied values is assigned to
                each value.
            'dense': Like 'min', but the rank of the next highest element is assigned the rank immediately after
                those assigned to the tied elements. 'ordinal': All values are given a distinct rank, corresponding
                to the order that the values occur in `a`.

        offset
            Used in scaling the result for the density and distribution functions. Defaults to 0.
        """
        self.ties = ties
        self._offset = offset
        self._name = "Empirical"
        self.smoothing = smoothing

        assert data.ndim == 2 and data.shape
        self._data = data

        self._dim = data.shape[1]
        assert self.dim > 1, "Dimension must be >= 2"

        self.init_validate()

    @property
    def data(self):
        return self._data

    @array_io_mcd
    def cdf(self, u: Array, log=False) -> np.ndarray:
        if np.any(u > (1 + EPSILON)) or np.any(u < -EPSILON):
            raise ValueError("input array must be pseudo observations")

        uu = self.pobs(self._data, self.ties)  # pseudo-observations of source marginal to compare against
        cdf = emp_dist_func(u, uu, self._smoothing, self._offset)
        return np.log(cdf) if log else cdf

    def fit(self, data, x0=None, method='mpl', optim_options=None, ties='average', verbose=1):
        warn("EmpiricalCopula has no concept of 'fitting'")
        return self

    @property
    def params(self):
        """
        By default, the Empirical copula has no "parameters" as everything is defined by the input data
        """
        return None

    @array_io_mcd
    def pdf(self, u: Array, log=False):
        assert self.smoothing == "beta", "Empirical Copula only has density (PDF) for 'beta' smoothing"
        u = self.pobs(u, self.ties)

        data_rank = rank_data(self.data, 1, self.ties)
        n = len(self.data)

        if log:
            return np.array([
                log_sum(
                    np.array([
                        sum(beta.logpdf(row, a=row_rank, b=n + 1 - row_rank))
                        for row_rank in data_rank
                    ])
                ) for row in u]) - np.log(n + self._offset)
        else:
            return np.array([
                sum([
                    np.prod(beta.pdf(row, a=row_rank, b=n + 1 - row_rank))
                    for row_rank in data_rank
                ]) for row in u]) / (n + self._offset)

    def random(self, n: int, seed: int = None):
        if seed is not None:
            np.random.seed(seed)

        data = np.asarray(self.data)
        return self._format_output(data[np.random.randint(0, len(data), n)])

    @property
    def smoothing(self):
        """
        The smoothing parameter. "none" provides no smoothing. "beta" and "checkerboard" provide a smoothed
        version of the empirical copula. See equations (2.1) - (4.1) in Segers, Sibuya and Tsukahara

        References
        ----------
        `The Empirical Beta Copula <https://arxiv.org/pdf/1607.04430.pdf>`
        """
        return self._smoothing

    @smoothing.setter
    def smoothing(self, smoothing: Optional[Smoothing]):
        if smoothing is None:
            smoothing: Smoothing = "none"

        assert smoothing in ("none", "beta", "checkerboard"), "Smoothing must be 'none', 'beta' or 'checkerboard'"
        self._smoothing = smoothing

    def summary(self):
        return Summary(self, {
            "Dimensions": self.dim,
            "Ties method": self.ties,
            "Offset": self._offset,
            "Smoothing": self._smoothing,
        })

    def to_marginals(self, u: Union[np.ndarray, pd.DataFrame]) -> Union[pd.DataFrame, np.ndarray]:
        """
        Transforms a sample marginal data (pseudo-observations) to empirical margins based on the
        input dataset

        Parameters
        ----------
        u
            Sample marginals (pseudo observations). Values must be between [0, 1]

        Returns
        -------
        np.ndarray or pd.DataFrame
            Transformed marginals
        """
        # because it is pseudo-observations, and already ranked within the columns, we can just
        # multiply by the number of rows in the original data set to get the position rank
        index = np.floor(u * len(self.data)).astype(int)
        data = np.array(self.data)
        source = np.take_along_axis(np.array(data), data.argsort(axis=0), axis=0)

        # marginals derived row by row based on 'lowest' position, we could offer an interpolation in
        # the future, but not sure how popular this method is
        marginals = np.transpose([source[r, c] for c, r in enumerate(index.T)])
        return self._format_output(marginals)

    @property
    def ties(self):
        """
        The method used to assign ranks to tied elements. The options are 'average', 'min', 'max', 'dense'
        and 'ordinal'.

        'average':
            The average of the ranks that would have been assigned to all the tied values is assigned
            to each value.
        'min':
            The minimum of the ranks that would have been assigned to all the tied values is assigned to
            each value. (This is also referred to as "competition" ranking.)
        'max':
            The maximum of the ranks that would have been assigned to all the tied values is assigned to
            each value.
        'dense':
            Like 'min', but the rank of the next highest element is assigned the rank immediately after
            those assigned to the tied elements. 'ordinal': All values are given a distinct rank, corresponding
            to the order that the values occur in `a`.
        """
        return self._ties

    @ties.setter
    def ties(self, value: Ties):
        self._ties = value

    def _format_output(self, output: np.ndarray):
        """Converts output array to DataFrame if the input data is a DataFrame"""
        if isinstance(output, pd.DataFrame):
            return pd.DataFrame(output, columns=self.data.columns)
        return output
