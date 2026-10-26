// 生成的（Palace/Source/gen_layout.py），不要手改。数据源 = Palace/PalaceLayout.json
public static class LanbaiPalaceData
{
    public const float TerraceDepth = 250.3350f;
    public const float LipY = -13.000f;   // 台地下唇（海的约定 terrace.lip_bottom_y）：眼睛低于它，灯焰的深度往前挪（终审 10-25 #3）
    public static readonly float[] WashLinear = { 0.00150f, 0.00380f, 0.00520f };   // 上方微光卡的颜色（线性，加在水色上）
    public const float FogScale = 0.420f;   // 宫殿几何的雾密度倍数（终审 10-25 #1）
    public static readonly float[] Flames = { -9.00000f, 1.62000f, 54.39000f, -27.00000f, 1.62000f, 54.39000f, -9.00000f, 1.50000f, 72.24000f, -27.00000f, 1.50000f, 72.24000f, -9.00000f, 1.62000f, 90.44000f, -27.00000f, 1.62000f, 90.44000f, -9.00000f, 1.50000f, 108.29000f, -27.00000f, 1.50000f, 108.29000f, -9.00000f, 1.62000f, 126.49000f, -27.00000f, 1.62000f, 126.49000f, -9.00000f, 1.50000f, 144.34000f, -27.00000f, 1.50000f, 144.34000f, -9.00000f, 1.62000f, 162.19000f, -27.00000f, 1.62000f, 162.19000f, -9.00000f, 1.50000f, 180.39000f, -27.00000f, 1.50000f, 180.39000f, -9.00000f, 1.62000f, 198.24000f, -27.00000f, 1.62000f, 198.24000f, -9.00000f, 1.50000f, 216.44000f, -27.00000f, 1.50000f, 216.44000f, -9.00000f, 1.62000f, 234.29000f, -27.00000f, 1.62000f, 234.29000f, -9.00000f, 1.50000f, 252.49000f, -27.00000f, 1.50000f, 252.49000f, -13.00000f, 7.66000f, 335.30000f, -23.00000f, 7.66000f, 335.30000f, -34.00000f, 7.66000f, 335.30000f, -45.00000f, 7.66000f, 335.30000f, -56.00000f, 7.66000f, 335.30000f, -66.00000f, 7.66000f, 335.30000f, -12.00000f, 3.62000f, 34.79000f, -24.00000f, 3.62000f, 34.79000f };
    public static readonly bool[] LampIndigo = { true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true };   // 第 8 轮：全部加靛光（阙前两盏也加）
    public static readonly float[] LampGain = { 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f };   // 烘焙的暖 / 靛 × 这个（阙前两盏立灯 ×4，第 8 轮）
    public static readonly float[] LampIndigoGain = { 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 0.45f, 0.45f };
    public const float CowrieLampGain = 1.50f;   // 宝贝贴面的解析高光增益
    public static readonly float[] LampIndigoLift = { 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 4.00f, 0.00f, 0.00f };   // 阙前两盏 0（不抬高）
    public static readonly float[] LampIndigoRange = { 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 12.00f, 5.00f, 5.00f };   // 阙前两盏 5 m
    public static readonly string[] LampIds = { "Lamp_R01", "Lamp_L01", "Lamp_R02", "Lamp_L02", "Lamp_R03", "Lamp_L03", "Lamp_R04", "Lamp_L04", "Lamp_R05", "Lamp_L05", "Lamp_R06", "Lamp_L06", "Lamp_R07", "Lamp_L07", "Lamp_R08", "Lamp_L08", "Lamp_R09", "Lamp_L09", "Lamp_R10", "Lamp_L10", "Lamp_R11", "Lamp_L11", "Lamp_R12", "Lamp_L12", "Lamp_P01", "Lamp_P02", "Lamp_P03", "Lamp_P04", "Lamp_P05", "Lamp_P06", "Lamp_Q1", "Lamp_Q2" };
    public static readonly float[] DoorCentre = { -18.00000f, 9.75000f, 343.50000f };
    public const float DoorHalfHeight = 3.750f, DoorSpecI = 60.000f, NacreLampGain = 1.00f;
    public const float NacreLift = 0.00f, NacreSpread = 0.024f;
    public const float BandGain = 0.100f, BandWidth = 0.60f, BandReach = 6.00f;   // 珍珠光带（终审 10-25 #5）
    public const float WarmI = 5.4600f, WarmRange = 3.500f, IndigoI = 28.0000f, IndigoRange = 12.000f, IndigoLift = 4.00f;
    public static readonly float[] WarmColor = { 1.00000f, 0.33245f, 0.02843f };   // 线性 #FF9C2F
    public static readonly float[] IndigoColor = { 0.02315f, 0.09084f, 0.19807f };   // 线性 #2A557B
    public static readonly float[] DoorColor = { 1.00000f, 0.47353f, 0.07421f };   // 线性 #FFB74D
    // 第 8 轮：门的两盏烘焙聚光（有范围窗）
    public static readonly float[] DoorSpillPos = { -18.00000f, 10.12500f, 342.30000f }, DoorSpillDir = { 0.00000f, -0.35000f, -1.00000f };
    public static readonly float DoorSpillI = 60.000f, DoorSpillRange = 4.00f, DoorSpillAngle = 90.0f;
    public static readonly float[] DoorAccentPos = { -18.00000f, 11.00000f, 335.60000f }, DoorAccentTarget = { -18.00000f, 11.50000f, 342.60000f };   // D-31：只参与烘焙，门前 7 m、朝门
    public static readonly float DoorAccentI = 40.000f, DoorAccentRange = 9.00f, DoorAccentAngle = 70.0f;
    public static readonly float[] AmbSky = { 0.00439f, 0.02956f, 0.08022f }, AmbEquator = { 0.00304f, 0.01600f, 0.03955f }, AmbGround = { 0.01033f, 0.00700f, 0.01600f };
    public static readonly float[] FlameLinear = { 8.63380f, 0.96640f, 0.19990f };
    public static readonly float[] HaloMid = { 0.05781f, 0.12214f, 0.22323f };
    public static readonly float[] FishCentre = { -38.00000f, 14.00000f, 356.60000f };
    public const float FishR = 35.00f, FishTube = 9.00f, FishRev = 0.0300f;
    public static readonly float[] FishPassPoint = { 1.44900f, 5.13300f, 232.33400f, 720.00000f };
    public static readonly float[] FishPassVel = { -2.2f, 0.1f, 0.4f, 0f };
}
