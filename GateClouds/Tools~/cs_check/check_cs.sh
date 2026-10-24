#!/bin/bash
# mcs (Mono C#) type-check of the kit's C# against UnityStub.cs. NOT a Unity / UdonSharp compile.
HERE=$(cd "$(dirname "$0")" && pwd)
mcs -nologo -langversion:7.2 -warnaserror+ -nowarn:0414,0649 -target:library -out:"${TMPDIR:-/tmp}/gateclouds_check.dll" \
  "$HERE/UnityStub.cs" "$HERE"/../../Runtime/*.cs "$HERE"/../../Editor/*.cs && echo "C# CHECK OK"
