using System;
using System.Globalization;
using System.Text;
using Lanbai.Grading;
public static class Dump
{
    static string F(float? f) { return f.HasValue ? f.Value.ToString("R", CultureInfo.InvariantCulture) : "null"; }
    static string S(string s) { return s == null ? "null" : "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\""; }
    static string A(float[] a) { if (a == null) return "null"; var p = new string[a.Length]; for (int i = 0; i < a.Length; i++) p[i] = a[i].ToString("R", CultureInfo.InvariantCulture); return "[" + string.Join(",", p) + "]"; }
    static string SA(string[] a) { if (a == null) return "null"; var p = new string[a.Length]; for (int i = 0; i < a.Length; i++) p[i] = S(a[i]); return "[" + string.Join(",", p) + "]"; }
    static string B(bool? b) { return b.HasValue ? (b.Value ? "true" : "false") : "null"; }
    public static int Main(string[] args)
    {
        var sb = new StringBuilder();
        sb.Append("{\"entries\":[");
        for (int i = 0; i < LanbaiGradeData.Entries.Length; i++)
        {
            var e = LanbaiGradeData.Entries[i];
            if (i > 0) sb.Append(",");
            sb.Append("{");
            sb.Append("\"id\":" + S(e.id) + ",\"displayName\":" + S(e.displayName) + ",\"kind\":" + S(e.kind.ToString()) + ",\"group\":" + S(e.group));
            sb.Append(",\"priority\":" + F(e.priority) + ",\"initialWeight\":" + F(e.initialWeight) + ",\"desktopOnly\":" + B(e.desktopOnly) + ",\"weightRule\":" + S(e.weightRule));
            sb.Append(",\"hdrNeutral\":" + B(e.hdrNeutral) + ",\"postExposure\":" + F(e.postExposure) + ",\"temperature\":" + F(e.temperature) + ",\"tint\":" + F(e.tint));
            sb.Append(",\"colorFilter\":" + S(e.colorFilter) + ",\"hueShift\":" + F(e.hueShift) + ",\"saturation\":" + F(e.saturation) + ",\"contrast\":" + F(e.contrast));
            sb.Append(",\"lift\":" + A(e.lift) + ",\"gamma\":" + A(e.gamma) + ",\"gain\":" + A(e.gain) + ",\"channelMixer\":" + A(e.channelMixer));
            sb.Append(",\"bloomIntensity\":" + F(e.bloomIntensity) + ",\"bloomThreshold\":" + F(e.bloomThreshold) + ",\"bloomSoftKnee\":" + F(e.bloomSoftKnee) + ",\"bloomClamp\":" + F(e.bloomClamp));
            sb.Append(",\"bloomDiffusion\":" + F(e.bloomDiffusion) + ",\"bloomAnamorphicRatio\":" + F(e.bloomAnamorphicRatio) + ",\"bloomColor\":" + S(e.bloomColor) + ",\"bloomFastMode\":" + B(e.bloomFastMode));
            sb.Append(",\"vignetteMode\":" + S(e.vignetteMode) + ",\"vignetteColor\":" + S(e.vignetteColor) + ",\"vignetteCenter\":" + A(e.vignetteCenter) + ",\"vignetteIntensity\":" + F(e.vignetteIntensity));
            sb.Append(",\"vignetteSmoothness\":" + F(e.vignetteSmoothness) + ",\"vignetteRoundness\":" + F(e.vignetteRoundness) + ",\"vignetteRounded\":" + B(e.vignetteRounded));
            sb.Append(",\"grainColored\":" + B(e.grainColored) + ",\"grainIntensity\":" + F(e.grainIntensity) + ",\"grainSize\":" + F(e.grainSize) + ",\"grainLumContrib\":" + F(e.grainLumContrib));
            sb.Append(",\"bloomT0\":" + F(e.bloomT0) + ",\"expectedTestCard\":" + SA(e.expectedTestCard));
            sb.Append(",\"bloomColorCompensated\":" + A(e.bloomColorCompensated) + ",\"predictedTestCard\":" + SA(e.predictedTestCard));
            sb.Append(",\"expectedColourPatches\":" + SA(e.expectedColourPatches) + ",\"predictedColourPatches\":" + SA(e.predictedColourPatches));
            sb.Append(",\"expectedBlack\":" + S(e.expectedBlack) + ",\"predictedBlack\":" + S(e.predictedBlack) + ",\"lookDefinition\":" + S(e.lookDefinition) + ",\"routeCLut\":" + S(e.routeCLut));
            sb.Append(",\"HasColorGrading\":" + B(e.HasColorGrading) + ",\"HasBloom\":" + B(e.HasBloom) + ",\"HasVignette\":" + B(e.HasVignette) + ",\"HasGrain\":" + B(e.HasGrain));
            sb.Append("}");
        }
        sb.Append("],\"forbidden\":" + SA(LanbaiGradeData.ForbiddenEffects));
        sb.Append(",\"colourPatchNames\":" + SA(LanbaiGradeData.ColourPatchNames) + ",\"colourPatchLinear\":" + A(LanbaiGradeData.ColourPatchLinear));
        // the U# helper's static math, executed for real
        sb.Append(",\"expo\":{\"SceneCount\":" + LanbaiExposure.SceneCount + ",\"up\":" + F(LanbaiExposure.ExpoUpTarget) + ",\"down\":" + F(LanbaiExposure.ExpoDownTarget) + ",\"scenes\":[");
        for (int i = 0; i < LanbaiExposure.SceneCount; i++)
        {
            if (i > 0) sb.Append(",");
            sb.Append("{\"i\":" + i + ",\"id\":" + S(LanbaiExposure.SceneId(i)) + ",\"back\":" + LanbaiExposure.SceneIndex(LanbaiExposure.SceneId(i)) + ",\"pe\":" + F(LanbaiExposure.ScenePostExposure(i)) + "}");
        }
        sb.Append("],\"calls\":[");
        // args: dEV b  -> weights and applied
        float[][] cases = new float[][] {
            new float[]{0.5f,-0.9f}, new float[]{0.3f,-0.85f}, new float[]{1.5f,-0.9f}, new float[]{-0.5f,-0.8f}, new float[]{0.8f,-0.5f},
            new float[]{1.0f,0.3f}, new float[]{2.4f,0.3f}, new float[]{0.35f,0.3f}, new float[]{1.0f,-0.15f}, new float[]{0.8f,0f}, new float[]{0f,0f}, new float[]{9f,0f}, new float[]{-9f,0f},
            new float[]{-0.5f,-0.75f}, new float[]{-2.43f,-0.45f}, new float[]{0.5f,-0.5f} };
        for (int i = 0; i < cases.Length; i++)
        {
            float d = cases[i][0], b = cases[i][1];
            float wu = LanbaiExposure.WeightUp(d, b), wd = LanbaiExposure.WeightDown(d, b);
            if (i > 0) sb.Append(",");
            sb.Append("{\"dEV\":" + F(d) + ",\"b\":" + F(b) + ",\"wUp\":" + F(wu) + ",\"wDown\":" + F(wd) + ",\"applied\":" + F(LanbaiExposure.AppliedDeltaEV(wu, wd, b)) + ",\"fill\":" + F(LanbaiExposure.OverlayFillScale(LanbaiExposure.AppliedDeltaEV(wu, wd, b))) + "}");
        }
        sb.Append("],\"blend\":[");
        // crossfade S2(1) + S3(w) and a full fold
        float[] w1 = new float[LanbaiExposure.SceneCount]; w1[1] = 1f; w1[2] = 0.3f;
        float[] w2 = new float[LanbaiExposure.SceneCount]; w2[10] = 1f; w2[11] = 0.5f;
        float[] w3 = new float[LanbaiExposure.SceneCount]; w3[0] = 1f;
        sb.Append(F(LanbaiExposure.BlendedBase(w1)) + "," + F(LanbaiExposure.CrossfadeBase(1, 2, 0.3f)) + "," + F(LanbaiExposure.BlendedBase(w2)) + "," + F(LanbaiExposure.BlendedBase(w3)));
        sb.Append("],\"routeC\":[" + F(LanbaiExposure.RouteCCrossfadeWeight(1f, 0f)) + "," + F(LanbaiExposure.RouteCCrossfadeWeight(1f, 0.5f)) + "," + F(LanbaiExposure.RouteCCrossfadeWeight(1f, 1f)) + "," + F(LanbaiExposure.RouteCCrossfadeWeight(-0.8f, 0.5f)) + "]}");
        sb.Append("}");
        Console.WriteLine(sb.ToString());
        return 0;
    }
}
