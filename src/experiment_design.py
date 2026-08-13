from dataclasses import dataclass
from math import ceil, sqrt
from statistics import NormalDist


@dataclass(frozen=True)
class SampleSizePlan:
    baseline_rate: float
    target_rate: float
    relative_mde: float
    alpha: float
    power: float
    sample_size_per_variant: int


def calculate_sample_size_per_variant(
    baseline_rate: float,
    relative_mde: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> SampleSizePlan:
    """Estimate equal-arm sample size for a two-sided two-proportion test."""
    if not 0 < baseline_rate < 1:
        raise ValueError("baseline_rate must be between 0 and 1.")
    if relative_mde <= 0:
        raise ValueError("relative_mde must be greater than 0.")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1.")
    if not 0 < power < 1:
        raise ValueError("power must be between 0 and 1.")

    target_rate = baseline_rate * (1 + relative_mde)
    if target_rate >= 1:
        raise ValueError("baseline_rate multiplied by the MDE must remain below 1.")

    normal_distribution = NormalDist()
    critical_value = normal_distribution.inv_cdf(1 - alpha / 2)
    power_value = normal_distribution.inv_cdf(power)
    pooled_rate = (baseline_rate + target_rate) / 2
    null_standard_error = sqrt(2 * pooled_rate * (1 - pooled_rate))
    alternative_standard_error = sqrt(
        baseline_rate * (1 - baseline_rate)
        + target_rate * (1 - target_rate)
    )
    effect_size = target_rate - baseline_rate
    sample_size = ceil(
        (
            critical_value * null_standard_error
            + power_value * alternative_standard_error
        )
        ** 2
        / effect_size**2
    )

    return SampleSizePlan(
        baseline_rate=baseline_rate,
        target_rate=target_rate,
        relative_mde=relative_mde,
        alpha=alpha,
        power=power,
        sample_size_per_variant=sample_size,
    )


def calculate_required_days(
    sample_size_per_variant: int,
    eligible_exposures_per_day: float,
    variant_allocation: float = 0.50,
) -> int:
    """Return calendar days needed for each equal-size experiment arm."""
    if sample_size_per_variant < 1:
        raise ValueError("sample_size_per_variant must be at least 1.")
    if eligible_exposures_per_day <= 0:
        raise ValueError("eligible_exposures_per_day must be greater than 0.")
    if not 0 < variant_allocation <= 1:
        raise ValueError("variant_allocation must be between 0 and 1.")

    daily_exposures_per_variant = eligible_exposures_per_day * variant_allocation
    return ceil(sample_size_per_variant / daily_exposures_per_variant)
