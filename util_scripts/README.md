# TCK Utility Scripts

This directory contains scripts used for maintaining the A2A Technology Compatibility Kit (TCK), primarily related to managing specification updates and analyzing test coverage.

## User-Facing Scripts

These scripts are intended to be run manually by TCK maintainers.

### `check_spec_changes.py`

Analyzes and reports the differences between the current baseline A2A specification and a target version (e.g., a branch or tag in the official repository). This is the first step in the specification update workflow.

**Important Change**: This tool now uses **a2a.proto as the source of truth** instead of JSON schema.

*   **Usage**: `util_scripts/check_spec_changes.py [options]`
*   **Current Spec Files Required**:
    - `current_spec/a2a.proto` (proto specification - source of truth)
    - `current_spec/specification.md` (markdown documentation)
*   **Download Spec Files**: Run `./update_spec.sh` to download the latest specification files
*   **Detailed Documentation**: See the [Specification Update Workflow](../docs/SPEC_UPDATE_WORKFLOW.md)
*   **Architecture Decision**: See [ADR-003: Proto-First Code Generation](../docs/adrs/ADR-003-proto-first-code-generation.md)

**Example Usage**:
```bash
# Compare current spec against main branch
./util_scripts/check_spec_changes.py

# Compare against specific branch
./util_scripts/check_spec_changes.py --branch v1.2.0

# Generate detailed report
./util_scripts/check_spec_changes.py --output reports/analysis.md --verbose
```

The tool now:
- Parses proto messages, services, RPC methods, and enums
- Compares proto structures instead of JSON schema
- Maintains backward compatibility with existing report formats

## Internal Modules

The following files are not intended to be executed directly. They are modules imported by other scripts (`run_tck.py`).

*   `__init__.py`: Marks this directory as a Python package.
*   `compliance_levels.py`: Defines the logic and thresholds for the different A2A compliance levels.
*   `generate_compliance_report.py`: Contains the logic for generating the final JSON compliance report. 