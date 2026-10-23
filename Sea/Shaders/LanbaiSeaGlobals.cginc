// Lanbai / LanbaiSeaGlobals.cginc  -- the sea's _Udon_ globals that are not (yet) in Common/Shaders/LanbaiGlobals.cginc.
// Same guard macro as the generator (LANBAI_DECL_<name>): when the registry adds them, whichever file comes first wins
// and there is never a second declaration (FXC X3003). Registration asked in Sea/给总控.md.
#ifndef LANBAI_SEA_GLOBALS_INCLUDED
#define LANBAI_SEA_GLOBALS_INCLUDED
#ifndef LANBAI_DECL__Udon_T
#define LANBAI_DECL__Udon_T
float _Udon_T;            // (not yet in LanbaiGlobals.cginc: Sea/给总控.md)
#endif
#ifndef LANBAI_DECL__Udon_SeaBus
#define LANBAI_DECL__Udon_SeaBus
float4 _Udon_SeaBus;            // (not yet in LanbaiGlobals.cginc: Sea/给总控.md)
#endif
#ifndef LANBAI_DECL__Udon_SeaBusVel
#define LANBAI_DECL__Udon_SeaBusVel
float4 _Udon_SeaBusVel;            // (not yet in LanbaiGlobals.cginc: Sea/给总控.md)
#endif
#endif
