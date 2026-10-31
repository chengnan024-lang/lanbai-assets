// =====================================================================================================
//  LanbaiPoemDriver.cs   蓝白 · 诗句的运行时（UdonSharp），字体套件第 5 版（D-45，2026-10-25，总工程师）
//  !!! WRITTEN WITHOUT A UNITY COMPILER. Checked with Common/Tools~/compile_check (Roslyn + U# rules) only. !!!
//
//  Every field is filled by 蓝白/Fonts/Build Subtitles (v5) (Fonts/Editor/LanbaiPoemBake.cs) from Fonts/strings_all.json.
//
//  Director interface (CONTROL §5), unchanged from v4.1: LanbaiTick(t) every frame (Update), LanbaiActivate(on),
//  LanbaiWindow() = the whole film, LanbaiTakesOverNothing(). LB_Journey: LanbaiBoard(s) / LanbaiBoardHide(), SetSeat(s).
//  Board buttons (LanbaiLangButton -> SendCustomEvent): _LangZhs, _LangZht, _LangJa, _LangEn, _SubFollow, _SubStay,
//  _SubOff; _LangZh is kept with its v4 meaning (the local test tool sends it).
//
//  1. Subtitles (D-45, Art/字幕方案_D-45.md B–D): the poems are one or two lines of white text in the lower part of the
//     view. LanbaiTick only decides, from t alone (D-33 #6), which poem / page / line alphas are live and puts the page's
//     text on the font's two line objects (Line_T, Line_B; one pair per font, only the current font's pair is on).
//     PostLateUpdate places the rig: VR = lazy follow (C.3: yaw dead zone, critically damped spring, <= 60°/s, pitch in
//     three bands with hysteresis, fast-turn hide, ±120° limit), depth from the bus's table (C.2) or the fallbacks;
//     desktop = in front of VRCCameraSettings.ScreenCamera at 1 m, em = 4.2 % of the screen height (C.8). Mode 1
//     ("stay") anchors each poem once; mode 2 ("off") shows no subtitles (the world text below still shows).
//     Look: _FaceColor = the solved linear fill × 2^(−ΔEV) (LanbaiExposure, as the overlay sphere) with the line's alpha
//     (Lanbai/Subtitle multiplies the underlay by it), _FaceDilate 0.10 VR / 0.05 desktop; the line halos
//     (Lanbai/SubtitleHalo) take the poem's halo fill and alpha × the line's alpha.
//  2. World text (v4.1 path, D-45 #15.4 / G.1): the Han characters of Tianwen in the sky (everyone) and the Zhuangzi
//     column (zh / en / de: simplified, zht / ja: traditional). Objects baked in the scene, fixed in bus space.
//  3. The board's settings card (F.2) before departure; 4. the desktop letterbox (D-45 #15.3), desktop only.
//
//  Language (D-30, D-31 #1, F.4): VRCPlayerApi.GetCurrentLanguage() -> key by prefix (zh-HK / zh-TW / zh-Hant first);
//  OnLanguageChanged re-maps unless the player chose on the board. Keys: 0 zh, 1 zht, 2 ja, 3 en, 4 de.
// =====================================================================================================
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;
using VRC.SDK3.Rendering;
using TMPro;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class LanbaiPoemDriver : UdonSharpBehaviour
{
    public const int K = 5;                          // zh, zht, ja, en, de
    public const int NF = 5;                         // subtitle fonts: SC, TC, JP, Garamond, Garamond Italic
    [Header("Scene")]
    public Transform busRoot;                        // the bus (cabin space); poemsRoot is re-parented under it at Start
    public Transform poemsRoot;                      // world text (Tianwen's sky characters, the Zhuangzi column)
    public Vector3 eyeLocal = new Vector3(0.55f, 1.70f, 2.05f);   // the main seat's eye in bus space (BusLayout.json)
    public LanbaiExposure exposure;                  // ΔEV the EXPO helpers apply (null -> 0)
    public bool useLocalAppliedExposure;             // Local Journey owns PPv2; updated after ApplyGrades, before PostLateUpdate.
    public float localAppliedDeltaEV;

    // ------------------------------------------------------------------------------- 2. world text (v4.1 path)
    [Header("World text (one entry per poem that keeps world text)")]
    public string[] pId;
    public float[] pT0;                              // t_appear
    public float[] pTgone;                           // t_gone: nothing of the poem after this
    public float[] pAz, pEl, pDist;                  // anchor (deg, deg, m); pAzKey[p * K + k] per key
    public float[] pAzKey;
    public Transform[] slotRoot;                     // [p * K + k] (keys reading the same column share the objects)
    public int[] slotObjStart, slotObjCount;
    public int[] slotScrimStart, slotScrimCount;
    public GameObject[] oGo;
    public MeshRenderer[] oRenderer;
    public Vector4[] oFill;                          // solved linear _FaceColor (rgb)
    public float[] oAlpha, oStart, oFocus, oSoftEnd, oExitT, oExitS, oDrift, oLocalY;
    public SpriteRenderer[] sRenderer;
    public float[] sAlpha, sStart, sExitT, sExitS;

    // ------------------------------------------------------------------------------- 1. subtitles
    [Header("Subtitle rig: per font (SC, TC, JP, Garamond, Garamond Italic) a top and a bottom line")]
    public Transform subRig;                         // origin = the last line's em centre; built at 1 m, scaled by depth
    public GameObject[] subFontRoot;                 // [f]: holds Line_T / Line_B of that font
    public TextMeshPro[] subTop, subBot;
    public MeshRenderer[] subTopR, subBotR;
    public float[] fontCentre;                       // em centre above the baseline (em) per font
    public float[] fontPitch;                        // line pitch (em) per font
    public SpriteRenderer haloTop, haloBot;
    public float haloBaseW = 1f, haloBaseH = 1f;     // halo sprite size (m) at localScale 1
    public float haloPadEm = 1.2f, haloHEm = 1.8f;
    public float emM = 0.031418f;                    // em (m) at 1 m = 2 tan(0.9°): em 1.8°

    [Header("Subtitles: per poem")]
    public float[] sT0, sTend, sOutLast, sE, sHalo;  // first page in, gone, last fade, last-line elevation, halo alpha
    public Vector4[] sFill, sHaloFill;               // linear fills (rgb)
    public int[] sPgStart, sPgCount;                 // [s * K + k] -> pages
    [Header("Subtitles: pages")]
    public float[] pgT, pgTout, pgTgone;             // fade-in start; fade-out start; gone
    public int[] pgFont;
    public string[] pgTop, pgBot;                    // pgTop "" = a one-line page (it sits on the last line)
    public float[] pgTopT, pgBotT, pgLineIn;         // when each line starts to appear; its fade-in (s)
    public float[] pgTopX, pgBotX, pgTopW, pgBotW;   // hang offset and width (em)
    public float[] pgHalfW;                          // half the widest line (deg): the yaw dead zone

    [Header("Rig parameters (subtitle_rig of strings_all.json)")]
    public float fadeIn = 0.30f;
    public float yawDeadMin = 12f, yawDeadMargin = 3f, yawStopErr = 1.5f, yawStopVel = 3f;
    public float omega = 4.5f, maxSpeed = 60f, yawLimit = 120f, yawLimitBack = 110f, firstHold = 0.6f;
    public float upEnter = 27f, upExit = 23f, pitchHold = 0.4f, upCap = 35f;
    public float lowBand = -12f, lowAbove = 12f, lowFloor = -36f, lowMove = 3f, lowStop = 1f;
    public float fastDps = 120f, fastErr = 40f, fastOut = 0.15f, settleDps = 30f, settleS = 0.25f, fastIn = 0.30f;
    public float headTau = 0.5f;
    public float depthMain = 1f, depthMin = 0.45f, depthMax = 1f, depthNear = 0.92f, depthRate = 0.5f;
    public float depthFbMain30 = 1f, depthFbMainOther = 0.6f, depthFbOther = 0.45f, depthFbUnseated = 0.8f;
    public float[] depthTable;                       // [(seat * 24 + yawCell) * 9 + pitchCell]: final depth (m, the bus applied 0.92 / clamp); empty -> fallbacks
    public float deskDist = 1f, deskEmFrac = 0.042f, deskBaseFrac = 0.08f, deskFov = 60f;
    public float dilateVR = 0.10f, dilateDesk = 0.05f;

    [Header("Board settings card (F.2): per display key 0..3 (zh, zht, ja, en)")]
    public GameObject boardCard;
    public GameObject[] boardLangSet;                // the card's text in that language
    public TextMeshPro[] boardLine1;                 // "the bus leaves in {0} s": only when s > 0
    public string[] boardPrefix, boardSuffix;
    public TextMeshPro[] boardLangRow;               // 简体中文 / 繁體中文 / 日本語 / English (every player sees these)
    public TextMeshPro[] boardModeRow;               // [displayKey * 3 + mode]
    public GameObject boardDeNote;                   // "Deutsch" next to English: German clients only
    public Transform boardPinLang, boardPinMode;
    public Vector3[] boardPinLangPos, boardPinModePos;
    public GameObject boardButtons;                  // the Interact colliders: off after departure (§6·12)
    public Color boardInk = new Color(0.137f, 0.153f, 0.180f, 1f);   // #23272E
    public float boardDim = 0.55f;

    [Header("Desktop letterbox (D-45 #15.3): desktop only, three set pieces")]
    public Transform lbQuad;                         // a Quad with Lanbai/Letterbox; sized to the view at lbDist
    public MeshRenderer lbRenderer;
    public float[] lbT0, lbT1;
    public float lbAspect = 2.39f, lbCornerDeg = 45f, lbSlide = 1.5f, lbDist = 0.9f;
    public float lbCornerFrac = 0.5f;                // the corner cut is this fraction of the bar's height deep
    public bool lbSubsInBar = true;                  // while the bars are in, the subtitles sit centred in the bottom bar

    [Header("State (read only)")]
    public int key = 3;
    public int overrideKey = -1;
    public int mode = 0;                             // 0 follow, 1 stay, 2 off
    public int seat = -1;                            // the bus's seat order (main 0); -1 = not seated (SetSeat)
    public string clientLanguage = "";

    private MaterialPropertyBlock _mpb;
    private int _idFace, _idSoft, _idDilate, _idColor, _idSlide, _idAspect, _idCut;
    private bool _vr;
    private bool _active = true;
    private bool[] _shown;
    private int[] _shownKey;
    private bool[] _placed;
    private int _boardKey = -1, _boardSel = -1, _boardMode = -1;
    private bool _boardDe;
    // subtitles: what LanbaiTick decided
    private float _t;
    private int _sCur = -1, _pg = -1, _pgShown = -1, _fontShown = -1;
    private float _aTop, _aBot;
    // follow state (PostLateUpdate)
    private int _placedS = -1;
    private bool _haveHead, _headOk;
    private Vector3 _headL;
    private float _hYaw, _hPitch, _angVel;
    private Vector3 _hp, _prevFwd;
    private float _yaw, _yawVel, _el, _elVel, _depth = 1f;
    private bool _chaseYaw, _chaseEl;
    private int _pitchMode;
    private float _pitchTimer, _holdUntil, _waitNew;
    private int _fState;                             // 0 shown, 1 fading out, 2 hidden, 3 fading in
    private int _hideReason;                         // 1 fast turn, 2 yaw limit
    private float _fade = 1f, _fTimer, _calmT;
    private float _lbE, _lbBar;                      // this frame: slide (eased 0..1) and bar height (fraction of the view)

    void Start()
    {
        _mpb = new MaterialPropertyBlock();
        _idFace = VRCShader.PropertyToID("_FaceColor");
        _idSoft = VRCShader.PropertyToID("_OutlineSoftness");
        _idDilate = VRCShader.PropertyToID("_FaceDilate");
        _idColor = VRCShader.PropertyToID("_Color");
        _idSlide = VRCShader.PropertyToID("_Slide");
        _idAspect = VRCShader.PropertyToID("_ScreenAspect");
        _idCut = VRCShader.PropertyToID("_Cut");
        VRCPlayerApi lp = Networking.LocalPlayer;
        _vr = lp != null && lp.IsUserInVR();
        int n = pId != null ? pId.Length : 0;
        _shown = new bool[n];
        _shownKey = new int[n];
        _placed = new bool[n];
        if (poemsRoot != null && busRoot != null) poemsRoot.SetParent(busRoot, false);
        for (int i = 0; i < (oGo != null ? oGo.Length : 0); i++)
            if (oGo[i] != null) oGo[i].SetActive(false);
        for (int i = 0; i < (sRenderer != null ? sRenderer.Length : 0); i++)
            if (sRenderer[i] != null) sRenderer[i].enabled = false;
        if (subRig != null) subRig.gameObject.SetActive(false);
        if (lbQuad != null) lbQuad.gameObject.SetActive(false);
        PickLanguage(VRCPlayerApi.GetCurrentLanguage());
    }

    // ------------------------------------------------------------------------------------------ language and mode
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

    // the board, this player only (F.4): a choice overrides the client language from then on
    public void _LangZhs() { overrideKey = 0; key = 0; }
    public void _LangZht() { overrideKey = 1; key = 1; }
    public void _LangJa() { overrideKey = 2; key = 2; }
    public void _LangEn() { overrideKey = KeyOf(clientLanguage) == 4 ? 4 : 3; key = overrideKey; }   // German clients keep de
    public void _LangZh() { int k = KeyOf(clientLanguage); overrideKey = k == 1 ? 1 : 0; key = overrideKey; }   // v4 alias
    public void _SubFollow() { mode = 0; }
    public void _SubStay() { mode = 1; }
    public void _SubOff() { mode = 2; }

    // ------------------------------------------------------------------------------------------ Director
    // Director v1.1: this driver runs the whole film but takes over no placeholder group (D-33 review #2)
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
        _active = on;
        if (poemsRoot != null) poemsRoot.gameObject.SetActive(on);
        if (!on)
        {
            if (subRig != null) subRig.gameObject.SetActive(false);
            if (lbQuad != null) lbQuad.gameObject.SetActive(false);
        }
    }

    public void LanbaiTick(float t)
    {
        _t = t;
        TickWorld(t);
        TickSubtitles(t);
    }

    // LB_Journey: the local player's seat (the bus's seat order); -1 when not seated. Picks the depth-table row.
    public void SetSeat(int s)
    {
        seat = s;
    }

    // ------------------------------------------------------------------------------------------ 1. subtitles: from t
    private void TickSubtitles(float t)
    {
        int s = -1;
        int n = sT0 != null ? sT0.Length : 0;
        for (int i = 0; i < n; i++)
            if (t >= sT0[i] - 0.05f && t < sTend[i]) { s = i; break; }
        _sCur = s;
        _pg = -1;
        _aTop = 0f;
        _aBot = 0f;
        if (s < 0) return;
        int slot = s * K + key;
        int a = sPgStart[slot], b = a + sPgCount[slot];
        for (int i = a; i < b; i++)
            if (t >= Mathf.Min(pgTopT[i], pgBotT[i]) && t < pgTgone[i]) { _pg = i; break; }
        if (_pg < 0) return;
        int p = _pg;
        float outA = 1f;
        if (t >= pgTout[p])
        {
            float v = Mathf.Clamp01((t - pgTout[p]) / Mathf.Max(0.01f, pgTgone[p] - pgTout[p]));
            outA = 1f - v * v;                                       // ease-in, exactly 0 at pgTgone (D.1)
        }
        _aTop = pgTop[p].Length > 0 ? InA(t, pgTopT[p], pgLineIn[p]) * outA : 0f;
        _aBot = InA(t, pgBotT[p], pgLineIn[p]) * outA;
    }

    private float InA(float t, float t0, float dur)
    {
        if (t < t0) return 0f;
        float x = Mathf.Clamp01((t - t0) / Mathf.Max(0.01f, dur));
        return 1f - (1f - x) * (1f - x);                             // ease-out (D.1)
    }

    // the page's text goes on its font's pair only when the page changes (D-44 #7: assign .text, no maxVisibleLines)
    private void ShowPage(int p)
    {
        int f = pgFont[p];
        if (_fontShown != f)
        {
            for (int i = 0; i < NF; i++)
                if (subFontRoot[i] != null && subFontRoot[i].activeSelf != (i == f)) subFontRoot[i].SetActive(i == f);
            _fontShown = f;
        }
        float em = emM;
        float c = fontCentre[f];
        bool two = pgTop[p].Length > 0;
        subBot[f].text = pgBot[p];
        subBotR[f].transform.localPosition = new Vector3(pgBotX[p] * em, -c * em, 0f);
        subTopR[f].gameObject.SetActive(two);
        if (two)
        {
            subTop[f].text = pgTop[p];
            subTopR[f].transform.localPosition = new Vector3(pgTopX[p] * em, (fontPitch[f] - c) * em, 0f);
        }
        // halos: one per line, centred on the line's em box (B.4 #4)
        if (haloBot != null)
        {
            haloBot.transform.localPosition = new Vector3(pgBotX[p] * em, 0f, 0.002f);
            haloBot.transform.localScale = new Vector3((pgBotW[p] + haloPadEm) * em / haloBaseW, haloHEm * em / haloBaseH, 1f);
        }
        if (haloTop != null)
        {
            haloTop.gameObject.SetActive(two);
            haloTop.transform.localPosition = new Vector3(pgTopX[p] * em, fontPitch[f] * em, 0.002f);
            haloTop.transform.localScale = new Vector3((pgTopW[p] + haloPadEm) * em / haloBaseW, haloHEm * em / haloBaseH, 1f);
        }
        _pgShown = p;
    }

    // ------------------------------------------------------------------------------------------ 1. subtitles: placing
    public override void PostLateUpdate()
    {
        bool show = _active && mode != 2 && _sCur >= 0 && _pg >= 0 && subRig != null;
        if (_vr) SampleHead();                                       // every frame: no stale sample after a page gap
        Letterbox(_active && mode != 2);                             // its segments start ~3 s before their poem
        if (!show)
        {
            if (subRig != null && subRig.gameObject.activeSelf) subRig.gameObject.SetActive(false);
            if (_sCur < 0) { _placedS = -1; _fState = 0; _fade = 1f; _waitNew = 0f; }
            return;
        }
        if (_pgShown != _pg) ShowPage(_pg);
        if (_vr) PlaceVR(); else PlaceDesktop();
        if (!subRig.gameObject.activeSelf && _placedS == _sCur) subRig.gameObject.SetActive(true);
        if (_placedS == _sCur) Draw();
    }

    private void Draw()
    {
        int s = _sCur, f = pgFont[_pg];
        float ev = useLocalAppliedExposure ? localAppliedDeltaEV : (exposure != null ? exposure.GetAppliedDeltaEV() : 0f);
        float k = Mathf.Pow(2f, -ev);
        float vis = _vr ? _fade : 1f;
        float dil = _vr ? dilateVR : dilateDesk;
        Vector4 c = sFill[s] * k;
        c.w = _aBot * vis;
        _mpb.Clear();
        _mpb.SetVector(_idFace, c);
        _mpb.SetFloat(_idDilate, dil);
        if (subBotR[f] != null) subBotR[f].SetPropertyBlock(_mpb);
        c.w = _aTop * vis;
        _mpb.SetVector(_idFace, c);
        if (subTopR[f] != null) subTopR[f].SetPropertyBlock(_mpb);
        if (sHalo[s] > 0f)
        {
            Vector4 h = sHaloFill[s] * k;
            if (haloBot != null) { haloBot.enabled = true; _mpb.Clear(); h.w = sHalo[s] * _aBot * vis; _mpb.SetVector(_idColor, h); haloBot.SetPropertyBlock(_mpb); }
            if (haloTop != null) { haloTop.enabled = _aTop > 0f; _mpb.Clear(); h.w = sHalo[s] * _aTop * vis; _mpb.SetVector(_idColor, h); haloTop.SetPropertyBlock(_mpb); }
        }
        else
        {
            if (haloBot != null && haloBot.enabled) haloBot.enabled = false;
            if (haloTop != null && haloTop.enabled) haloTop.enabled = false;
        }
    }

    // ---- VR: lazy follow in bus space (C.3)
    // head pose in bus space, sampled every PostLateUpdate in VR (also while no page shows)
    private void SampleHead()
    {
        VRCPlayerApi lp = Networking.LocalPlayer;
        if (lp == null) { _headOk = false; return; }
        float dt = Mathf.Max(Time.deltaTime, 0.0001f);
        VRCPlayerApi.TrackingData hd = lp.GetTrackingData(VRCPlayerApi.TrackingDataType.Head);
        Quaternion inv = Quaternion.Inverse(busRoot != null ? busRoot.rotation : Quaternion.identity);
        _headL = busRoot != null ? busRoot.InverseTransformPoint(hd.position) : hd.position;
        Vector3 fwd = inv * (hd.rotation * Vector3.forward);
        _hYaw = Mathf.Atan2(fwd.x, fwd.z) * Mathf.Rad2Deg;
        _hPitch = Mathf.Asin(Mathf.Clamp(fwd.y, -1f, 1f)) * Mathf.Rad2Deg;
        if (!_haveHead) { _hp = _headL; _prevFwd = fwd; _haveHead = true; }
        _hp = Vector3.Lerp(_hp, _headL, 1f - Mathf.Exp(-dt / headTau));
        _angVel = Vector3.Angle(_prevFwd, fwd) / dt;
        _prevFwd = fwd;
        _headOk = true;
    }

    private void PlaceVR()
    {
        if (!_headOk) return;
        float dt = Mathf.Max(Time.deltaTime, 0.0001f);
        Quaternion busRot = busRoot != null ? busRoot.rotation : Quaternion.identity;
        float yaw = _hYaw, th = _hPitch, angVel = _angVel;
        float E = sE[_sCur];

        if (_placedS != _sCur)
        {
            // a new poem appears straight ahead; during a fast turn wait for it to slow down, at most 0.5 s
            if (angVel > fastDps && _waitNew < 0.5f) { _waitNew += dt; return; }
            _hp = _headL;                                            // around where the head is now, not the last poem's
            Anchor(yaw, th, E);
            _depth = DepthTarget();
            _placedS = _sCur;
            _holdUntil = Time.time + firstHold;
            _fState = 0;
            _fade = 1f;
            // placed late (the page's own fade-in is over): fade in here instead of cutting in (D.1);
            // turned beyond the yaw limit: start hidden until the head comes back
            if (_waitNew > 0f) { _fState = 3; _fade = 0f; }
            if (mode == 0 && Mathf.Abs(yaw) > yawLimit) { _fState = 2; _fade = 0f; _hideReason = 2; _fTimer = 0f; _calmT = 0f; }
            _waitNew = 0f;
        }
        else if (mode == 0)
        {
            if (_fState == 0 || _fState == 3)
            {
                if (Mathf.Abs(yaw) > yawLimit) { _fState = 1; _hideReason = 2; }
                else if (angVel > fastDps || Mathf.Abs(Mathf.DeltaAngle(_yaw, yaw)) > fastErr) { _fState = 1; _hideReason = 1; }
            }
            if (_fState == 1)
            {
                _fade -= dt / fastOut;
                if (_fade <= 0f) { _fade = 0f; _fState = 2; _fTimer = 0f; _calmT = 0f; }
            }
            else if (_fState == 2)
            {
                _fTimer += dt;
                _calmT = angVel < settleDps ? _calmT + dt : 0f;
                bool ok = _hideReason != 2 || Mathf.Abs(yaw) < yawLimitBack;
                if (ok && _calmT >= settleS && _fTimer >= settleS) { Anchor(yaw, th, E); _depth = DepthTarget(); _fState = 3; }
            }
            else if (_fState == 3)
            {
                _fade += dt / fastIn;
                if (_fade >= 1f) { _fade = 1f; _fState = 0; }
            }
            if (_fState == 0)
            {
                if (Time.time >= _holdUntil)                         // nothing moves in the first 0.6 s (C.3)
                {
                    FollowYaw(yaw, dt);
                    FollowPitch(th, E, dt);
                }
            }
        }
        // depth: changes only while hidden or moving (> 5°/s), <= 0.5 m/s (C.2)
        float dTarget = DepthTarget();
        if (_fState == 2) _depth = dTarget;
        else if (Mathf.Abs(_yawVel) > 5f || Mathf.Abs(_elVel) > 5f) _depth = Mathf.MoveTowards(_depth, dTarget, depthRate * dt);

        float yr = _yaw * Mathf.Deg2Rad, er = _el * Mathf.Deg2Rad;
        Vector3 dir = new Vector3(Mathf.Cos(er) * Mathf.Sin(yr), Mathf.Sin(er), Mathf.Cos(er) * Mathf.Cos(yr));
        Vector3 local = _hp + dir * _depth;
        Vector3 up = busRoot != null ? busRoot.up : Vector3.up;
        subRig.position = busRoot != null ? busRoot.TransformPoint(local) : local;
        subRig.rotation = Quaternion.LookRotation(busRot * dir, up);    // +Z away from the viewer, level (no roll)
        subRig.localScale = new Vector3(_depth, _depth, _depth);
    }

    private void Anchor(float yaw, float th, float E)
    {
        _yaw = mode == 0 ? Mathf.Clamp(yaw, -yawLimit, yawLimit) : yaw;
        _yawVel = 0f;
        _chaseYaw = false;
        _pitchMode = th > E + upEnter ? 1 : (th < E + lowBand ? 2 : 0);
        _pitchTimer = 0f;
        _el = PitchTarget(th, E);
        _elVel = 0f;
        _chaseEl = false;
    }

    private float PitchTarget(float th, float E)
    {
        if (_pitchMode == 1) return Mathf.Min(th + E, upCap);
        if (_pitchMode == 2) return Mathf.Max(th + lowAbove, lowFloor);
        return E;
    }

    private void FollowYaw(float yaw, float dt)
    {
        float err = Mathf.DeltaAngle(_yaw, yaw);
        float dead = Mathf.Max(yawDeadMin, pgHalfW[_pg] + yawDeadMargin);
        if (!_chaseYaw && Mathf.Abs(err) > dead) _chaseYaw = true;
        if (!_chaseYaw) return;
        // critically damped spring towards the current yaw, <= 60°/s; stop only once caught up (C.3)
        _yawVel += (omega * omega * err - 2f * omega * _yawVel) * dt;
        _yawVel = Mathf.Clamp(_yawVel, -maxSpeed, maxSpeed);
        _yaw += _yawVel * dt;
        if (Mathf.Abs(Mathf.DeltaAngle(_yaw, yaw)) < yawStopErr && Mathf.Abs(_yawVel) < yawStopVel) { _chaseYaw = false; _yawVel = 0f; }
    }

    private void FollowPitch(float th, float E, float dt)
    {
        // three bands with hysteresis (C.3): level E; up after 0.4 s above E + 27°, back after 0.4 s below E + 23°;
        // low below E − 12°: 12° above the gaze, never below −36° (continuous at the boundary)
        if (_pitchMode == 0)
        {
            if (th < E + lowBand) { _pitchMode = 2; _pitchTimer = 0f; }
            else if (th > E + upEnter) { _pitchTimer += dt; if (_pitchTimer >= pitchHold) { _pitchMode = 1; _pitchTimer = 0f; } }
            else _pitchTimer = 0f;
        }
        else if (_pitchMode == 1)
        {
            if (th < E + upExit) { _pitchTimer += dt; if (_pitchTimer >= pitchHold) { _pitchMode = th < E + lowBand ? 2 : 0; _pitchTimer = 0f; } }
            else _pitchTimer = 0f;
        }
        else if (th >= E + lowBand) { _pitchMode = 0; _pitchTimer = 0f; }
        float target = PitchTarget(th, E);
        float err = target - _el;
        float start = _pitchMode == 2 ? lowMove : 0.5f;
        if (!_chaseEl && Mathf.Abs(err) > start) _chaseEl = true;
        if (!_chaseEl) return;
        _elVel += (omega * omega * err - 2f * omega * _elVel) * dt;
        _elVel = Mathf.Clamp(_elVel, -maxSpeed, maxSpeed);
        _el += _elVel * dt;
        if (Mathf.Abs(target - _el) < lowStop && Mathf.Abs(_elVel) < yawStopVel) { _chaseEl = false; _elVel = 0f; }
    }

    // depth from the bus's table (values already clamp(0.92 × first opaque hit, 0.45, 1.0), Bus/给总控.md #32): yaw cells
    // centred on -180 + 15 j, pitch cells on -40 + 10 i; the cell and its two yaw neighbours, the smallest (no
    // interpolation, C.2); no table -> the fallbacks
    private float DepthTarget()
    {
        if (depthTable != null && seat >= 0 && depthTable.Length >= (seat + 1) * 216)
        {
            int yc = Mathf.RoundToInt((_yaw + 180f) / 15f);
            int pc = Mathf.Clamp(Mathf.RoundToInt((_el + 40f) / 10f), 0, 8);
            float d = 1000f;
            for (int j = -1; j <= 1; j++)
            {
                int c = ((yc + j) % 24 + 24) % 24;
                float v = depthTable[(seat * 24 + c) * 9 + pc];
                if (v > 0f && v < d) d = v;
            }
            return Mathf.Clamp(d, depthMin, depthMax);
        }
        if (seat < 0) return depthFbUnseated;
        if (seat > 0) return depthFbOther;
        return Mathf.Abs(_yaw) <= 30f ? depthFbMain30 : depthFbMainOther;
    }

    // ---- desktop: on the screen camera (C.8)
    private void PlaceDesktop()
    {
        Vector3 pos;
        Quaternion rot;
        float fov = deskFov;
        VRCCameraSettings cam = VRCCameraSettings.ScreenCamera;
        if (cam != null)
        {
            pos = cam.Position;
            rot = cam.Rotation;
            if (cam.FieldOfView > 1f) fov = cam.FieldOfView;
        }
        else
        {
            VRCPlayerApi lp = Networking.LocalPlayer;
            if (lp == null) return;
            VRCPlayerApi.TrackingData hd = lp.GetTrackingData(VRCPlayerApi.TrackingDataType.Head);
            pos = hd.position;
            rot = hd.rotation;
        }
        float h = 2f * deskDist * Mathf.Tan(0.5f * fov * Mathf.Deg2Rad);          // view height at deskDist
        float emD = deskEmFrac * h;
        int f = pgFont[_pg];
        float y = -0.5f * h + deskBaseFrac * h + fontCentre[f] * emD;              // last line's em centre
        if (lbSubsInBar && _lbBar > 0f)
        {
            // D-45 #15 r2: with the bars in, the block sits vertically centred in the bottom bar (film-style), moving with
            // the slide; computed from the bar's height, so a new aspect (Fins measured) moves it too
            float blockMid = pgTop[_pg].Length > 0 ? 0.5f * fontPitch[f] * emD : 0f;   // block centre above the last line
            float yBar = -0.5f * h + 0.5f * _lbBar * h - blockMid;
            y = Mathf.Lerp(y, yBar, _lbE);
        }
        subRig.position = pos + rot * new Vector3(0f, y, deskDist);
        subRig.rotation = rot;
        float sc = emD / emM;
        subRig.localScale = new Vector3(sc, sc, sc);
        _placedS = _sCur;
        _fade = 1f;
    }

    // ---- desktop letterbox: 2.39:1, 45° corner cuts, slides in / out over lbSlide s; never in VR; off with the subtitles
    private void Letterbox(bool allowed)
    {
        _lbE = 0f;
        _lbBar = 0f;
        if (lbQuad == null) return;
        float target = 0f;
        if (!_vr && allowed && lbT0 != null)
            for (int i = 0; i < lbT0.Length; i++)
                if (_t >= lbT0[i] && _t < lbT1[i]) { target = 1f; break; }
        // slide from t alone near the edges of a segment, so a joiner / a seek lands on the right state
        float slide = 0f;
        if (target > 0f)
            for (int i = 0; i < lbT0.Length; i++)
                if (_t >= lbT0[i] && _t < lbT1[i])
                    slide = Mathf.Clamp01(Mathf.Min(_t - lbT0[i], lbT1[i] - _t) / Mathf.Max(0.01f, lbSlide));
        bool on = slide > 0f;
        if (lbQuad.gameObject.activeSelf != on) lbQuad.gameObject.SetActive(on);
        if (!on) return;
        Vector3 pos;
        Quaternion rot;
        float fov = deskFov, aspect = 16f / 9f;
        VRCCameraSettings cam = VRCCameraSettings.ScreenCamera;
        if (cam != null)
        {
            pos = cam.Position;
            rot = cam.Rotation;
            if (cam.FieldOfView > 1f) fov = cam.FieldOfView;
            if (cam.PixelHeight > 0) aspect = (float)cam.PixelWidth / cam.PixelHeight;
        }
        else
        {
            VRCPlayerApi lp = Networking.LocalPlayer;
            if (lp == null) return;
            VRCPlayerApi.TrackingData hd = lp.GetTrackingData(VRCPlayerApi.TrackingDataType.Head);
            pos = hd.position;
            rot = hd.rotation;
        }
        const float over = 1.02f;                                                 // 2 % overscan (the shader undoes it)
        float h = 2f * lbDist * Mathf.Tan(0.5f * fov * Mathf.Deg2Rad) * over;
        lbQuad.position = pos + rot * new Vector3(0f, 0f, lbDist);
        lbQuad.rotation = rot;
        lbQuad.localScale = new Vector3(h * aspect, h, 1f);
        float e = slide * slide * (3f - 2f * slide);
        _lbE = e;
        _lbBar = Mathf.Max(0f, 0.5f * (1f - aspect / Mathf.Max(lbAspect, 0.01f))) * e;   // as the shader draws it
        _mpb.Clear();
        _mpb.SetFloat(_idSlide, e);
        _mpb.SetFloat(_idAspect, aspect);
        _mpb.SetVector(_idCut, new Vector4(lbAspect, Mathf.Tan(lbCornerDeg * Mathf.Deg2Rad), over, lbCornerFrac));
        if (lbRenderer != null) lbRenderer.SetPropertyBlock(_mpb);
    }

    // ------------------------------------------------------------------------------------------ 2. world text (v4.1)
    private void TickWorld(float t)
    {
        int n = pId != null ? pId.Length : 0;
        for (int p = 0; p < n; p++)
        {
            bool live = t >= pT0[p] - 0.05f && t < pTgone[p];
            int slot = p * K + key;
            if (!live)
            {
                if (_shown[p]) { HideSlot(p * K + _shownKey[p]); _shown[p] = false; }
                _placed[p] = false;
                continue;
            }
            if (_shown[p] && _shownKey[p] != key && slotObjStart[p * K + _shownKey[p]] != slotObjStart[slot]) HideSlot(p * K + _shownKey[p]);
            if (!_placed[p]) { Place(p); _placed[p] = true; }
            DrawSlot(slot, pDist[p], t);
            _shown[p] = true;
            _shownKey[p] = key;
        }
    }

    private void Place(int p)
    {
        for (int k = 0; k < K; k++)
        {
            int slot = p * K + k;
            float a = pAzKey != null && pAzKey.Length > slot ? pAzKey[slot] : pAz[p];
            PlaceSlot(p, k, a, pEl[p], eyeLocal);
        }
    }

    private void PlaceSlot(int p, int k, float a, float el, Vector3 origin)
    {
        Transform r = slotRoot[p * K + k];
        if (r == null || busRoot == null) return;
        float ar = a * Mathf.Deg2Rad, er = el * Mathf.Deg2Rad;
        Vector3 dir = new Vector3(Mathf.Cos(er) * Mathf.Sin(ar), Mathf.Sin(er), Mathf.Cos(er) * Mathf.Cos(ar));
        Vector3 world = busRoot.TransformPoint(origin + dir * pDist[p]);
        Vector3 eye = busRoot.TransformPoint(origin);
        // +Z away from the viewer (TMP reads right only that way), Vector3.up of the bus: the line stays level (§1.3.6)
        r.position = world;
        r.rotation = Quaternion.LookRotation(world - eye, busRoot.up);
    }

    private void HideSlot(int slot)
    {
        int a = slotObjStart[slot], b = a + slotObjCount[slot];
        for (int i = a; i < b; i++) if (oGo[i] != null && oGo[i].activeSelf) oGo[i].SetActive(false);
        a = slotScrimStart[slot]; b = a + slotScrimCount[slot];
        for (int i = a; i < b; i++) if (sRenderer[i] != null) sRenderer[i].enabled = false;
    }

    private void DrawSlot(int slot, float dist, float t)
    {
        float dil = _vr ? dilateVR : dilateDesk;
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
            Vector4 f = oFill[i];
            f.w = alpha;
            _mpb.Clear();
            _mpb.SetVector(_idFace, f);
            _mpb.SetFloat(_idSoft, soft);
            _mpb.SetFloat(_idDilate, dil);
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

    // ------------------------------------------------------------------------------------------ 3. the board (F.2)
    // LB_Journey calls this every frame before departure (seconds to departure; <= 0: no countdown line), Hide after.
    public void LanbaiBoard(float secondsToDeparture)
    {
        if (boardCard == null) return;
        if (!boardCard.activeSelf) { boardCard.SetActive(true); _boardKey = -1; }
        if (boardButtons != null && !boardButtons.activeSelf) boardButtons.SetActive(true);
        int k = key == 4 ? 3 : key;                                  // de reads the English card
        bool de = key == 4;
        if (_boardKey != k)
        {
            for (int i = 0; i < boardLangSet.Length; i++) if (boardLangSet[i] != null) boardLangSet[i].SetActive(i == k);
            _boardKey = k;
            _boardSel = -1;
            _boardMode = -1;
        }
        if (_boardSel != k || _boardDe != de)
        {
            for (int i = 0; i < boardLangRow.Length; i++)
                if (boardLangRow[i] != null) boardLangRow[i].color = Ink(i == k);
            if (boardDeNote != null) boardDeNote.SetActive(de);
            if (boardPinLang != null && boardPinLangPos != null && k < boardPinLangPos.Length) boardPinLang.localPosition = boardPinLangPos[k];
            _boardSel = k;
            _boardDe = de;
        }
        if (_boardMode != mode)
        {
            for (int m = 0; m < 3; m++)
            {
                int i = k * 3 + m;
                if (boardModeRow != null && i < boardModeRow.Length && boardModeRow[i] != null) boardModeRow[i].color = Ink(m == mode);
            }
            if (boardPinMode != null && boardPinModePos != null && mode < boardPinModePos.Length) boardPinMode.localPosition = boardPinModePos[mode];
            _boardMode = mode;
        }
        if (boardLine1 != null && k < boardLine1.Length && boardLine1[k] != null)
        {
            bool count = secondsToDeparture > 0f;
            GameObject lineObject = ((Component)boardLine1[k]).gameObject;
            if (lineObject.activeSelf != count) lineObject.SetActive(count);
            if (count) boardLine1[k].text = boardPrefix[k] + Mathf.CeilToInt(secondsToDeparture).ToString() + boardSuffix[k];
        }
    }

    private Color Ink(bool selected)
    {
        Color c = boardInk;
        c.a = selected ? 1f : boardDim;
        return c;
    }

    public void LanbaiBoardHide()
    {
        if (boardButtons != null) boardButtons.SetActive(false);
        if (boardCard != null) boardCard.SetActive(false);
        _boardKey = -1;
    }
}
