#!/bin/sh
export PYTHONPATH=/private/tmp/desloppify-work${PYTHONPATH:+:$PYTHONPATH}
exec /usr/local/opt/python@3.11/bin/python3.11 -m desloppify.cli "$@"
