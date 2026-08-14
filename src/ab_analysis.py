from dataclasses import dataclass
from math import erfc, sqrt
from statistics import NormalDist


@dataclass(frozen=True)
class ProportionComparison:
    control_rate: float
    treatment_rate: float
    absolute_difference: float
    relative_lift: float
    standard_error: float
    confidence_interval_low: float
    confidence_interval_high: float
    p_value: float


def compare_proportions(
    control_successes: int,
    control_total: int,
    treatment_successes: int,
    treatment_total: int,
    alpha: float = 0.05,
) -> ProportionComparison:
    """Calculate a two-sided normal-approximation comparison of two proportions."""
    if control_total < 1 or treatment_total < 1:
        raise ValueError("Each variant must have at least one assigned visitor.")
    if not 0 <= control_successes <= control_total:
        raise ValueError("control_successes must be between 0 and control_total.")
    if not 0 <= treatment_successes <= treatment_total:
        raise ValueError("treatment_successes must be between 0 and treatment_total.")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1.")

    control_rate = control_successes / control_total
    treatment_rate = treatment_successes / treatment_total
    absolute_difference = treatment_rate - control_rate
    standard_error = sqrt(
        control_rate * (1 - control_rate) / control_total
        + treatment_rate * (1 - treatment_rate) / treatment_total
    )
    critical_value = NormalDist().inv_cdf(1 - alpha / 2)
    test_statistic = absolute_difference / standard_error if standard_error else 0
    p_value = erfc(abs(test_statistic) / sqrt(2)) if standard_error else 1.0
    relative_lift = (
        absolute_difference / control_rate if control_rate else float("inf")
    )

    return ProportionComparison(
        control_rate=control_rate,
        treatment_rate=treatment_rate,
        absolute_difference=absolute_difference,
        relative_lift=relative_lift,
        standard_error=standard_error,
        confidence_interval_low=absolute_difference - critical_value * standard_error,
        confidence_interval_high=absolute_difference + critical_value * standard_error,
        p_value=p_value,
    )


def sample_ratio_mismatch_p_value(
    control_total: int,
    treatment_total: int,
) -> float:
    """Return a two-sided chi-square p-value for an expected 50/50 split."""
    if control_total < 0 or treatment_total < 0:
        raise ValueError("Assignment counts cannot be negative.")

    total_assigned = control_total + treatment_total
    if total_assigned == 0:
        raise ValueError("At least one visitor must be assigned.")

    expected_per_variant = total_assigned / 2
    chi_square_statistic = (
        (control_total - expected_per_variant) ** 2 / expected_per_variant
        + (treatment_total - expected_per_variant) ** 2 / expected_per_variant
    )
    return erfc(sqrt(chi_square_statistic / 2))
