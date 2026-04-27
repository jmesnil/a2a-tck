---
id: TASK-26
title: Add schema validation to response-handling tests
status: Done
assignee: []
created_date: '2026-04-27 15:36'
updated_date: '2026-04-27 15:42'
labels:
  - schema-validation
  - test-quality
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Following the pattern established in TASK-25 (streaming event schema validation), add `validator.validate(data, SCHEMA_REF)` calls to test files that currently do only manual field checking on protocol responses.

## Motivation

Several test files manually check response structure (artifact fields, task IDs, history content) without first validating the response against the A2A JSON/proto schema. Adding schema validation catches structural conformance issues early and lets manual checks focus on behavioral/content assertions.

## Files to update

### 1. `tests/compatibility/core_operations/test_artifacts.py`
- 5 test classes, none use schema validation
- Add `validator.validate(response.raw_response, SEND_MESSAGE_RESPONSE)` before content checks
- Simplifies `TestFileArtifact` and `TestFileUrlArtifact` which duplicate inline artifact structure validation

### 2. `tests/compatibility/core_operations/test_task_lifecycle.py`
- 4 test classes, none use schema validation
- `TestGetTask` / `TestCancelTask`: add `TASK` schema validation on GetTask/CancelTask responses
- `TestMultiTurn`: add `SEND_MESSAGE_RESPONSE` validation on successful SendMessage responses
- `TestSubscribeLifecycle`: add per-event `STREAM_RESPONSE` validation on streaming events

### 3. `tests/compatibility/core_operations/test_task_history.py`
- 5 test classes, none use schema validation
- Add `TASK` schema validation on GetTask/SendMessage responses before history content checks

### 4. `tests/compatibility/core_operations/test_multi_stream.py`
- 1 test class, no schema validation
- Add per-event `STREAM_RESPONSE` validation on collected streaming events

## Pattern to follow

From task-25 and `test_stream_ordering.py`:
```python
validator = validators[transport]
for i, event in enumerate(events):
    result = validator.validate(event, STREAM_RESPONSE)
    if not result.valid:
        errors.extend(f"Event {i}: {e}" for e in result.errors)
```

## Out of scope

- Error handling tests (use specialized error validators intentionally)
- Agent card caching tests (test HTTP headers, not payloads)
- Files already using schema validation (test_data_model.py, test_stream_ordering.py, test_sse_streaming.py, test_streaming.py)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 test_artifacts.py uses SEND_MESSAGE_RESPONSE schema validation
- [x] #2 test_task_lifecycle.py uses TASK, SEND_MESSAGE_RESPONSE, and STREAM_RESPONSE schema validation as appropriate
- [x] #3 test_task_history.py uses TASK schema validation on responses
- [x] #4 test_multi_stream.py uses STREAM_RESPONSE schema validation on streaming events
- [x] #5 All existing tests continue to pass
- [x] #6 validators fixture is added to test methods that need it
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added schema validation to 4 test files following the pattern established in TASK-25:\n\n- **test_artifacts.py**: Added `SEND_MESSAGE_RESPONSE` validation to all 5 test methods via a shared `_validate_response_schema()` helper. Removed redundant manual `artifactId` checks from `TestFileArtifact` and `TestFileUrlArtifact` (now covered by schema). Removed unused `get_artifact_id` import.\n\n- **test_task_lifecycle.py**: Added `TASK` validation to GetTask/CancelTask responses, `SEND_MESSAGE_RESPONSE` to SendMessage responses, and per-event `STREAM_RESPONSE` validation to SubscribeToTask events via a shared `_validate_schema()` helper.\n\n- **test_task_history.py**: Added `TASK` validation to all GetTask responses and `SEND_MESSAGE_RESPONSE` to SendMessage responses across all 6 test methods via a shared `_validate_schema()` helper.\n\n- **test_multi_stream.py**: Added per-event `STREAM_RESPONSE` validation to all 3 multi-stream test methods.\n\nAll 250 unit tests pass. Ruff lint clean across the full compatibility test suite.
<!-- SECTION:FINAL_SUMMARY:END -->
