// =====================================================================================================
//  LanbaiPoemDriver.cs   蓝白 · 摆诗的运行时（UdonSharp），字体套件第 4.1 版（D-33 #5，2026-10-24，总工程师）
//  !!! WRITTEN WITHOUT A UNITY COMPILER. Checked with Common/Tools~/compile_check (Roslyn + U# rules) only. !!!
//
//  Every field is filled by 蓝白/Fonts/Build Poem Objects (Fonts/Editor/LanbaiPoemBake.cs) from Fonts/strings_all.json:
//  the text objects already exist in the scene (one set per poem and player key, all off); this behaviour only decides
//  which set is on, where the anchor sits, and the per-frame look (alpha, _OutlineSoftness, drift).
//
//  Director interface (CONTROL §5): LanbaiTick(t) every frame, LanbaiActivate(on), LanbaiWindow() = the whole film.
//  Stateless in t (D-33 #6): whatever t is (a late joiner, the debug clock dragged back), the frame is rebuilt from t;
//  the only memory is WHERE a poem's anchor was put when it appeared (the gaze rule, bible §7.4-6), re-decided
//  whenever a poem (re)appears.
//
//  Language (D-30, D-31 #1): VRCPlayerApi.GetCurrentLanguage() (RFC 5646) -> key by prefix, zh-HK / zh-TW / zh-Hant
//  first; OnLanguageChanged(language) re-maps; the notice board's switch (LanbaiLangButton -> _LangZh/_LangJa/_LangEn)
//  overrides it for this player only. Changing the key mid-poem just shows the other set at the same moment.
//  Keys: 0 zh, 1 zht, 2 ja, 3 en, 4 de (the order of KEYS below = the order the bake uses).
//
//  Look per text object (bible §7.4-4): focus-in over oFocus s from its own start (ease-out): alpha 0 -> oAlpha,
//  _OutlineSoftness 0.9 -> oSoftEnd; exit from oExitT over oExitS s: alpha -> 0 and a drift of 0.2° up (+1) / down
//  (-1) / none (0). Written with a MaterialPropertyBlock on the TMP MeshRenderer (_FaceColor = the solved linear fill
//  with alpha, _OutlineSoftness, _FaceDilate 0.05 desktop / 0.10 VR), so no per-object material instance is needed.
//  Urlicht's lines appear with their cues (TMP maxVisibleLines). Tianwen's Han line is 20 one-character objects.
//  Seats (D-33 #7b): the bus exports a 1° occlusion grid per seat (from that seat's eye); the bake copies it into
//  seatOcc. Placing a poem (default or moved by the gaze rule), the block is looked up for the LOCAL player's seat
//  (SetSeat from LB_Journey): more than 10 % behind bus parts -> move it sideways 1° at a time, toward the default
//  first, at most ±15°, the nearest position with ≤ 10 %; none -> the default. Fixed poems (Zhuangzi, Tianwen) never move.
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;
using TMPro;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiPoemDriver : UdonSharpBehaviour
{
    public const int K = 5;                          // zh, zht, ja, en, de
    [Header("Scene")]
    public Transform busRoot;                        // the bus (cabin space); poemsRoot is re-parented under it at Start
    public Transform poemsRoot;
    public Vector3 eyeLocal = new Vector3(0.55f, 1.70f, 2.05f);   // the main seat's eye in bus space (BusLayout.json)

    [Header("Poems (one entry per poem)")]
    public string[] pId;
    public float[] pT0;                              // t_appear
    public float[] pTgone;                           // t_gone: nothing of the poem after this
    public float[] pAz, pEl, pDist;                  // default anchor (deg, deg, m); pAzKey[p * K + k] overrides per key
    public float[] pAzKey;
    public bool[] pFixed;                            // never follows the gaze (Zhuangzi, Tianwen)
    public float[] pGazeDeg;                         // gaze threshold per poem: 50°, the side-window poems 75° (D-33 #7c)
    public Vector2 winRight = new Vector2(-22.5f, 16.5f);   // a moved block stays inside one of these azimuth spans
    public Vector2 winSide = new Vector2(48.5f, 103f);
    public Transform[] slotRoot;                     // [p * K + k]: the anchor of that poem for that key
    public int[] slotObjStart, slotObjCount;         // text objects of the slot (contiguous)
    public int[] slotScrimStart, slotScrimCount;

    [Header("Text objects")]
    public GameObject[] oGo;
    public MeshRenderer[] oRenderer;
    public TextMeshPro[] oTmp;
    public Vector4[] oFill;                          // solved linear _FaceColor (rgb), alpha ignored
    public float[] oAlpha, oStart, oFocus, oSoftEnd, oExitT, oExitS, oDrift, oLocalY;
    public int[] oCueStart, oCueCount;               // Urlicht: oCueCount > 0 -> visible lines follow cueT
    public float[] cueT;

    [Header("Scrims (SpriteRenderer, colour (1,1,1,a))")]
    public SpriteRenderer[] sRenderer;
    public float[] sAlpha, sStart, sExitT, sExitS;

    [Header("Notice board (D-31): per key 0..3 (zh, zht, ja, en), before departure only")]
    public GameObject[] boardRoot;
    public TextMeshPro[] boardLine1;
    public string[] boardPrefix, boardSuffix;        // line 1 = prefix + seconds + suffix (the {0} of strings_all.json ui)
    public GameObject boardButtons;                  // 中 / 日 / EN: on with the countdown, off after departure (§6·12)

    [Header("Seats (D-33 #7b): 1° occlusion grid per seat from the bus, row-major el0 upward, az0 eastward")]
    public Vector3[] seatEye;                        // bus space; empty -> eyeLocal
    public byte[] seatOcc;                           // [seat * occNEl * occNAz + row * occNAz + col]: 1 = a bus part
    public int occAz0 = -180, occEl0 = -25, occNAz = 360, occNEl = 46;
    public float[] slotBlkW, slotBlkEl0, slotBlkEl1; // the block per slot (width deg, bottom / top elevation deg)
    public int seat = 0;

    [Header("State (read only)")]
    public int key = 3;
    public int overrideKey = -1;
    public string clientLanguage = "";

    private MaterialPropertyBlock _mpb;
    private int _idFace, _idSoft, _idDilate;
    private float _dilate = 0.05f;
    private bool[] _shown;                           // per poem: drawn last frame
    private int[] _shownKey;
    private bool[] _placed;
    private int _boardKey = -1;

    void Start()
    {
        _mpb = new MaterialPropertyBlock();
        _idFace = VRCShader.PropertyToID("_FaceColor");
        _idSoft = VRCShader.PropertyToID("_OutlineSoftness");
        _idDilate = VRCShader.PropertyToID("_FaceDilate");
        VRCPlayerApi lp = Networking.LocalPlayer;
        if (lp != null && lp.IsUserInVR()) _dilate = 0.10f;          // bible §7.2
        int n = pId != null ? pId.Length : 0;
        _shown = new bool[n];
        _shownKey = new int[n];
        _placed = new bool[n];
        if (poemsRoot != null && busRoot != null) poemsRoot.SetParent(busRoot, false);
        for (int i = 0; i < (oGo != null ? oGo.Length : 0); i++)
            if (oGo[i] != null) oGo[i].SetActive(false);
        for (int i = 0; i < (sRenderer != null ? sRenderer.Length : 0); i++)
            if (sRenderer[i] != null) sRenderer[i].enabled = false;
        PickLanguage(VRCPlayerApi.GetCurrentLanguage());
    }

    // ------------------------------------------------------------------------------------------ language
    public override void OnLanguageChanged(string language)
    {
        PickLanguage(language);
    }

    public void PickLanguage(string code)
    {
        clientLanguage = code == null ? "" : code;
        if (overrideKey < 0) key = KeyOf(clientLanguage);
    }

    // client code -> key (Fonts/strings_all.json player_of_client_language; the first match wins)
    public int KeyOf(string code)
    {
        if (code == null || code.Length == 0) return 3;
        string c = code.ToLower();
        if (c.StartsWith("zh-hk") || c.StartsWith("zh-tw") || c.StartsWith("zh-hant") || c.StartsWith("chinese traditional")) return 1;
        if (c.StartsWith("zh") || c.StartsWith("chinese")) return 0;
        if (c.StartsWith("ja") || c.StartsWith("japanese")) return 2;
        if (c.StartsWith("de") || c.StartsWith("german")) return 4;
        return 3;
    }

    // the notice board's switch, this player only (D-31 #1): 中 keeps a zh-HK client on Traditional
    public void _LangZh() { int k = KeyOf(clientLanguage); overrideKey = k == 1 ? 1 : 0; key = overrideKey; }
    public void _LangJa() { overrideKey = 2; key = 2; }
    public void _LangEn() { overrideKey = 3; key = 3; }

    // ------------------------------------------------------------------------------------------ Director
    // Director v1.1: this driver runs the whole film but takes over no placeholder group: its window must not go into
    // windowsFlat / LanbaiCovered(t) (D-33 review #2)
    public bool LanbaiTakesOverNothing()
    {
        return true;
    }

    public float[] LanbaiWindow()
    {
        return new float[] { -100000f, 100000f };
    }

    public void LanbaiActivate(bool on)
    {
        if (poemsRoot != null) poemsRoot.gameObject.SetActive(on);
    }

    public void LanbaiTick(float t)
    {
        int n = pId != null ? pId.Length : 0;
        for (int p = 0; p < n; p++)
        {
            bool live = t >= pT0[p] - 0.05f && t < pTgone[p];
            int slot = p * K + key;
            if (!live)
            {
                if (_shown[p]) { HideSlot(p * K + _shownKey[p]); _shown[p] = false; }
                _placed[p] = false;                                  // re-decide the gaze placement next time
                continue;
            }
            if (_shown[p] && _shownKey[p] != key) HideSlot(p * K + _shownKey[p]);
            if (!_placed[p]) { Place(p); _placed[p] = true; }
            DrawSlot(slot, pDist[p], t);
            _shown[p] = true;
            _shownKey[p] = key;
        }
    }

    // ------------------------------------------------------------------------------------------ placement (§7.4-6)
    private void Place(int p)
    {
        float az = pAz[p];
        bool kept = true;
        if (!pFixed[p])
        {
            // trigger: the player's yaw (in bus space) within the poem's gaze threshold of the default -> default (50°;
            // the side-window poems 75°, D-33 #7c); else the player's yaw rounded to 15°, moved 20° toward the default,
            // same elevation and distance
            float yaw = HeadYaw();
            float d = Mathf.DeltaAngle(yaw, az);
            float thr = pGazeDeg != null && pGazeDeg.Length > p ? pGazeDeg[p] : 50f;
            if (Mathf.Abs(d) > thr) { az = Mathf.Round(yaw / 15f) * 15f + (d > 0f ? 20f : -20f); kept = false; }
        }
        // origin: the seat's eye for the default; the player's head (in bus space) for a gaze-moved poem (D-33 review #6)
        Vector3 origin = seatEye != null && seatEye.Length > seat ? seatEye[seat] : eyeLocal;
        if (!kept && busRoot != null) origin = busRoot.InverseTransformPoint(HeadPos());
        for (int k = 0; k < K; k++)
        {
            // the per-key default (D-13: Rilke ja +4.5°) holds only where the gaze rule kept the default
            int slot = p * K + k;
            float def = pAzKey != null && pAzKey.Length > slot ? pAzKey[slot] : pAz[p];
            float a = kept ? def : InWindows(slot, az);
            if (!pFixed[p]) a = Avoid(slot, a, def);
            PlaceSlot(p, k, a, origin);
        }
    }

    // D-33 #7c: a moved poem stays inside the right windscreen pane or the side window (block edges inside
    // winRight / winSide, bus README §2.2); the nearest allowed centre
    private float InWindows(int slot, float a)
    {
        float h = slotBlkW != null && slotBlkW.Length > slot ? slotBlkW[slot] * 0.5f : 0f;
        float l0 = winRight.x + h, l1 = winRight.y - h, s0 = winSide.x + h, s1 = winSide.y - h;
        if ((a >= l0 && a <= l1) || (a >= s0 && a <= s1)) return a;
        float best = a, bd = 1e9f;
        if (l0 <= l1) { float c = Mathf.Clamp(a, l0, l1); if (Mathf.Abs(c - a) < bd) { bd = Mathf.Abs(c - a); best = c; } }
        if (s0 <= s1) { float c = Mathf.Clamp(a, s0, s1); if (Mathf.Abs(c - a) < bd) { bd = Mathf.Abs(c - a); best = c; } }
        return best;
    }

    // D-33 #7b: blocked share of the block at azimuth a for the local player's seat (0 when there is no grid)
    public float Blocked(int slot, float a)
    {
        int per = occNAz * occNEl;
        if (seatOcc == null || seatOcc.Length < per * (seat + 1) || slotBlkW == null || slotBlkW.Length <= slot) return 0f;
        float a0 = a - slotBlkW[slot] * 0.5f, a1 = a + slotBlkW[slot] * 0.5f;
        int c0 = Mathf.FloorToInt(a0) - occAz0, c1 = Mathf.CeilToInt(a1) - occAz0;
        int r0 = Mathf.Max(0, Mathf.FloorToInt(slotBlkEl0[slot]) - occEl0), r1 = Mathf.Min(occNEl, Mathf.CeilToInt(slotBlkEl1[slot]) - occEl0);
        int n = 0, hit = 0, b = seat * per;
        for (int r = r0; r < r1; r++)
            for (int c = c0; c < c1; c++)
            {
                int cc = ((c % occNAz) + occNAz) % occNAz;
                n++;
                if (seatOcc[b + r * occNAz + cc] != 0) hit++;
            }
        return n > 0 ? (float)hit / n : 0f;
    }

    private float Avoid(int slot, float a, float def)
    {
        if (Blocked(slot, a) <= 0.1f) return a;
        float dir = def > a ? 1f : -1f;                              // toward the default first
        for (int d = 1; d <= 15; d++)
        {
            if (Blocked(slot, a + dir * d) <= 0.1f) return a + dir * d;
            if (Blocked(slot, a - dir * d) <= 0.1f) return a - dir * d;
        }
        return def;
    }

    // LB_Journey: the local player's seat index (the bus's seat order, as the grid was exported)
    public void SetSeat(int s)
    {
        seat = s;
    }

    private void PlaceSlot(int p, int k, float a, Vector3 origin)
    {
        Transform r = slotRoot[p * K + k];
        if (r == null || busRoot == null) return;
        float ar = a * Mathf.Deg2Rad, er = pEl[p] * Mathf.Deg2Rad;
        Vector3 dir = new Vector3(Mathf.Cos(er) * Mathf.Sin(ar), Mathf.Sin(er), Mathf.Cos(er) * Mathf.Cos(ar));
        Vector3 local = origin + dir * pDist[p];
        Vector3 world = busRoot.TransformPoint(local);
        Vector3 head = HeadPos();
        // +Z away from the viewer (TMP reads right only that way), Vector3.up of the bus: the line stays level (§1.3.6)
        Quaternion rot = Quaternion.LookRotation(world - head, busRoot.up);
        r.position = world;
        r.rotation = rot;
    }

    private float HeadYaw()
    {
        VRCPlayerApi lp = Networking.LocalPlayer;
        if (lp == null || busRoot == null) return 0f;
        Quaternion q = lp.GetTrackingData(VRCPlayerApi.TrackingDataType.Head).rotation;
        Vector3 f = Quaternion.Inverse(busRoot.rotation) * (q * Vector3.forward);
        return Mathf.Atan2(f.x, f.z) * Mathf.Rad2Deg;
    }

    private Vector3 HeadPos()
    {
        VRCPlayerApi lp = Networking.LocalPlayer;
        if (lp == null) return busRoot != null ? busRoot.TransformPoint(seatEye != null && seatEye.Length > seat ? seatEye[seat] : eyeLocal) : Vector3.zero;
        return lp.GetTrackingData(VRCPlayerApi.TrackingDataType.Head).position;
    }

    // ------------------------------------------------------------------------------------------ drawing
    private void HideSlot(int slot)
    {
        int a = slotObjStart[slot], b = a + slotObjCount[slot];
        for (int i = a; i < b; i++) if (oGo[i] != null && oGo[i].activeSelf) oGo[i].SetActive(false);
        a = slotScrimStart[slot]; b = a + slotScrimCount[slot];
        for (int i = a; i < b; i++) if (sRenderer[i] != null) sRenderer[i].enabled = false;
    }

    private void DrawSlot(int slot, float dist, float t)
    {
        int a = slotObjStart[slot], b = a + slotObjCount[slot];
        for (int i = a; i < b; i++)
        {
            float u = t - oStart[i];
            bool on = u >= 0f && !(oExitS[i] > 0f && t >= oExitT[i] + oExitS[i]);
            if (oGo[i] == null) continue;
            if (oGo[i].activeSelf != on) oGo[i].SetActive(on);
            if (!on) continue;
            float x = oFocus[i] > 0f ? Mathf.Clamp01(u / oFocus[i]) : 1f;
            float e = 1f - (1f - x) * (1f - x) * (1f - x);              // ease-out, monotone (§7.4-4)
            float alpha = oAlpha[i] * e;
            float soft = Mathf.Lerp(0.9f, oSoftEnd[i], e);
            float v = oExitS[i] > 0f ? Mathf.Clamp01((t - oExitT[i]) / oExitS[i]) : 0f;
            alpha *= 1f - v * v * (3f - 2f * v);
            Transform tr = oGo[i].transform;
            Vector3 lp = tr.localPosition;
            lp.y = oLocalY[i] + oDrift[i] * dist * Mathf.Tan(0.2f * v * Mathf.Deg2Rad);
            tr.localPosition = lp;
            if (oCueCount[i] > 0 && oTmp[i] != null)
            {
                int vis = 0;
                for (int c = 0; c < oCueCount[i]; c++) if (t >= cueT[oCueStart[i] + c]) vis = c + 1;
                if (oTmp[i].maxVisibleLines != vis) oTmp[i].maxVisibleLines = vis;
            }
            Vector4 f = oFill[i];
            f.w = alpha;
            _mpb.SetVector(_idFace, f);
            _mpb.SetFloat(_idSoft, soft);
            _mpb.SetFloat(_idDilate, _dilate);
            if (oRenderer[i] != null) oRenderer[i].SetPropertyBlock(_mpb);
        }
        a = slotScrimStart[slot]; b = a + slotScrimCount[slot];
        for (int i = a; i < b; i++)
        {
            if (sRenderer[i] == null) continue;
            float u = t - sStart[i];
            float x = Mathf.Clamp01(u / 2.5f);
            float v = sExitS[i] > 0f ? Mathf.Clamp01((t - sExitT[i]) / sExitS[i]) : 0f;
            float al = sAlpha[i] * (1f - (1f - x) * (1f - x) * (1f - x)) * (1f - v * v * (3f - 2f * v));
            bool on = u >= 0f && al > 0f;
            if (sRenderer[i].enabled != on) sRenderer[i].enabled = on;
            if (on) sRenderer[i].color = new Color(1f, 1f, 1f, al);
        }
    }

    // ------------------------------------------------------------------------------------------ notice board (D-31)
    // LB_Journey calls this every frame before departure (seconds to departure), LanbaiBoardHide() after.
    public void LanbaiBoard(float secondsToDeparture)
    {
        int k = key == 4 ? 3 : key;                                  // de -> the English board
        if (boardRoot == null || k >= boardRoot.Length) return;
        if (boardButtons != null && !boardButtons.activeSelf) boardButtons.SetActive(true);
        if (_boardKey != k)
        {
            for (int i = 0; i < boardRoot.Length; i++) if (boardRoot[i] != null) boardRoot[i].SetActive(i == k);
            _boardKey = k;
        }
        int s = Mathf.Max(0, Mathf.CeilToInt(secondsToDeparture));
        if (boardLine1 != null && k < boardLine1.Length && boardLine1[k] != null)
            boardLine1[k].text = boardPrefix[k] + s.ToString() + boardSuffix[k];
    }

    public void LanbaiBoardHide()
    {
        if (boardButtons != null) boardButtons.SetActive(false);
        if (boardRoot == null) return;
        for (int i = 0; i < boardRoot.Length; i++) if (boardRoot[i] != null) boardRoot[i].SetActive(false);
        _boardKey = -1;
    }
}
