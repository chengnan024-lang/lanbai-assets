#!/bin/bash
# Roslyn type-check + execution of the kit's C# outside Unity (art-side sanity check, NOT a Unity compile).
# Needs: CSC_HOME with run_csc.sh (Roslyn 4.10 on .NET 8), Unity 2021.1 UnityEngine.dll/UnityEditor.dll
# (NuGet Unity3D.SDK 2021.1.14.1) and .NET Framework 4.7.2 reference assemblies (NuGet).
set -e
H=$(cd "$(dirname "$0")" && pwd); KIT=$(cd "$H/../.." && pwd)
source "$CSC_HOME/build_common.sh"
O=$(mktemp -d)
C="$CSC_HOME/run_csc.sh -nologo -noconfig -nostdlib+ -langversion:9 -warn:4 -warnaserror+"
$C -target:library $REFS -out:$O/Unity.Postprocessing.Runtime.dll "$H/PPv2Stub.cs"
$C -target:library $REFS -out:$O/UdonStub.dll "$H/UdonStub.cs"
# 1. Editor asmdef layout (Editor/*.cs alone, PPv2 + UnityEditor refs)
$C -target:library $REFS -r:$U/UnityEditor.dll -r:$O/Unity.Postprocessing.Runtime.dll "$DEFS" -out:$O/Lanbai.Grading.Editor.dll "$KIT"/Editor/*.cs
# 2. U# runtime, normal path and Animator fallback path (the fallback must not need PPv2 at all)
$C -target:library $REFS -r:$O/Unity.Postprocessing.Runtime.dll -r:$O/UdonStub.dll "$DEFS" -out:$O/Expo.dll "$KIT/Runtime/LanbaiExposure.cs"
$C -target:library $REFS -r:$O/UdonStub.dll "$DEFS;LANBAI_PPV_ANIMATOR_FALLBACK" -out:$O/ExpoFallback.dll "$KIT/Runtime/LanbaiExposure.cs"
# 3. no-asmdef layout (everything in one assembly) + execute the data and the U# math
$C -target:library $REFS -r:$U/UnityEditor.dll -r:$O/Unity.Postprocessing.Runtime.dll -r:$O/UdonStub.dll "$DEFS" -out:$O/AllInOne.dll "$KIT"/Editor/*.cs "$KIT"/Runtime/*.cs
$C -target:exe $REFS -r:$O/AllInOne.dll -r:$O/UdonStub.dll -r:$O/Unity.Postprocessing.Runtime.dll -out:$O/Dump.exe "$H/Dump.cs"
cp $U/UnityEngine.dll $U/UnityEditor.dll $O/
echo '{ "runtimeOptions": { "tfm": "net8.0", "framework": { "name": "Microsoft.NETCore.App", "version": "8.0.0" }, "rollForward": "Major" } }' > $O/Dump.runtimeconfig.json
DOTNET_ROOT=$CSC_HOME/dotnet $CSC_HOME/dotnet/dotnet exec --runtimeconfig $O/Dump.runtimeconfig.json $O/Dump.exe > "$H/dump.json"
echo "compile OK (editor asmdef layout, U# normal + fallback, all-in-one); dump -> $H/dump.json"
