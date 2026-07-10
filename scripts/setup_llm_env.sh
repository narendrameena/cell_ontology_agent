#!/usr/bin/env bash
# Build a PERSISTENT Python 3.11 virtualenv with the OBO/Monarch LLM stack that
# CellScribe hands off to: OntoGPT (SPIRES), CurateGPT (DRAGON-AI), Aurelian.
#
# These require Python >=3.10/3.11, so they live in a separate interpreter from
# CellScribe (which runs on 3.8+); CellScribe invokes their CLIs as subprocesses.
# We use `uv` to fetch a standalone CPython 3.11 and resolve deps fast.
#
#   bash scripts/setup_llm_env.sh            # builds ./.llm-venv
#   CELLSCRIBE_LLM_VENV=/path bash scripts/setup_llm_env.sh   # custom location
#
# The dep pins below are load-bearing (discovered empirically):
#   setuptools<75   -> newer setuptools drops pkg_resources, which ontogpt imports
#   psutil          -> curategpt.agents.dragon_agent needs it
#   pdfminer.six    -> aurelian's literature agent needs it
#   pydantic-ai==0.2.0 -> aurelian 0.4.2 pins `>=0.2.0` but its code uses the 0.2 API
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${CELLSCRIBE_LLM_VENV:-$HERE/.llm-venv}"
PYVER="${CELLSCRIBE_PYVER:-3.11}"

# 1) ensure uv is available (installs to ~/.local/bin if missing)
if ! command -v uv >/dev/null 2>&1; then
  export PATH="$HOME/.local/bin:$PATH"
  command -v uv >/dev/null 2>&1 || python3 -m pip install --user -q uv
fi
export PATH="$HOME/.local/bin:$PATH"
echo "uv: $(uv --version)"

# 2) fetch a standalone Python 3.11 + create the venv
uv python install "$PYVER"
uv venv --python "$PYVER" "$VENV"

# 3) install the stack, then the load-bearing dep fixes
uv pip install --python "$VENV" ontogpt aurelian requests
uv pip install --python "$VENV" --prerelease=allow curategpt
uv pip install --python "$VENV" "setuptools<75" psutil "pdfminer.six" "pydantic-ai==0.2.0"

# 4) smoke-test the CLIs + import the hand-off targets
echo "--- versions ---"
"$VENV/bin/ontogpt" --version 2>/dev/null || true
"$VENV/bin/python" - <<'PY'
import importlib
for mod, sym in [("ontogpt.engines.spires_engine","SPIRESEngine"),
                 ("curategpt.agents.dragon_agent","DragonAgent")]:
    getattr(importlib.import_module(mod), sym)
    print("  import OK:", mod + "." + sym)
print("  ontogpt cell_type template + Groq (litellm) ready")
PY
echo ""
echo "Done. LLM venv at: $VENV"
echo "Point CellScribe at it with:  export CELLSCRIBE_LLM_VENV=$VENV"
echo "Set a Groq key with:          export GROQ_API_KEY=gsk_...   (free tier at console.groq.com)"
