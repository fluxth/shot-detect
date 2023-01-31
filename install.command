#!/bin/bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
cd "$SCRIPT_DIR"

if command -v virtualenv; then
    virtualenv venv
fi

if [[ -f "$SCRIPT_DIR/venv/bin/activate" ]]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

python -m pip install -r requirements.txt
exit_code=$?

echo
if [[ "$exit_code" == 0 ]]; then
    echo -en "\033[32m"
    echo "Installation complete!"
    echo -en "\033[0m"
else
    echo -en "\033[31m"
    echo "Installation failed with code: $exit_code"
    echo -en "\033[0m"
fi
