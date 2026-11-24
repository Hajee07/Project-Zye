"""
Uncertainty Distribution & Correlated Sampling Engine (Day 37 / Phase 3).
Provides mathematically rigorous stochastic sampling across Normal, Uniform,
Truncated Normal, and Correlated Multivariates with covariance validation.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple, Union
import numpy as np

from zye_realtime_tactical.kinematics.kinematic_models import DistributionType


class CovarianceValidationError(ValueError):
    """Raised when an empirical or user-provided covariance matrix violates mathematical properties."""
    pass


class UncertaintyDistributionSampler:
    """High-speed vectorized stochastic generator for state and parameter uncertainties."""

    @classmethod
    def sample_perturbations(
        cls,
        base_vector: np.ndarray,
        std_vector: Optional[np.ndarray],
        cov_matrix: Optional[np.ndarray],
        sample_count: int,
        distribution_type: DistributionType = DistributionType.NORMAL,
        rng: Optional[np.random.Generator] = None,
        lower_bound: Optional[np.ndarray] = None,
        upper_bound: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Generates shape (N, dim) stochastic perturbation array centered around base_vector.
        Uses numpy.random.Generator with vectorization for high throughput.
        """
        generator = rng if rng is not None else np.random.default_rng()
        dim = base_vector.shape[0]

        # Case 1: Correlated Multivariate Uncertainty via Covariance Matrix
        if cov_matrix is not None:
            cls.validate_covariance_matrix(cov_matrix, dim)
            samples = generator.multivariate_normal(
                mean=base_vector,
                cov=cov_matrix,
                size=sample_count,
                check_valid="ignore",
            )
            return cls._apply_bounds(samples, lower_bound, upper_bound)

        # Standard deviations default to zero if absent
        std = std_vector if std_vector is not None else np.zeros(dim, dtype=np.float64)
        if std.shape[0] != dim:
            raise ValueError(f"std_vector dimension mismatch: expected {dim}, got {std.shape[0]}")

        # If zero uncertainty, broadcast base vector
        if np.all(std <= 1e-12):
            return np.tile(base_vector, (sample_count, 1))

        # Case 2: Independent Uniform Distribution [base - sqrt(3)*std, base + sqrt(3)*std]
        # (Variance of Uniform[-w, w] is w^2 / 3, so w = std * sqrt(3))
        if distribution_type == DistributionType.UNIFORM:
            half_width = std * math.sqrt(3.0)
            low = base_vector - half_width
            high = base_vector + half_width
            samples = generator.uniform(low=low, high=high, size=(sample_count, dim))
            return cls._apply_bounds(samples, lower_bound, upper_bound)

        # Case 3: Independent Normal / Gaussian Distribution
        samples = generator.normal(loc=base_vector, scale=std, size=(sample_count, dim))

        # Case 4: Truncated Normal (clipping bounds or rejection)
        if distribution_type == DistributionType.TRUNCATED_NORMAL or lower_bound is not None or upper_bound is not None:
            samples = cls._apply_bounds(samples, lower_bound, upper_bound)

        return samples

    @staticmethod
    def _apply_bounds(
        samples: np.ndarray,
        lower_bound: Optional[np.ndarray] = None,
        upper_bound: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Enforce physical boundaries (e.g. non-negative radii, delays)."""
        res = samples
        if lower_bound is not None:
            res = np.maximum(res, lower_bound)
        if upper_bound is not None:
            res = np.minimum(res, upper_bound)
        return res

    @staticmethod
    def validate_covariance_matrix(cov: np.ndarray, expected_dim: int) -> None:
        """
        Mathematically verifies that a covariance matrix is square, symmetric,
        finite, and positive semi-definite (all eigenvalues >= -1e-8).
        """
        if cov.ndim != 2:
            raise CovarianceValidationError(f"Covariance matrix must be 2D, got shape {cov.shape}")
        if cov.shape[0] != expected_dim or cov.shape[1] != expected_dim:
            raise CovarianceValidationError(
                f"Covariance matrix dimension mismatch: expected ({expected_dim}, {expected_dim}), got {cov.shape}"
            )
        if not np.all(np.isfinite(cov)):
            raise CovarianceValidationError("Covariance matrix contains non-finite values (NaN or Inf)")

        # Symmetry check: cov == cov.T
        if not np.allclose(cov, cov.T, atol=1e-7):
            raise CovarianceValidationError("Covariance matrix is not symmetric (cov != cov.T)")

        # Positive semi-definiteness: eigenvalues >= 0
        eigenvalues = np.linalg.eigvalsh(cov)
        min_eig = float(np.min(eigenvalues))
        if min_eig < -1e-6:
            raise CovarianceValidationError(
                f"Covariance matrix is not positive semi-definite (min eigenvalue = {min_eig:.6e} < 0)"
            )
