"""Necessary single-class patch bounds from stored aggregates, never a gate.

No per-patch distribution, new data volume or redistribution recommendation is
inferred. The original stored-requirements result stays embedded unchanged.
"""
from . import bare_class_requirements as requirements


REPORT_RELATIVE = requirements.REPORT_RELATIVE
OUTPUT_CAP = requirements.OUTPUT_CAP
PATCH_PIXEL_CAPACITY = 256 * 256  # Enforced patch_size in the reused 76 contract.
FALSE_FIELDS = {
    'per_patch_distribution_reconstructed', 'pixels_rechecked', 'eligibility_recomputed',
    'ready_for_training', 'scientific_accuracy_validated', 'execution_authorized',
    'collection_authorized', 'training_executed', 'new_scene_count_estimated',
    'download_volume_estimated', 'future_pixel_requirement_estimated',
    'redistribution_recommended', 'relabeling_authorized', 'requirements_are_full_gate',
    'source_authenticity_verified', 'exact_label_requirement_verified',
    'source_manifest_currently_verified', 'spatial_overlap_rechecked',
    'training_split_leakage_resolved', 'policy_thresholds_changed',
}


def _contribution_bounds(eligible, pixels, threshold, capacity):
    """Integer capacity model only; small capacities also support oracle tests."""
    requirements._need(type(eligible) is int and 0 <= eligible <= 3000)
    requirements._need(type(capacity) is int and 1 <= capacity <= 65536)
    requirements._need(type(threshold) is int and 1 <= threshold <= capacity)
    requirements._need(type(pixels) is int and 0 <= pixels <= eligible * capacity)
    numerator = pixels - eligible * (threshold - 1)
    denominator = capacity - threshold + 1
    lower = max(0, -(-numerator // denominator))
    upper = min(eligible, pixels // threshold)
    return lower, upper


def _project(stored_requirements):
    by_split = {}
    for split in ('train', 'val', 'test'):
        source = stored_requirements['by_split'][split]
        eligible = source['eligible_patches']
        pixels = source['bare_pixels']
        threshold = source['minimum_bare_pixels_per_contributing_patch']
        required = source['minimum_contributing_class_patches']
        observed = source['contributing_class_patches']
        lower, upper = _contribution_bounds(eligible, pixels, threshold, PATCH_PIXEL_CAPACITY)
        by_split[split] = {
            'eligible_patches': eligible, 'bare_pixels': pixels,
            'observed_contributing_patches': observed,
            'minimum_bare_pixels_per_contributing_patch': threshold,
            'patch_pixel_capacity': PATCH_PIXEL_CAPACITY,
            'minimum_contributing_patches_from_aggregate': lower,
            'maximum_contributing_patches_from_aggregate': upper,
            'observed_count_within_aggregate_bounds': lower <= observed <= upper,
            'required_contributing_patches': required,
            'eligible_patch_capacity_supports_required_count': eligible >= required,
            'aggregate_upper_bound_supports_required_count': upper >= required,
            'minimum_total_bare_pixels_necessary_for_required_count': required * threshold,
            'necessary_total_bare_pixel_shortfall': max(0, required * threshold - pixels),
        }
    inconsistent = [split for split, value in by_split.items()
                    if not value['observed_count_within_aggregate_bounds']]
    return {
        'schema_version': 1, 'kind': 'BARE_CLASS_PATCH_AGGREGATE_FEASIBILITY',
        'status': 'BLOCKED', 'scope': 'STORED_AGGREGATE_NECESSARY_BOUNDS_ONLY',
        'stored_requirements': stored_requirements,
        'class_index': 7, 'class_name': 'bare', 'by_split': by_split,
        'stored_contributing_counts_within_aggregate_bounds': not inconsistent,
        'inconsistent_splits': inconsistent,
        **{field: False for field in sorted(FALSE_FIELDS)},
        'network_requests': 0, 'source_files_written': 0,
        'limitation': ('Single-class integer capacity model of the same counted eligible patches only. '
            'Bounds and necessary-total differences are not a reconstructed histogram, sufficient QA '
            'conditions, redistribution advice, or future pixels/scenes/download requirements. '
            'All original fixed splits, quality, labels, ratio, overlap and approval gates remain unchanged.'),
    }


def build_bare_patch_feasibility(report, reference):
    """Use 76 once; a pure caller reference does not verify report file bytes."""
    return _project(requirements.build_bare_class_requirements(report, reference))


def inspect_bare_patch_feasibility(data_root, expected_report_sha256):
    """Reuse 76's pinned single-report reader once, with no extra file reads."""
    return _project(requirements.inspect_bare_class_requirements(data_root, expected_report_sha256))
