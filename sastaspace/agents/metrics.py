# sastaspace/agents/metrics.py
"""Prometheus metrics for the Agno multi-agent redesign pipeline."""
from __future__ import annotations

from prometheus_client import Counter, Histogram

# Pipeline-level metrics
redesign_pipeline_duration_seconds = Histogram(
    "redesign_pipeline_duration_seconds",
    "Total duration of the redesign pipeline in seconds",
    labelnames=["tier", "status"],
    buckets=(5, 10, 30, 60, 120, 300, 600),
)

redesign_pipeline_total = Counter(
    "redesign_pipeline_total",
    "Total number of redesign pipeline runs",
    labelnames=["tier", "status"],
)

# Per-agent metrics
redesign_agent_duration_seconds = Histogram(
    "redesign_agent_duration_seconds",
    "Duration of individual agent execution in seconds",
    labelnames=["agent_name", "status"],
    buckets=(1, 5, 10, 30, 60, 120, 300),
)

redesign_agent_tokens_total = Counter(
    "redesign_agent_tokens_total",
    "Total tokens used by agents",
    labelnames=["agent_name", "direction"],
)

# Guardrail metrics
redesign_guardrail_triggers_total = Counter(
    "redesign_guardrail_triggers_total",
    "Total number of guardrail triggers",
    labelnames=["guardrail_name", "action"],
)
