#!/bin/bash
# Roslyn type-check of the three Editor/*.cs files outside Unity (art-side sanity check, NOT a Unity compile).
# Needs CSC_HOME with run_csc.sh + build_common.sh (Roslyn 4.x on .NET 8, Unity 2021.1 UnityEngine/UnityEditor.dll,
# .NET Framework 4.7.2 reference assemblies) — the same setup the Grading kit used.
set -e
H=$(cd "$(dirname "$0")" && pwd); KIT=$(cd "$H/../.." && pwd)
source "$CSC_HOME/build_common.sh"
O=$(mktemp -d)
C="$CSC_HOME/run_csc.sh -nologo -noconfig -nostdlib+ -langversion:9 -warn:4 -warnaserror+"
$C -target:library $REFS -out:$O/Unity.TextMeshPro.dll "$H/TMPStub.cs"
$C -target:library $REFS -r:$U/UnityEditor.dll -r:$O/Unity.TextMeshPro.dll "$DEFS" -out:$O/Lanbai.Fonts.Editor.dll "$KIT/Editor/LanbaiTMPFontBuilder.cs" "$KIT/Editor/LanbaiScrimTextureImport.cs" "$KIT/Editor/LanbaiPoemMaterials.cs"
echo "type-check OK: Editor/LanbaiTMPFontBuilder.cs + LanbaiScrimTextureImport.cs + LanbaiPoemMaterials.cs (warnings as errors)"
