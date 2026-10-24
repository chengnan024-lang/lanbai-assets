#!/bin/bash
# Roslyn type-check of Sky/Editor/*.cs and Sky/Runtime/*.cs (+ Act09_StarSea when present), warnings as errors,
# against UnityEngine / UnityEditor 2021.1 (NuGet unity3d.sdk 2021.1.14.1) + .NET Framework 4.7.2 reference assemblies
# + UdonStub.cs. NOT a Unity / UdonSharp compile. Setup (once):
#   apt-get install -y dotnet-sdk-8.0
#   mkdir -p ~/csc && cd ~/csc && curl -o u.nupkg https://api.nuget.org/v3-flatcontainer/unity3d.sdk/2021.1.14.1/unity3d.sdk.2021.1.14.1.nupkg \
#     && curl -o n.nupkg https://api.nuget.org/v3-flatcontainer/microsoft.netframework.referenceassemblies.net472/1.0.3/microsoft.netframework.referenceassemblies.net472.1.0.3.nupkg \
#     && unzip -qo u.nupkg -d unity && unzip -qo n.nupkg -d net472
set -e
H=$(cd "$(dirname "$0")" && pwd); SKY=$(cd "$H/../.." && pwd); REPO=$(cd "$SKY/.." && pwd)
CSC=$(ls /usr/lib/dotnet/sdk/*/Roslyn/bincore/csc.dll | head -1)
NET=~/csc/net472/build/.NETFramework/v4.7.2; U=~/csc/unity/lib
OUT=${CHECK_OUT:-/tmp/lanbai_sky_cs}; mkdir -p "$OUT"
REFS="-r:$NET/mscorlib.dll -r:$NET/System.dll -r:$NET/System.Core.dll -r:$NET/Facades/netstandard.dll -r:$U/UnityEngine.dll"
C="dotnet $CSC -nologo -noconfig -nostdlib+ -langversion:9 -warn:4 -warnaserror+ -nowarn:CS0414"
$C -target:library $REFS -out:"$OUT/UdonStub.dll" "$H/UdonStub.cs"
RUNTIME=$(ls "$SKY"/Runtime/*.cs "$REPO"/Act09_StarSea/Runtime/*.cs 2>/dev/null || true)
$C -target:library $REFS -r:"$OUT/UdonStub.dll" -out:"$OUT/LanbaiSky.Runtime.dll" $RUNTIME
EDITOR=$(ls "$SKY"/Editor/*.cs "$REPO"/Act09_StarSea/Editor/*.cs 2>/dev/null || true)
$C -target:library $REFS -r:$U/UnityEditor.dll -r:"$OUT/UdonStub.dll" -r:"$OUT/LanbaiSky.Runtime.dll" -out:"$OUT/LanbaiSky.Editor.dll" $EDITOR
echo "C# CHECK OK (runtime: $(echo $RUNTIME | wc -w) files, editor: $(echo $EDITOR | wc -w) files)"
