#!/bin/bash
# Roslyn type-check (C# 9, warnings as errors) of the 门内 session's C#: runtime (U#) scripts against UnityEngine +
# UdonStub.cs, editor scripts against UnityEngine + UnityEditor. NOT a Unity / UdonSharp compile.
# usage: CSC=<folder with run_csc.sh + build_common.sh> ./check_cs.sh [package folder ...]
if [ -z "$CSC" ] || [ ! -f "$CSC/build_common.sh" ]; then echo "set CSC (see README)" >&2; exit 2; fi
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../../.." && pwd)
OUT=${CHECK_OUT:-${TMPDIR:-/tmp}/lanbai_inside_cs}; mkdir -p "$OUT"
source "$CSC/build_common.sh"
PKGS=${@:-"$REPO/Act04c_Inside $REPO/Overlay"}
ok=1
for P in $PKGS; do
  name=$(basename "$P")
  RT=$(find "$P" -path '*~*' -prune -o -name '*.cs' -path '*Runtime*' -print)
  # dependencies: the overlay component and the Grading kit's exposure helper (+ a PPv2 stub) for act 4c's driver
  DEP="$REPO/Overlay/Runtime/LanbaiOverlay.cs $REPO/Grading/Runtime/LanbaiExposure.cs $REPO/Grading/Tools~/compile_check/PPv2Stub.cs"
  [ "$name" = "Act04c_Inside" ] && RT="$RT $DEP"
  ED=$(find "$P" -path '*~*' -prune -o -name '*.cs' -path '*Editor*' -print)
  if [ -n "$RT" ]; then
    "$CSC/run_csc.sh" -nologo -langversion:9 -warnaserror+ -target:library -out:"$OUT/$name.Runtime.dll" $REFS $DEFS "$HERE/UdonStub.cs" $RT \
      && echo "OK   $name runtime ($(echo $RT | wc -w) file(s))" || ok=0
  fi
  [ "$name" = "Act04c_Inside" ] && ED="$ED $REPO/Overlay/Editor/LanbaiOverlayBuild.cs"
  if [ -n "$ED" ]; then
    "$CSC/run_csc.sh" -nologo -langversion:9 -warnaserror+ -target:library -out:"$OUT/$name.Editor.dll" $REFS -r:$U/UnityEditor.dll $DEFS \
      "$HERE/UdonStub.cs" $RT $ED && echo "OK   $name editor ($(echo $ED | wc -w) file(s))" || ok=0
  fi
done
[ $ok = 1 ] && echo "C# CHECK OK" || { echo "C# CHECK FAILED"; exit 1; }
