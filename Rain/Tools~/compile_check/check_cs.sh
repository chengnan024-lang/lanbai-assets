#!/bin/bash
# Roslyn type-check of Runtime/*.cs (C# 9, warnings as errors) against UnityEngine 2021.1 + UdonStub.cs.
# This is NOT a Unity / UdonSharp compile: it proves the C# parses and type-checks against the stubs only.
# usage: CSC=<folder with run_csc.sh + build_common.sh (Roslyn 4.x + .NET 8 + the unity3d.sdk nupkg)> ./check_cs.sh
# The DLL goes to $CHECK_OUT (default: $TMPDIR/lanbai_rain_check), never into the kit.
if [ -z "$CSC" ] || [ ! -f "$CSC/build_common.sh" ]; then
  echo "set CSC to the folder that holds run_csc.sh and build_common.sh" >&2; exit 2
fi
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${CHECK_OUT:-${TMPDIR:-/tmp}/lanbai_rain_check}
source "$CSC/build_common.sh"
mkdir -p "$OUT"
"$CSC/run_csc.sh" -nologo -langversion:9 -warnaserror+ -nowarn:CS0414 -target:library -out:"$OUT/LanbaiRain.dll" $REFS $DEFS \
  "$HERE/UdonStub.cs" "$HERE"/../../Runtime/*.cs && echo "C# CHECK OK"
