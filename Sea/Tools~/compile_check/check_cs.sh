#!/bin/bash
# Roslyn type-check (C# 9, warnings as errors) of the sea / palace / act-7 C# against Unity reference assemblies +
# UdonStub.cs. NOT a Unity / UdonSharp compile: it proves the C# parses and type-checks against the references only.
# usage: CSC=<folder with run_csc.sh + build_common.sh> bash check_cs.sh      (CHECK_OUT: output dir, default /tmp)
set -e
if [ -z "$CSC" ] || [ ! -f "$CSC/build_common.sh" ]; then echo "set CSC" >&2; exit 2; fi
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../../.." && pwd)
OUT=${CHECK_OUT:-${TMPDIR:-/tmp}/lanbai_sea_cs}; mkdir -p "$OUT"
source "$CSC/build_common.sh"
C="$CSC/run_csc.sh -nologo -langversion:9 -warnaserror+ -nowarn:CS0414,CS0649"
# 1. runtime (UdonSharp behaviours) against UnityEngine + the Udon stub
RT=$(ls "$R"/Sea/Runtime/*.cs "$R"/Act07_Sea/Runtime/*.cs "$R"/Palace/Runtime/*.cs 2>/dev/null || true)
$C -target:library $REFS "$DEFS" -out:"$OUT/LanbaiSeaRuntime.dll" "$H/UdonStub.cs" $RT
# 2. editor scripts (all in one assembly, like Assembly-CSharp-Editor), against UnityEditor too
ED=$(ls "$R"/Sea/Editor/*.cs "$R"/Act07_Sea/Editor/*.cs "$R"/Palace/Editor/*.cs 2>/dev/null || true)
$C -target:library $REFS -r:$U/UnityEditor.dll "$DEFS" -r:"$OUT/LanbaiSeaRuntime.dll" -out:"$OUT/LanbaiSeaEditor.dll" $ED
echo "C# CHECK OK (runtime: $(echo $RT | wc -w) files, editor: $(echo $ED | wc -w) files)"
