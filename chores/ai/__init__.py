"""Anthropic-backed AI setup.

Everything that talks to the Anthropic API lives in :mod:`chores.ai.setup`,
behind ``generate_plan`` which returns a parsed plan or raises. The client is
injectable so tests (and CI) run without a key or a network.
"""
