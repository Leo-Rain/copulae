from copulae.utility.special_func import *
import pytest


@pytest.mark.parametrize('n, k, exp', [
    (5, 3, 35),
    (8, 4, 6769),
    (8, 5, 1960),
    (7, 2, 1764),
])
def test_stirling_first(n, k, exp):
    assert stirling_first(n, k) == exp


@pytest.mark.parametrize('n, k, exp', [
    (5, 3, 25),
    (8, 4, 1701),
    (8, 5, 1050),
    (6, 5, 15),
])
def test_stirling_second(n, k, exp):
    assert stirling_second(n, k) == exp


@pytest.mark.parametrize('n, exp', [
    (7, [720, 1764, 1624, 735, 175, 21, 1]),
    (8, [5040, 13068, 13132, 6769, 1960, 322, 28, 1])
])
def test_stirling_first_all(n, exp):
    assert stirling_first_all(n) == exp


@pytest.mark.parametrize('n, exp', [
    (7, [1, 63, 301, 350, 140, 21, 1]),
    (8, [1, 127, 966, 1701, 1050, 266, 28, 1])
])
def test_stirling_second_all(n, exp):
    assert stirling_second_all(n) == exp


# noinspection PyTypeChecker
@pytest.mark.parametrize('n, k', [
    (5.5, 0.4),
    ([1, 2, 3], [4, 5, 6])
])
def test_raises_type_error(n, k):
    match = '<k> and <n> must both be integers'
    with pytest.raises(TypeError, match=match):
        stirling_second(n, k)
    with pytest.raises(TypeError, match=match):
        stirling_first(n, k)


@pytest.mark.parametrize('n, k', [
    (4, 6),
    (4, -1)
])
def test_raises_value_error(n, k):
    match = r'<k> must be in the range of \[0, <n>\]'
    with pytest.raises(ValueError, match=match):
        stirling_second(n, k)

    with pytest.raises(ValueError, match=match):
        stirling_first(n, k)