#!/bin/bash
# Lanbai shared C# compile check: Roslyn type-check of every *.cs under the given folders, in Unity's assembly layout
# (asmdef / Editor folders), editor pass + player pass (runtime code must compile without UnityEditor).
# NOT a Unity / UdonSharp compile - see README_compile_check.md for what it proves and what it does not.
#   usage: ./check_cs.sh <folder> [more folders]      e.g.  ./check_cs.sh Rain/Runtime   ./check_cs.sh Grading
#          options: --pass editor|player   --strict   -D SYMBOL   --out <dir outside the repo>
# Run ./setup.sh once first. Outputs go to $LANBAI_CHECK_OUT (default $TMPDIR/lanbai_check_out/cs), never into the repo.
HERE=$(cd "$(dirname "$0")" && pwd)
exec python3 "$HERE/lib/cs_check.py" "$@"
