#!/usr/bin/env python3
"""Convenience entry point: `python run_demo.py [--online] [--llm]`.

Runs the two bundled worked examples. Offline by default (uses shipped fixtures
in demo_data/fixtures) so it works with no network; pass --online to refresh
from EBI OLS / Europe PMC. Deterministic by default; pass --llm to enable an
LLM planner/polisher if ANTHROPIC_API_KEY or OPENAI_API_KEY is set.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    online = "--online" in sys.argv
    use_llm = "--llm" in sys.argv
    # default to the shipped fixture cache + offline unless --online
    os.environ.setdefault("CLARA_CACHE",
                          os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "demo_data", "fixtures"))
    if not online:
        os.environ["CLARA_OFFLINE"] = "1"
    from clara.demo import run_demo
    run_demo(out="demo_output", offline=not online, use_llm=use_llm)
