#!/bin/bash
# Verifier's compile check: the kit against the REAL PPv2 runtime (v2 branch = com.unity.postprocessing 3.0.2,
# 56 Runtime/*.cs fetched from raw.githubusercontent.com and compiled against Unity 2021.1 reference DLLs),
# instead of the builder's hand-written PPv2Stub.cs. Warnings are errors.
# Needs CSC_HOME (Roslyn + build_common.sh, same as ../compile_check/run_check.sh).
set -e
H=$(cd "$(dirname "$0")" && pwd); KIT=$(cd "$H/../.." && pwd)
source "$CSC_HOME/build_common.sh"
W=$(mktemp -d); B=https://raw.githubusercontent.com/Unity-Technologies/PostProcessing/v2/PostProcessing/Runtime
for f in Attributes/DisplayNameAttribute.cs Attributes/MaxAttribute.cs Attributes/MinAttribute.cs Attributes/MinMaxAttribute.cs \
  Attributes/PostProcessAttribute.cs Attributes/TrackballAttribute.cs Effects/AmbientOcclusion.cs Effects/AutoExposure.cs Effects/Bloom.cs \
  Effects/ChromaticAberration.cs Effects/ColorGrading.cs Effects/DepthOfField.cs Effects/Dithering.cs Effects/FastApproximateAntialiasing.cs \
  Effects/Fog.cs Effects/Grain.cs Effects/LensDistortion.cs Effects/MotionBlur.cs Effects/MultiScaleVO.cs Effects/ScalableAO.cs \
  Effects/ScreenSpaceReflections.cs Effects/SubpixelMorphologicalAntialiasing.cs Effects/TemporalAntialiasing.cs Effects/Vignette.cs \
  Monitors/HistogramMonitor.cs Monitors/LightMeterMonitor.cs Monitors/Monitor.cs Monitors/VectorscopeMonitor.cs Monitors/WaveformMonitor.cs \
  Utils/ColorUtilities.cs Utils/HableCurve.cs Utils/HaltonSeq.cs Utils/LogHistogram.cs Utils/MeshUtilities.cs Utils/PropertySheet.cs \
  Utils/PropertySheetFactory.cs Utils/RuntimeUtilities.cs Utils/ShaderIDs.cs Utils/Spline.cs Utils/TargetPool.cs Utils/TextureFormatUtilities.cs \
  Utils/TextureLerper.cs Utils/XRSettings.cs ParameterOverride.cs PostProcessBundle.cs PostProcessDebug.cs PostProcessDebugLayer.cs \
  PostProcessEffectRenderer.cs PostProcessEffectSettings.cs PostProcessEvent.cs PostProcessLayer.cs PostProcessManager.cs \
  PostProcessProfile.cs PostProcessRenderContext.cs PostProcessResources.cs PostProcessVolume.cs; do
  mkdir -p "$W/src/$(dirname $f)"; curl -sSf -m 30 -o "$W/src/$f" "$B/$f"; done
PPDEFS="-define:UNITY_EDITOR;UNITY_2017_1_OR_NEWER;UNITY_2017_2_OR_NEWER;UNITY_2017_3_OR_NEWER;UNITY_2018_1_OR_NEWER;UNITY_2018_2_OR_NEWER;UNITY_2018_3_OR_NEWER;UNITY_2018_4_OR_NEWER;UNITY_2019_1_OR_NEWER;UNITY_2019_2_OR_NEWER;UNITY_2019_3_OR_NEWER;UNITY_2019_4_OR_NEWER;UNITY_2020_1_OR_NEWER;UNITY_2020_2_OR_NEWER;UNITY_2020_3_OR_NEWER;UNITY_2021_1_OR_NEWER;UNITY_STANDALONE_WIN;ENABLE_VR_MODULE;ENABLE_VR;ENABLE_XR_MODULE"
R="$CSC_HOME/run_csc.sh -nologo -noconfig -nostdlib+ -langversion:9"
$R -nowarn:0618,0612,0414,0649,0169,0108 -target:library $REFS -r:$U/UnityEditor.dll "$PPDEFS" -out:$W/Unity.Postprocessing.Runtime.dll $(find "$W/src" -name '*.cs')
C="$R -warn:4 -warnaserror+"
$C -target:library $REFS -r:$U/UnityEditor.dll -r:$W/Unity.Postprocessing.Runtime.dll "$DEFS" -out:$W/Editor.dll "$KIT"/Editor/*.cs
$C -target:library $REFS -out:$W/UdonStub.dll "$KIT/Tools~/compile_check/UdonStub.cs"
$C -target:library $REFS -r:$W/Unity.Postprocessing.Runtime.dll -r:$W/UdonStub.dll "$DEFS" -out:$W/Expo.dll "$KIT/Runtime/LanbaiExposure.cs"
$C -target:library $REFS -r:$W/UdonStub.dll "$DEFS;LANBAI_PPV_ANIMATOR_FALLBACK" -out:$W/ExpoFB.dll "$KIT/Runtime/LanbaiExposure.cs"
$C -target:library $REFS -r:$U/UnityEditor.dll -r:$W/Unity.Postprocessing.Runtime.dll -r:$W/UdonStub.dll "$DEFS" -out:$W/AllInOne.dll "$KIT"/Editor/*.cs "$KIT"/Runtime/*.cs
echo "OK: kit compiles against the real PPv2 3.0.2 runtime (editor asmdef layout, U# normal + fallback, all-in-one), 0 warnings"
