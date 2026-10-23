#!/bin/bash
# =====================================================================================================
#  Lanbai shared compile check - one-time setup (idempotent: run it again any time, it only fetches what is missing).
#  Everything goes into $LANBAI_CHECK_CACHE (default ~/.cache/lanbai_check), never into the repo.
#
#  required  dotnet 8 SDK (Roslyn csc), .NET Framework 4.7.2 reference assemblies, Unity3D.SDK 2021.1.14.1
#            (UnityEngine.dll + UnityEditor.dll: the newest UnityEditor reference assembly on nuget.org),
#            python3 + slangpy + pcpp
#  optional  RocketModFix.UnityEngine.Redist 2022.3.62.3 (UnityEngine 2022.3 modules + real PPv2/TMP runtime DLLs:
#            the 'player 2022.3' C# pass), Unity 2022.3.22f1 built-in CGIncludes (real UnityCG etc. instead of the
#            stub), Vortice.Dxc.Native 1.0.6 (DXC: a real HLSL compiler pass). Missing optional parts = that pass is
#            skipped and the check says so.
#  usage: ./setup.sh            (LANBAI_CHECK_CACHE=/somewhere ./setup.sh to put the cache elsewhere)
# =====================================================================================================
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
CACHE=${LANBAI_CHECK_CACHE:-$HOME/.cache/lanbai_check}
case "$CACHE" in "$(cd "$HERE/../../.." && pwd)"*) echo "LANBAI_CHECK_CACHE must be outside the repo" >&2; exit 2;; esac
mkdir -p "$CACHE/nuget" "$CACHE/pylib"
FETCH="python3 -I $HERE/lib/setup_fetch.py"
FAIL=0
echo "cache: $CACHE"

# ---- 1. dotnet 8 SDK + Roslyn ----------------------------------------------------------------------
echo "[1/6] dotnet + Roslyn"
if ! dotnet --version >/dev/null 2>&1; then
  if [ "$(id -u)" = 0 ] && command -v apt-get >/dev/null; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q dotnet-sdk-8.0 >"$CACHE/apt_dotnet.log" 2>&1 || true
  fi
fi
if ! dotnet --version >/dev/null 2>&1; then
  echo "  FAILED  no dotnet SDK (install dotnet-sdk-8.0)"; exit 1
fi
DOTNET=$(command -v dotnet)
DOTNET_ROOT_DIR=$(dirname "$(readlink -f "$DOTNET")")
CSC=$(ls -1 "$DOTNET_ROOT_DIR"/sdk/*/Roslyn/bincore/csc.dll 2>/dev/null | sort -V | tail -1)
if [ -z "$CSC" ]; then
  # no Roslyn inside the SDK: use the compiler NuGet package instead
  $FETCH nupkg Microsoft.Net.Compilers.Toolset 4.8.0 "$CACHE/nuget/Microsoft.Net.Compilers.Toolset.4.8.0" tasks/netcore/bincore/ || FAIL=1
  CSC="$CACHE/nuget/Microsoft.Net.Compilers.Toolset.4.8.0/tasks/netcore/bincore/csc.dll"
fi
echo "  dotnet $(dotnet --version), csc $(dotnet "$CSC" -version 2>/dev/null | head -1) ($CSC)"

# ---- 2. reference assemblies -----------------------------------------------------------------------
echo "[2/6] reference assemblies (NuGet)"
NET472="$CACHE/nuget/Microsoft.NETFramework.ReferenceAssemblies.net472.1.0.3"
$FETCH nupkg Microsoft.NETFramework.ReferenceAssemblies.net472 1.0.3 "$NET472" build/ || FAIL=1
U2021="$CACHE/nuget/Unity3D.SDK.2021.1.14.1"
$FETCH nupkg Unity3D.SDK 2021.1.14.1 "$U2021" lib/ || FAIL=1
U2022="$CACHE/nuget/RocketModFix.UnityEngine.Redist.2022.3.62.3"
$FETCH nupkg RocketModFix.UnityEngine.Redist 2022.3.62.3 "$U2022" lib/net40/ Unity-License.txt LICENSE || echo "  (optional: no 'player 2022.3' C# pass)"

# ---- 3. Unity built-in shader includes -------------------------------------------------------------
echo "[3/6] Unity 2022.3.22f1 CGIncludes"
CGINC="$CACHE/unity_cgincludes/2022.3.22f1"
$FETCH cginc v2022.3.22f1 "$CGINC" || echo "  (optional: shaders fall back to stubs/unity_stub.hlsl)"

# ---- 4. DXC ----------------------------------------------------------------------------------------
echo "[4/6] DXC (Vortice.Dxc.Native 1.0.6, linux-x64)"
DXCPKG="$CACHE/nuget/Vortice.Dxc.Native.1.0.6"
DXC_LIB=""; DXC_BASE=""
if $FETCH nupkg Vortice.Dxc.Native 1.0.6 "$DXCPKG" runtimes/linux-x64/ LICENSE-MS.txt LICENSE-LLVM.txt LICENSE-MIT.txt; then
  L="$DXCPKG/runtimes/linux-x64/native/libdxcompiler.so"
  for b in 3 5; do   # probe the COM vtable layout in a child process (a wrong guess can crash)
    if [ "$(cd "$HERE/lib" && python3 -c "import dxc,sys; print('ok' if dxc.selftest(sys.argv[1], int(sys.argv[2])) else 'bad')" "$L" $b 2>/dev/null)" = ok ]; then
      DXC_LIB="$L"; DXC_BASE=$b; break
    fi
  done
  if [ -n "$DXC_LIB" ]; then echo "  DXC ok (vtable base $DXC_BASE)"; else echo "  DXC library did not pass its self-test: DXC pass disabled"; fi
else
  echo "  (optional: no DXC pass)"
fi

# ---- 5. python packages ----------------------------------------------------------------------------
echo "[5/6] python: slangpy, pcpp"
PYTAG=$(python3 -c "import sys; print('cp%d%d' % sys.version_info[:2])")
PYLIB="$CACHE/pylib/$PYTAG"
mkdir -p "$PYLIB"
if ! PYTHONPATH="$PYLIB" python3 -c "import pcpp" 2>/dev/null; then
  python3 -m pip install -q --disable-pip-version-check --target "$PYLIB" pcpp==1.30 >/dev/null 2>&1 || { echo "  FAILED  pip install pcpp"; FAIL=1; }
fi
if ! PYTHONPATH="$PYLIB" python3 -c "import slangpy" 2>/dev/null; then
  python3 -m pip install -q --disable-pip-version-check --target "$PYLIB" slangpy >/dev/null 2>&1 || { echo "  FAILED  pip install slangpy"; FAIL=1; }
fi
PYTHONPATH="$PYLIB" python3 -c "import pcpp, slangpy; print('  pcpp', pcpp.__version__ if hasattr(pcpp, '__version__') else 'ok', '/ slangpy', getattr(slangpy, 'SLANG_BUILD_TAG', 'ok'))" 2>/dev/null | grep -v WARN || FAIL=1

# ---- 6. env.json + smoke test ----------------------------------------------------------------------
echo "[6/6] env.json + smoke test"
python3 - "$CACHE/env.json" <<EOF
import json, os, sys
def d(p): return p if p and os.path.exists(p) else ''
env = {
  'dotnet': '$DOTNET', 'csc': '$CSC',
  'net472': d('$NET472/build/.NETFramework/v4.7.2'),
  'unity2021': d('$U2021/lib'),
  'unity2022': d('$U2022/lib/net40'),
  'cginc': d('$CGINC') if os.path.exists('$CGINC/.lanbai_ok') else '',
  'cginc_version': '2022.3.22f1',
  'dxc': d('$DXC_LIB'), 'dxc_base': int('${DXC_BASE:-3}'),
  'pylib': '$PYLIB',
}
json.dump(env, open(sys.argv[1], 'w'), indent=1)
for k, v in env.items(): print('  %-13s %s' % (k, v if v != '' else '(missing)'))
EOF
if [ $FAIL = 0 ]; then
  echo "setup OK. Run:  $HERE/check_cs.sh <folder...>   and   python3 $HERE/check_shaders.py <folder...>"
else
  echo "setup INCOMPLETE (see FAILED lines above)"; exit 1
fi
