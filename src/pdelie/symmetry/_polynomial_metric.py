from __future__ import annotations

"""Private polynomial metric helpers shared by runtime symmetry diagnostics."""


def _monomial_average_inner_product(powers_a: tuple[int, ...], powers_b: tuple[int, ...]) -> float:
    value = 1.0
    for power_a, power_b in zip(powers_a, powers_b):
        total_power = int(power_a) + int(power_b)
        if total_power % 2 == 1:
            return 0.0
        value *= 1.0 / float(total_power + 1)
    return value


__all__ = ["_monomial_average_inner_product"]
