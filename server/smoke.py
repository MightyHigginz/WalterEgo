#!/usr/bin/env python3
"""Live smoke test (spends a few cents): needs ANTHROPIC_API_KEY. Asks a question that requires the statute tools."""
import os, sys
os.environ.setdefault("TAX_DATA_ROOT", "/tmp/taxsuite-smoke")
import anthropic, agent
r = agent.run_agent(anthropic.Anthropic(), "smoke-test", [{"role": "user", "content": agent.add_context("What are the Kleinunternehmer turnover limits for 2026? Quote the statute.")}])
print(r["status"], r["tool_calls"], r["usage"]); print(r["answer"])
assert "25" in r["answer"] and "100" in r["answer"], "unexpected answer"
assert r["tool_calls"], "the model answered without using the statute tools"
