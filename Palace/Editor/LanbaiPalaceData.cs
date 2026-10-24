// 生成的（Palace/Source/gen_layout.py），不要手改。数据源 = Palace/PalaceLayout.json
public static class LanbaiPalaceData
{
    public const float TerraceDepth = 250.3350f;
    public static readonly float[] Flames = { -9.00000f, 1.62000f, 54.39000f, -27.00000f, 1.62000f, 54.39000f, -9.00000f, 1.50000f, 72.24000f, -27.00000f, 1.50000f, 72.24000f, -9.00000f, 1.62000f, 90.44000f, -27.00000f, 1.62000f, 90.44000f, -9.00000f, 1.50000f, 108.29000f, -27.00000f, 1.50000f, 108.29000f, -9.00000f, 1.62000f, 126.49000f, -27.00000f, 1.62000f, 126.49000f, -9.00000f, 1.50000f, 144.34000f, -27.00000f, 1.50000f, 144.34000f, -9.00000f, 1.62000f, 162.19000f, -27.00000f, 1.62000f, 162.19000f, -9.00000f, 1.50000f, 180.39000f, -27.00000f, 1.50000f, 180.39000f, -9.00000f, 1.62000f, 198.24000f, -27.00000f, 1.62000f, 198.24000f, -9.00000f, 1.50000f, 216.44000f, -27.00000f, 1.50000f, 216.44000f, -9.00000f, 1.62000f, 234.29000f, -27.00000f, 1.62000f, 234.29000f, -9.00000f, 1.50000f, 252.49000f, -27.00000f, 1.50000f, 252.49000f, -13.00000f, 7.66000f, 335.30000f, -23.00000f, 7.66000f, 335.30000f, -34.00000f, 7.66000f, 335.30000f, -45.00000f, 7.66000f, 335.30000f, -56.00000f, 7.66000f, 335.30000f, -66.00000f, 7.66000f, 335.30000f, -12.00000f, 1.62000f, 34.79000f, -24.00000f, 1.62000f, 34.79000f };
    public static readonly bool[] LampIndigo = { true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, false, false };   // 阙前的两盏不加靛光
    public static readonly string[] LampIds = { "Lamp_R01", "Lamp_L01", "Lamp_R02", "Lamp_L02", "Lamp_R03", "Lamp_L03", "Lamp_R04", "Lamp_L04", "Lamp_R05", "Lamp_L05", "Lamp_R06", "Lamp_L06", "Lamp_R07", "Lamp_L07", "Lamp_R08", "Lamp_L08", "Lamp_R09", "Lamp_L09", "Lamp_R10", "Lamp_L10", "Lamp_R11", "Lamp_L11", "Lamp_R12", "Lamp_L12", "Lamp_P01", "Lamp_P02", "Lamp_P03", "Lamp_P04", "Lamp_P05", "Lamp_P06", "Lamp_Q1", "Lamp_Q2" };
    public static readonly float[] DoorCentre = { -18.00000f, 9.75000f, 343.50000f };
    public const float DoorHalfHeight = 3.750f, DoorSpecI = 60.000f, NacreLampGain = 6.00f;
    public const float WarmI = 5.4600f, WarmRange = 4.000f, IndigoI = 28.0000f, IndigoRange = 12.000f, IndigoLift = 4.00f;
    public static readonly float[] WarmColor = { 1.00000f, 0.33245f, 0.02843f };   // 线性 #FF9C2F
    public static readonly float[] IndigoColor = { 0.02315f, 0.09084f, 0.19807f };   // 线性 #2A557B
    public static readonly float[] DoorSpillPos = { -18.00000f, 9.75000f, 343.20000f };
    public static readonly float[] DoorSpillSize = { 3.99000f, 7.12000f };
    public static readonly float[] DoorColor = { 1.00000f, 0.47353f, 0.07421f };   // 线性 #FFB74D
    public static readonly float DoorAreaI = 770.0000f, PourRatio = 0.000f;
    public static readonly float[] DoorAccentPos = { -18.00000f, 11.00000f, 335.60000f };   // D-31：只参与烘焙的面光，门前 7 m、朝门
    public static readonly float DoorAccentI = 0.125f;   // 按灰卡校（README §4），单位没对过
    public static readonly float[] DoorPourPos = { -18.00000f, 12.90000f, 342.90000f };   // 门楣处，朝外向下 35°
    public static readonly float[] AmbSky = { 0.00439f, 0.02956f, 0.08022f }, AmbEquator = { 0.00304f, 0.01600f, 0.03955f }, AmbGround = { 0.01033f, 0.00700f, 0.01600f };
    public static readonly float[] FlameLinear = { 8.63380f, 0.96640f, 0.19990f };
    public static readonly float[] HaloMid = { 0.05781f, 0.12214f, 0.22323f };
    public static readonly float[] FishCentre = { -38.00000f, 14.00000f, 356.60000f };
    public const float FishR = 35.00f, FishTube = 9.00f, FishRev = 0.0300f;
    public static readonly float[] FishPassPoint = { 1.44900f, 5.13300f, 232.33400f, 720.00000f };
    public static readonly float[] FishPassVel = { -2.2f, 0.1f, 0.4f, 0f };
}
