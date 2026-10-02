# -*- coding: utf-8 -*-
"""v2.1 timeline: every label in timeline seconds (t = 0 at departure).
Measured labels come from FromLocal/cues.json (U, U_sub, F, F_sub). The sub-labels in SUB are the v2.1 additions
(synthesis §1): read off the cues.md notes or the digitised loudness of cues_finale.png (+-0.5-1 s) and must be
dragged by ear in Audacity before the build. The Director binds to labels; seconds here are for humans and tools."""
import json
CUES_JSON = '/home/user/lanbai-assets/FromLocal/cues.json'
J = json.load(open(CUES_JSON, encoding='utf-8'))
FO = J['timeline']['F_offset']            # 240.36  (finale file s -> t)
UO = J['timeline']['T_urlicht']           # 3.0     (urlicht file s -> t)
def uf(file_s): return round(file_s + UO, 2)
def ff(file_s): return round(file_s + FO, 2)

T = {}          # label -> t
SRC = {}        # label -> (file s, source, meaning)
for grp in ('U', 'U_sub', 'F', 'F_sub'):
    for k, v in J[grp].items():
        T[k] = v['t']; SRC[k] = (v['file'], 'cues.json ' + v['conf'], v['event'])

SUB = {   # v2.1 sub-labels (not yet in cues.json): (t, file s, source, what it is, what it drives)
 'U2b': (uf(36.1), 36.1, 'cues.md', '众赞歌第三句起', '灯尽'),
 'U3b': (uf(57.7), 57.7, 'cues.md', '…in größter Pein!', '灯海揭示完'),
 'U4b': (uf(88.6), 88.6, 'cues.md', '第二遍 Je lieber…', '—'),
 'U4h': (uf(96.5), 96.5, 'cues.md', '第二遍 Himmel 高音（到 104.6）', '触云'),
 'U5r': (uf(124.5), 124.5, 'cues.md', '全团休止（到 U6k）', '第一次完全静止'),
 'F0s': (ff(26.0), 26.0, '波形', '召唤的膨胀（号角 + 小号，峰 ≈268.4）', '云塔应答'),
 'F1c': (ff(51.5), 51.5, '波形', '全团渐强起', '云墙升起'),
 'F1t': (ff(61.0), 61.0, 'cues.md', '定音鼓滚奏（到 303.4）', '云墙最高'),
 'F1b1': (ff(78.0), 78.0, '波形', '远方铜管峰（这一段最响）', '太阳重现'),
 'F1b2': (ff(88.0), 88.0, '波形', '第二次铜管峰（−30.5 dB；86.0 只有 −44）', '海镜的第一块'),
 'F1z': (ff(105.0), 105.0, 'cues.md', '第二段鸟鸣（到 353.0）', '用户之句（晨）'),
 'F3e': (ff(234.0), 234.0, '波形', '第一段合唱（含女高音）结束，管弦间奏起', '开始下沉'),
 'F4p': (ff(222.0), 222.0, '波形', '第一段合唱的女高音峰（−24 dB）', '光柱汇成一束落到手上'),
 'F3e1': (ff(266.0), 266.0, '波形', '间奏第一次膨胀（≈504–510，−24 dB）', '斯涅尔之窗最后一闪'),
 'F3e2': (ff(292.0), 292.0, '波形', '间奏第二次膨胀（≈532–534，−24 dB）', '海脊石壁'),
 'F3e3': (ff(316.0), 316.0, '波形', '间奏淡出（≈556–559，落到 −47 dB）', '最后的藍熄灭'),
 'F3i': (ff(318.5), 318.5, '波形', '第二段合唱 Wieder aufzublühn ppp 起', '播种'),
 'F5p': (ff(415.5), 415.5, '波形', '间奏膨胀之峰', '整条神道可见'),
 'F5q': (ff(435.0), 435.0, '波形', '间奏安静的台地（到 ≈707）', '行列'),
 'F5r': (ff(468.5), 468.5, '波形', '间奏第二次膨胀（到 ≈728）', '河伯之问'),
 'F7e': (ff(537.0), 537.0, 'cues.md', '女低音乐句结束', '—'),
 'F7s': (ff(556.5), 556.5, '波形', '女高音 O glaube: du wardst nicht umsonst geboren!', '离开'),
 'F7p': (ff(572.0), 572.0, '波形', '女高音 …gelitten! 的峰（−20 dB，海里最响的独唱）', '宫殿成了头顶的星座'),
 'F8a': (ff(608.5), 608.5, '波形', '合唱强起 Was vergangen, auferstehen!', '宫灯在下面复活'),
 'F8b': (ff(637.6), 637.6, 'cues.md', "Hör' auf zu beben!", '颤动停止，玫瑰光起'),
 'F8c': (ff(661.8), 661.8, 'cues.md', 'Bereite dich zu leben!（到 921.66）', '用户之句（暮）'),
 'F8r': (ff(681.3), 681.3, 'cues.md', '一口气的休止（Bereite dich zu leben! 唱完）', '水里最后的静止'),
 'F9s': (ff(681.5), 681.5, '波形', 'O Schmerz 之前的管弦膨胀（峰 ≈924.9）', '出海 = F9s + 0.5'),
 'F9t': (ff(696.9), 696.9, 'cues.md', 'O Tod! Du Allbezwinger!', '—'),
 'F10e': (ff(716.0), 716.0, 'cues.md', "二重唱 werd' ich entschweben", '唯一的变形'),
 'F10l': (ff(720.7), 720.7, 'cues.md', "zum Licht, zu dem kein Aug' gedrungen", '翼入光'),
}
for k, (t, fs, src, what, use) in SUB.items():
    T[k] = t; SRC[k] = (fs, src, what)

# derived moments used across the bible (seconds, all from labels)
D = dict(
    EXIT=round(T['F9s'] + 0.5, 2),                         # 922.36 sea exit
    STILL=round(T['U12'] - 2.25, 2),                       # 246.39 everything stops before FLASH_TEAR
    FLASH0=round(T['U12'] - 0.75, 2),                      # 247.89
    DAWN0=round(T['F0'] + 2.5, 2),                         # 254.14 first direction starts
    DAWN1=round(T['F0'] + 2.5 + 3.5 + 8.7, 2),             # 266.34 dawn complete (max stagger 3.5 s + 8.7 s per direction), on F0s
    IGNITE_FULL=round(T['F13'] + 4.2, 2),                  # 1022.41 glow gain line full (stars snap on at F13)
    SILENCE_END=round(J['F_sub']['F_end']['t'] + 5.0, 2),  # 1178.46 10 -> 11
)
D['WHITE_HOLD'] = round(D['SILENCE_END'] - T['F16'], 2)     # 29.15
D['W2_0'] = round(D['SILENCE_END'] + 62.0, 2)               # 1240.46
D['CUT3'] = round(D['W2_0'] + 1.5 + 2.0 + 8.0, 2)            # 1251.96: pre-roll 1.5 s + windows-first stagger 2 s + 8.0 s per direction
D['S12_0'] = round(D['CUT3'] + 3.0, 2)                       # 1254.96
D['VG'] = round(2700.0 / (T['U9'] - T['U6']), 2)            # 59.02

# mirrors (final, two phases): phase 1 = mirror 1 (F13 + 14.2) -> mirror 10 = F15 ('tragen!'), gaps 2.5 * r^k counted back from F15,
# r = 1.3083, interior crossings snapped to accents within +-0.8 s keeping gaps non-increasing and >= 2.5 s (work/beauty/mirror2.py);
# phase 2 = the coda: three bell-like crossings on the two strongest coda accents and F16.
MIRRORS = [1032.41, 1054.29, 1070.62, 1082.67, 1092.39, 1099.71, 1105.42, 1109.46, 1112.86, 1115.36, 1125.55, 1137.58, 1149.31]
MIRROR_R1 = 1.3083
D['WHITE0'] = MIRRORS[11]                                    # 1137.58 the white's impact starts on mirror 12 (the coda's loudest accent)
D['WHITE_SWELL_END'] = round(D['WHITE0'] + 1.2 + 6.0, 2)     # 1144.78 = start of the only hush of the star sea
D['WHITE_MASK0'] = round(T['F16'] - 3.0, 2)                  # 1146.31

if __name__ == '__main__':
    for k, v in sorted(T.items(), key=lambda kv: kv[1]):
        print('%-10s %8.2f  %s' % (k, v, SRC[k][2]))
    print(D)
