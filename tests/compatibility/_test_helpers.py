"""Shared test helper functions for compatibility tests.

Provides ``fail_msg``, ``record``, ``get_client``, and
``collect_events_with_timeout`` — utilities used across all conformance
test modules.
"""

from __future__ import annotations

import threading

from typing import TYPE_CHECKING, Any

import pytest


if TYPE_CHECKING:
    from tck.requirements.base import RequirementSpec
    from tck.transport.base import BaseTransportClient


def fail_msg(req: RequirementSpec, transport: str, detail: str) -> str:
    """Build a failure message referencing the requirement."""
    return (
        f"{req.id} [{req.title}] failed on {transport}: "
        f"{detail} (see {req.spec_url})"
    )


def record(
    collector: Any,
    req: RequirementSpec,
    transport: str,
    passed: bool,
    errors: list[str] | None = None,
    *,
    skipped: bool = False,
) -> None:
    """Record a result in the compatibility collector."""
    collector.record(
        requirement_id=req.id,
        transport=transport,
        level=req.level.value,
        passed=passed,
        errors=errors or [],
        skipped=skipped,
    )


def assert_and_record(
    collector: Any,
    req: RequirementSpec,
    transport: str,
    errors: list[str],
) -> None:
    """Record the result and assert no errors."""
    passed = not errors
    record(collector, req, transport, passed=passed, errors=errors)
    assert passed, fail_msg(req, transport, "; ".join(errors))


def get_client(
    transport_clients: dict[str, BaseTransportClient],
    transport: str,
    *,
    compatibility_collector: Any = None,
    req: Any = None,
) -> BaseTransportClient:
    """Get the transport client, skipping if not configured."""
    client = transport_clients.get(transport)
    if client is None:
        if compatibility_collector is not None and req is not None:
            record(compatibility_collector, req, transport, passed=False, skipped=True)
        pytest.skip(f"Transport {transport!r} not configured")
    return client


_DEFAULT_STREAM_TIMEOUT_S = 10


def collect_events_with_timeout(
    events_iter: Any,
    timeout: float = _DEFAULT_STREAM_TIMEOUT_S,
    *,
    stop_after_first: bool = False,
) -> tuple[list[Any], bool]:
    """Collect streaming events with a hard wall-clock timeout.

    Runs event consumption in a daemon thread so that we can enforce
    the deadline even when ``next(events_iter)`` itself blocks
    (e.g. an SSE connection waiting for data that never arrives).

    When *stop_after_first* is ``True`` the iterator is abandoned after the
    first event — used to simulate a client closing a stream early.

    Returns a tuple of (events, timed_out).
    """
    collected: list[Any] = []

    def _drain() -> None:
        for event in events_iter:
            collected.append(event)
            if stop_after_first:
                break

    thread = threading.Thread(target=_drain, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    timed_out = thread.is_alive()
    return collected, timed_out


def validate_schema(
    response: Any,
    transport: str,
    validators: dict[str, Any],
    schema_ref: str,
) -> list[str]:
    """Validate a transport response against a schema definition.

    Args:
        response: Transport response with a ``raw_response`` attribute.
        transport: Transport name (``"grpc"``, ``"jsonrpc"``, ``"http_json"``).
        validators: Dict of validators keyed by transport name.
        schema_ref: Schema reference constant (e.g. ``TASK``, ``SEND_MESSAGE_RESPONSE``).

    Returns:
        A list of error strings (empty if valid).
    """
    validator = validators.get(transport)
    if validator is None:
        return []
    result = validator.validate(response.raw_response, schema_ref)
    return result.errors if not result.valid else []


def validate_streaming_events(
    events: list[Any],
    transport: str,
    validators: dict[str, Any],
    schema_ref: str,
    *,
    prefix: str = "Event",
) -> list[str]:
    """Validate a list of streaming events against a schema definition.

    Args:
        events: List of streaming events (proto messages or dicts).
        transport: Transport name.
        validators: Dict of validators keyed by transport name.
        schema_ref: Schema reference constant (e.g. ``STREAM_RESPONSE``).
        prefix: Label prefix for error messages (e.g. ``"Stream 0 event"``).

    Returns:
        A list of error strings (empty if all events are valid).
    """
    validator = validators.get(transport)
    if validator is None:
        return []
    errors: list[str] = []
    for i, event in enumerate(events):
        result = validator.validate(event, schema_ref)
        if not result.valid:
            errors.extend(f"{prefix} {i}: {e}" for e in result.errors)
    return errors
