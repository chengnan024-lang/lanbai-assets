# -*- coding: utf-8 -*-
"""Lanbai / 蓝白 — every string the world displays (art bible v2.1 §4.7, §5.5, §6, §7; lens_story §4.2, §6).

This module is the single source for strings_all.json, the TMP charsets, the font subsets and the proofs.
Edit here, then re-run build_fonts.py and make_proofs.py.

Display-line conventions (bible §7.2 "在停顿处断行，显示行去掉句末'。'"):
  * lines are pre-broken at the pause; TMP word-wrap is OFF;
  * sentence-final 。 is dropped; we ALSO drop a line-final ，/、 (the line break is the pause, and a
    full-width comma at the end of a centred line pulls it half an em off centre). ？ and ！ stay;
  * typographic apostrophe ’ (U+2019) and quotes “ ” in Latin; spaced em dash " — " in English glosses.
Sources of the texts:
  * originals: exactly as in the bible (§7.5, §6); Keats/Rilke/Urlicht spelling checked against the standard texts;
  * ja 書き下し of the Chinese poems, and ALL zh / ja / en translations: written by the cloud art team for this
    world (the bible asks for them in §7.4-7 but does not contain them). Please have a native reader glance at them.
"""

# ----------------------------------------------------------------------------------------------- fonts
# key -> which file the TMP font asset is made from.  'bible' = where the bible names it.
FONTS = {
    'SourceHanSerifSC-Regular': dict(
        original='SourceHanSerifCN-Regular.otf', subset='LanbaiSerifSC-Regular.otf',
        new_family='Lanbai Serif SC', style='Regular', rfn=True, rfn_names=('Source',), cjk=True, lang='zh-Hans',
        tmp_asset='Lanbai_SerifSC_Regular SDF', atlas=(2048, 2048), role='中文玩家看到的全部诗句（原文与德 / 英诗的中译）；天问的汉字；片尾中文姓名与书名',
        bible='§7.1 中文诗句 思源宋体 SC Regular；§5.5 原文姓名'),
    'SourceHanSerifTW-Regular': dict(
        original='SourceHanSerifTW-Regular.otf', subset='LanbaiSerifTC-Regular.otf',
        new_family='Lanbai Serif TC', style='Regular', rfn=True, rfn_names=('Source',), cjk=True, lang='zh-Hant',
        tmp_asset='Lanbai_SerifTC_Regular SDF', atlas=(2048, 2048),
        role='第 4 版（D-31 #1 补充）：繁体中文玩家（客户端 zh-HK）看到的全部诗句与公告板字',
        bible='§7.1 思源宋体（繁体用 TC，D-31）'),
    'SourceHanSerifSC-Medium': dict(
        original='SourceHanSerifCN-Medium.otf', subset='LanbaiSerifSC-Medium.otf',
        new_family='Lanbai Serif SC', style='Medium', rfn=True, rfn_names=('Source',), cjk=True, lang='zh-Hans',
        tmp_asset='Lanbai_SerifSC_Medium SDF', atlas=(2048, 2048), role='片尾「蓝白」与题记（第 4 版：德 / 英诗的中译单独显示，改用 Regular）',
        bible='§7.1 次行 Medium；§5.5「蓝白」思源宋体 SC Medium；lens_story §6 题记 SC Medium'),
    'SourceHanSerifJP-Medium': dict(
        original='SourceHanSerifJP-Medium.otf', subset='LanbaiSerifJP-Medium.otf',
        new_family='Lanbai Serif JP', style='Medium', rfn=True, rfn_names=('Source',), cjk=True, lang='ja',
        tmp_asset='Lanbai_SerifJP_Medium SDF', atlas=(2048, 2048), role='第 4 版：只剩天问下面那一行日文小字（1.8°，次行）',
        bible='§7.1 日文诗句 源ノ明朝 JP Regular / Medium；§7.3 次行 Medium'),
    'SourceHanSerifJP-Regular': dict(
        original='SourceHanSerifJP-Regular.otf', subset='LanbaiSerifJP-Regular.otf',
        new_family='Lanbai Serif JP', style='Regular', rfn=True, rfn_names=('Source',), cjk=True, lang='ja',
        tmp_asset='Lanbai_SerifJP_Regular SDF', atlas=(2048, 2048),
        role='第 4 版：日文玩家看到的全部诗句（書き下し与日译，单独一份 = 主行，D-30）',
        bible='§7.1 源ノ明朝 JP Regular / Medium'),
    'SourceHanSansSC-Heavy': dict(
        original='SourceHanSansCN-Heavy.otf', subset='LanbaiSansSC-Heavy.otf',
        new_family='Lanbai Sans SC', style='Heavy', rfn=True, rfn_names=('Source',), cjk=True, lang='zh-Hans', texture_only=True,
        tmp_asset=None, atlas=None, role='目的地牌「蓝白」——贴图（站牌套件已烘好），不做 TMP',
        bible='§4.7 思源黑体 SC Heavy'),
    'EBGaramond-Regular': dict(
        original='EBGaramond[wght].ttf', instance={'wght': 400}, subset='EBGaramond-Regular.Lanbai.ttf',
        rfn=False, cjk=False, lang='en', kern_from_gpos=True,
        tmp_asset='Lanbai_Garamond_Regular SDF', atlas=(1024, 1024), role='英文译文（单独显示，D-30；天问下面的英文小字）；片尾姓名',
        bible='§7.1 英 / 德诗句 EB Garamond Regular；§5.5 原文姓名 EB Garamond Regular'),
    'EBGaramond-Italic': dict(
        original='EBGaramond-Italic[wght].ttf', instance={'wght': 400}, subset='EBGaramond-Italic.Lanbai.ttf',
        rfn=False, cjk=False, lang='de/en', kern_from_gpos=True,
        tmp_asset='Lanbai_Garamond_Italic SDF', atlas=(1024, 1024), role='德文原文（里尔克、Urlicht）、济慈原文；片尾角色名与西文作品名',
        bible='§7.1 德文用 Italic；§7.5 济慈 斜体；§5.5 角色 EB Garamond Italic'),
    'BarlowSemiCondensed-SemiBold': dict(
        original='BarlowSemiCondensed-SemiBold.ttf', subset='BarlowSemiCondensed-SemiBold.Lanbai.ttf',
        rfn=False, cjk=False, lang='en', kern_from_gpos=True,
        tmp_asset='Lanbai_Barlow_SemiBold SDF', atlas=(1024, 1024), role='片尾标题 LANBAI（字距 +0.3 em）',
        bible='§5.5 标题 Barlow Semi Condensed SemiBold'),
    'IMFellEnglish-Roman': dict(
        original='IMFeENrm28P.ttf', subset='LanbaiSlip-Regular.ttf',
        new_family='Lanbai Slip', style='Regular', rfn=True, rfn_names=('IM FELL', 'IM_FELL', 'FELL English'),
        cjk=False, lang='en',
        tmp_asset='Lanbai_Slip_Roman SDF', atlas=(1024, 1024), role='Coleridge 纸条正文（站牌套件已烘成贴图；TMP 仅备用）',
        bible='§5.5 / §7.1 IM FELL English'),
    'IMFellEnglishSC': dict(
        original='IMFeENsc28P.ttf', subset='LanbaiSlipSC-Regular.ttf',
        new_family='Lanbai Slip SC', style='Regular', rfn=True, rfn_names=('IM FELL', 'IM_FELL', 'FELL English'),
        cjk=False, lang='en',
        tmp_asset='Lanbai_Slip_SC SDF', atlas=(1024, 1024), role='Coleridge 纸条标题（小型大写字；同上，TMP 仅备用）',
        bible='§5.5 IM FELL English（标题用同家族的 SC）'),
}

# ------------------------------------------------------------------------------------------ colours
INK_CREDITS = '#23272E'
PAPER = '#E8E3D3'
SLIP_PAPER = '#E4D9BE'
SCRIM_DARK = ('#0E1A2F', 0.30)     # §7.2 暗衬, 40 px feather
SCRIM_LIGHT = ('#E8F1F5', 0.25)    # §7.2 亮衬 (scene 6d only)

# display rule v4 (D-30, 2026-10-24; overrides bible §7.4-7 "original main line + own language beneath"):
#   every player sees ONE language: the client language mapped to a player key (zh-* -> zh, ja -> ja, de -> de,
#   anything else -> en); the original when it is in that language, otherwise the translation into it; a de player
#   reads German originals and English for everything else. Chinese poems for ja players = 書き下し.
#   Exception (D-30 #4): Tianwen (act 9) is a picture in the sky: everyone sees the Han characters; a non-zh player
#   also gets one small line (1.8°) of their own language beneath.
#   D-31 #1 (supplement): Traditional Chinese = client code zh-HK (VRChat: zh-CN Simplified, zh-HK Traditional;
#   VRCPlayerApi.GetCurrentLanguage() returns RFC 5646 codes since client 2024.1.1) -> player 'zht' (Source Han Serif
#   TC, strings converted with OpenCC s2tw and checked by hand: 枕席 kept, not 枕蓆).
#   First match wins, prefix compare, case-insensitive; empty / null -> 'en'.
PLAYER_OF_CLIENT = (('zh-HK', 'zht'), ('zh-TW', 'zht'), ('zh-Hant', 'zht'), ('zh', 'zh'), ('ja', 'ja'), ('de', 'de'), ('*', 'en'))


def shown_lang(item, player_lang):
    """v4: which text a player sees: 'main' (= the original) or a translation key."""
    if player_lang == item['original']['lang']:
        return 'main'
    if player_lang == 'zht':
        return 'zht'                          # Traditional: the original (zh poems) or the zh translation, converted
    want = player_lang if player_lang in ('zh', 'ja') else 'en'
    if want == item['original']['lang']:
        return 'main'
    return want


def translation_for(item, player_lang):
    """v4: only the Tianwen exception still has a second line (the player's language under the Han picture)."""
    if not item.get('picture'):
        return None
    if player_lang in ('zh', 'zht'):
        return None                           # a Chinese reader reads the picture itself
    k = shown_lang(item, player_lang)
    return None if k == 'main' else k


def seg(main, zh=None, ja=None, en=None, t=None, note=None, upright=None, label=None):
    d = {'main': main}
    if label is not None: d['label'] = label
    if upright is not None: d['upright'] = upright
    if zh is not None: d['zh'] = zh
    if ja is not None: d['ja'] = ja
    if en is not None: d['en'] = en
    if t is not None: d['t'] = t
    if note: d['note'] = note
    return d

# v4: a translation shown alone is the main line -> the main-line weights (§7.1: SC Regular, JP Regular, Garamond Regular).
# Only the Tianwen sub-line (the one secondary line left) keeps the secondary weights (§7.3: Medium).
TR_FONT = {'zh': 'SourceHanSerifSC-Regular', 'zht': 'SourceHanSerifTW-Regular', 'ja': 'SourceHanSerifJP-Regular', 'en': 'EBGaramond-Regular'}
SUB_FONT = {'zh': 'SourceHanSerifSC-Medium', 'zht': 'SourceHanSerifTW-Regular', 'ja': 'SourceHanSerifJP-Medium', 'en': 'EBGaramond-Regular'}
# v4 sizes (D-30 #2): one block, main-line size for whichever script is shown: CJK 2.2–2.4°, Latin / German 2.0–2.2° em.
# Per poem: size_cjk / size_lat. Latin = CJK − 0.2 (the bible's pairing, e.g. Rilke 2.0° em, D-13). Poems whose v3 size
# was outside the range are clamped (size_note says so).
SIZE_RANGE = dict(cjk=(2.2, 2.4), lat=(2.0, 2.2))

# --------------------------------------------------------------------------------------------- poems
# Bible v2.1 §7.5 (measured timeline, t = seconds after departure; 'cue' = the label the time is bound to, bible law 2:
# the Director binds every event to the label, the seconds are for people).
# size = em height in degrees of visual angle (bible §7.3 / §7.5).  place = (azimuth°, elevation°, distance m)
# color_target = the bible's SCREEN TARGET (law 1), never a value to type in: Tools~/lanbai_color.py solves the
# scene-linear _FaceColor fill through the poem's scene grade (verify r2 B.1); TMP Vertex Color stays white.
# t_appear = start of the 2.5 s focus-in; hold_s from t_appear; t_exit = t_appear + hold_s; t_gone = end of the exit.
# hold_formula = §7.4-3: (3 + 0.3 s per CJK character | 0.35 s per Latin word + 2) x 1.3, clamped to [6, 14].
POEMS = [
    dict(id='P03_LiBai_Dream', scene='3', bible='§7.5 #1 / §6·3',
         source='李白《梦游天姥吟留别》', source_en='Li Bai, “Dreaming of Mount Tianmu: A Farewell”',
         original=dict(lang='zh', font='SourceHanSerifSC-Regular'),
         size_main=2.4, size_tr=1.8, color_target='#E2DDD4', opacity=0.90, scrim=None,
         place=(50, -9, 40), cue='U4 − 4.0', t_appear=71.80, hold_s=12.0, t_gone=86.80,
         trigger='U4 − 4.0（71.80；灯海在 U3b 60.70 落定 + 11.1 s）', exit='up 0.2°',
         treatment='暖白，无辉光；两行，断在“，”', staging='together',
         segments=[
             seg(['我欲因之梦吴越'],
                 ja=['我之に因りて', '呉越を夢みんと欲し'],
                 en=['I would dream my way to Wu and Yue,']),
             seg(['一夜飞度镜湖月'],
                 ja=['一夜飛んで度る鏡湖の月'],
                 en=['and in one night fly across', 'the moon on Mirror Lake']),
         ]),
    dict(id='P04a_Rilke', scene='3c', bible='§7.5 #2 / §6·4',
         source='Rainer Maria Rilke, Duineser Elegien I (1923)', source_en='Rilke, Duino Elegies I',
         original=dict(lang='de', font='EBGaramond-Italic'),
         size_main=2.2, size_tr=1.8, color_target='#D8DDE6', opacity=0.90, scrim=None,
         place=(20, 3, 60), cue='U6 + 3.5', t_appear=137.30, hold_s=10.0, t_gone=150.30,
         trigger='U6 + 3.5（137.30；破云 U6k + 8.2 s）；退场在 U7 150.30 结束', exit='up 0.2°',
         hold_note='§7.4 公式 10.6 s；圣经例外 −0.6 s（前有破云 + 8 s，后有 U7 的全景揭示）',
         treatment='无辉光；巨像 1 在它身后升起（143.80）；预言：§7.4-1 的例外；两行断在 nichts 之后', staging='together',
         segments=[
             seg(['Denn das Schöne ist nichts', 'als des Schrecklichen Anfang'],
                 zh=['因为美无非是', '恐怖的开端'],
                 ja=['美とは、恐ろしいものの', '始まりにほかならない'],
                 en=['For beauty is nothing but', 'the beginning of terror']),
         ]),
    dict(id='P04b_Urlicht', scene='4', bible='§7.5 #3 / §6·4',
         source='Des Knaben Wunderhorn, „Urlicht“ (Mahler, Sym. 2, IV)', source_en='“Urlicht”, from Des Knaben Wunderhorn',
         original=dict(lang='de', font='EBGaramond-Italic'),
         size_main=1.8, size_tr=1.8, color_target='#D8DDE6', opacity=0.90, scrim=None,
         place=(0, -8, 30), cue='U8', t_appear=166.15, hold_s=None, t_gone=171.5,
         trigger='U8 166.15（Ach nein!）逐词出现，与第一遍歌声同步；第 4 幕唯一的字',
         exit='第一遍唱完后 1.5 s 内淡出（≈171.5，在 U8c 171.40 第二遍之前）；第二遍不出字',
         hold_note='与歌声同步（§7.4-1 例外）；Da kam ein Engelein… 不出字，歌照唱（§7.5 #3，E24）',
         line_cues=[dict(line='Ach nein!', cue='U8', t=166.15), dict(line='Ich ließ mich nicht abweisen!', cue='U8b', t=167.90)],
         treatment='耳语，不是字幕卡；无辉光；U8 时裂口最宽处在 +17°，相距 25°', staging='sung: one card, word-synced to the first singing',
         segments=[
             seg(['Ach nein!', 'Ich ließ mich nicht abweisen!'],
                 zh=['啊，不！', '我不肯被拒之门外！'],
                 ja=['いいえ！', 'わたしは引き下がらなかった！'],
                 en=['Ah no!', 'I would not be turned away!'], t='U8 / U8b'),
         ]),
    dict(id='P06_Dream_Dawn', scene='6d', bible='§7.5 #4 / §6·6',
         source='用户梦中得句', source_en='a line received in the dreamer’s dream',
         original=dict(lang='zh', font='SourceHanSerifSC-Regular'),
         size_main=2.4, size_tr=1.8, color_target='#1F2A3A', opacity=1.00, scrim='light',
         place=(-15, -12, 40), cue='F1z', t_appear=345.36, hold_s=9.6, t_gone=357.96,
         trigger='F1z 第二段鸟鸣 345.36（海镜 337.0 落定 + 8.4 s；离海 149 m）', exit='DOWN 0.2°：向下漂进它自己的倒影（→ 357.96，离海 14 m）',
         opacity_note=('不透明度 1.00，不是 §7.2 的 90%（验收第 3 轮 MAJOR 3，圣经法律第 1 条：屏幕目标是法律）。'
                       'Unity 在线性帧缓冲里混合：90% 时 10% 的亮海镜（线性约 0.3–0.6）透过来，深墨 #1F2A3A（luma 41）'
                       '会读成石板灰 #575E69（luma 93）。1.00 时字心正好是 #1F2A3A，与背景无关。'),
         treatment='深墨字 + 亮衬 #E8F1F5 α0.25（以防落在暗处）；暗字写在亮的海镜上方；从晨挪到海镜（晨里不放字）', staging='together',
         segments=[
             seg(['我从天空坠入深海'],
                 ja=['わたしは空から', '深い海へ墜ちた'],
                 en=['I fell from the sky', 'into the deep sea']),
         ]),
    dict(id='P07_HeBo', scene='7b', bible='§7.5 #5 / §6·7b',
         source='屈原《九歌·河伯》', source_en='Qu Yuan, Nine Songs: “The Lord of the River”',
         original=dict(lang='zh', font='SourceHanSerifSC-Regular'),
         size_main=2.2, size_tr=1.8, color_target='#D9E2E7', opacity=0.90, scrim=None,
         place=(10, 6, 15), cue='F5r + 5.1', t_appear=714.0, hold_s=13.5, t_gone=730.5,
         trigger='F5r + 5.1（714.0；大殿立面 ≈706 显出 + 8 s）；在女低音 F6 735.56 之前问出', exit='up 0.2°',
         treatment='无辉光；门右、深渊一侧的暗水上（门在 −7° → −12°，相距 17–22°）；鱼群从前面游过一次（≈720）', staging='together',
         segments=[
             seg(['鱼鳞屋兮龙堂'], ja=['魚鱗の屋、龍の堂'], en=['Houses of fish-scale, halls of dragons,']),
             seg(['紫贝阙兮朱宫'], ja=['紫貝の闕、朱の宮'], en=['purple-shell gates, a vermilion palace —']),
             seg(['灵何为兮水中'], ja=['霊何為れぞ水中にある'], en=['O spirit, why do you dwell in the water?']),
         ]),
    dict(id='P08a_Dream_Dusk', scene='7c', bible='§7.5 #6 / §6·7c',
         source='用户梦中得句', source_en='a line received in the dreamer’s dream',
         original=dict(lang='zh', font='SourceHanSerifSC-Regular'),
         size_main=2.4, size_tr=1.8, color_target='#EADCD6', opacity=0.90, scrim=None,
         place=(-15, -12, 40), cue='F8c + 0.84', t_appear=903.0, hold_s=10.4, t_gone=916.4,
         trigger='F8c + 0.84（903.0；倒置的斯涅尔之窗 897.96 落定 + 5.0 s）', exit='DOWN 0.2°：向下漂进下面那片天里（→ 916.4）',
         scrim_note=('不加暗衬（§7.5 #6）：它写在 7c 的暗水上。圣经说只有落在窗光上时才加 #0E1A2F α0.30；'
                     '倒置的斯涅尔之窗是车下约 97° 的圆，边缘在仰角 −41.5°，字在 −12°，所以这个条件在几何上不会出现。'),
         treatment='亮字写在暗水上：晨那句的照相底片；从第 8 幕挪进 7c；与 #4 同一处', staging='together',
         segments=[
             seg(['自深海坠入另一片天空'],
                 ja=['深い海から', 'もうひとつの空へ墜ちた'],
                 en=['From the deep sea I fell', 'into another sky']),
         ]),
    dict(id='P08b_Zhuangzi_Xiaoyao', scene='8-ii', bible='§7.5 #7 / §6·8（镜像处理表）',
         source='庄子《逍遥游》', source_en='Zhuangzi, “Free and Easy Wandering”',
         original=dict(lang='zh', font='SourceHanSerifSC-Regular'),
         size_main=2.2, size_tr=1.8, color_target='#EADCD6', opacity=0.90, scrim='dark',
         place=(35, 0, 60), cue='≈965.4 + 6.0 / ≈F11b', t_appear=971.4, hold_s=17.6, t_gone=993.0, exit_s=4.0,
         trigger='L1 971.4（天顶散尽 ≈965.4 + 6.0 s）· L3 976.4（≈F11b 合唱的 entschweben）；固定在地平线上，不跟随注视',
         hold_note='两行都保持到 989.0（L1 17.6 s ≥ 公式 9.6 s；L3 12.6 s ≥ 公式 10.4 s），989.0 → 993.0 退场（4 s，与 F12 日线的收缩同步）',
         exit='上下分开：地平线上的物体向上漂、地平线下的向下漂（§7.4-4“庄子的镜像字两向分开”、§6·8“字竖着分开”）',
         treatment='镜像：只镜像原文（镜像字 α0.5、softness 0.3）；L2 不出（E25）；L3 正字在地平线下（低头读）；'
                   '译文不进镜像，放在整列下方的“译文字幕位”，随每一行更换', staging='per segment: 971.4 / 976.4',
         mirror=True, tr_display='caption',
         segments=[
             seg(['天之苍苍，其正色邪？'], ja=['天の蒼蒼たるは', '其れ正色なるか'],
                 en=['The sky, so blue, so blue —', 'is that its true colour?'], t='971.4', upright='above', label='L1'),
             seg(['其视下也，亦若是则已矣'], ja=['其の下を視るや', '亦た是くの若くならんのみ'],
                 en=['Looking down from there,', 'it would be just the same'], t='976.4', upright='below', label='L3',
                 note='upright copy BELOW the horizon, mirror copy above'),
         ]),
    dict(id='P09_Tianwen', scene='9a', bible='§7.5 #8 / §6·9',
         source='屈原《天问》', source_en='Qu Yuan, “Heavenly Questions”',
         original=dict(lang='zh', font='SourceHanSerifSC-Regular'),
         size_main=2.2, size_tr=1.8, color_target='#D9E2E7', opacity=0.90, scrim=None,
         place=(0, 8, 50), cue='第 9 幕 + 8.0（变暗结束）', t_appear=1009.21, hold_s=9.0, t_gone=1019.41,
         trigger='1009.21：8b 变暗结束 = 第 9 幕第 8.0 s；逐字对焦，≈1011.6 就位；天顶最后一颗星同一刻熄灭',
         hold_note='到 F13 1018.21（9.0 s）；§7.4 公式 12.7 s，圣经例外 −3.7 s（夹在蓝时与 F13 之间，永不压缩）',
         exit='F13 那一帧每个汉字的字心点燃一颗星（16 颗），字 1.2 s 内暗下（→ 1019.41）',
         treatment='逐字对焦 0.6 s、120 ms 错开；标点不变星；星留在原处到第 9 幕结束', staging='together, per-character focus',
         segments=[
             seg(['遂古之初，谁传道之？'], ja=['遂古の初め、誰か之を伝へ道ふ'],
                 en=['At the far beginning of things,', 'who was there to tell of it?']),
             seg(['上下未形，何由考之？'], ja=['上下未だ形あらず', '何に由りて之を考ふる'],
                 en=['When above and below had no form,', 'how could it be known?']),
         ]),
    dict(id='P11_Zhuangzi_Butterfly', scene='11', bible='§7.5 #9 / §6·11',
         source='庄子《齐物论》', source_en='Zhuangzi, “On the Equality of Things”',
         original=dict(lang='zh', font='SourceHanSerifSC-Regular'),
         size_main=2.0, size_tr=1.8, color_target='#E0D6C4', opacity=0.80, scrim=None,
         place=(0, 8, 10), cue='第 11 幕 + 28', t_appear=1206.46, hold_s=12.7, t_gone=1222.16,
         trigger='第 11 幕第 28 s（1206.46；白收缩完 + 20 s 的海揭示之后 8 s）', exit='up 0.2°',
         treatment='80%，低对比，小而安静', staging='together',
         segments=[
             seg(['不知周之梦为胡蝶与'], ja=['知らず', '周の夢に胡蝶と為れるか'],
                 en=['I cannot tell —', 'did Zhou dream he was a butterfly,']),
             seg(['胡蝶之梦为周与'], ja=['胡蝶の夢に周と為れるか'],
                 en=['or does a butterfly dream it is Zhou?']),
         ]),
    dict(id='P12a_LiBai_Wake', scene='12', bible='§7.5 #10 / §6·12',
         source='李白《梦游天姥吟留别》', source_en='Li Bai, “Dreaming of Mount Tianmu: A Farewell”',
         original=dict(lang='zh', font='SourceHanSerifSC-Regular'),
         size_main=2.4, size_tr=1.8, color_target='#D9E2E7', opacity=0.90, scrim=None,
         place=(50, -9, 40), cue='第 12 幕 + 16', t_appear=1270.96, hold_s=11.2, t_gone=1285.16,
         trigger='第 12 幕第 16 s（1270.96；白收缩进灯管、站台落定 + 12 s）', exit='up 0.2°',
         treatment='与第 3 幕李白同一处（一开一合）', staging='together',
         segments=[
             seg(['惟觉时之枕席'], ja=['惟だ覚めし時の枕席のみ'], en=['Only the pillow and mat of waking —']),
             seg(['失向来之烟霞'], ja=['向来の煙霞を失ふ'], en=['lost, the mists and rosy clouds of before']),
         ]),
    dict(id='P12b_Keats', scene='12', bible='§7.5 #11 / §6·12',
         source='John Keats, Ode to a Nightingale (1819), last line', source_en='Keats, Ode to a Nightingale',
         original=dict(lang='en', font='EBGaramond-Italic'),
         size_main=1.6, size_tr=1.8, color_target='#D9E2E7', opacity=0.90, scrim=None,
         place=(50, -14, 25), cue='第 12 幕 + 66', t_appear=1320.96, hold_s=10.6, t_gone=1334.56,
         trigger='第 12 幕第 66 s（1320.96；Lichtchen 在萤火虫之间被弄丢 ≈56 s + 10 s）',
         exit='up 0.2°（世界里最后的字，之后永远没有文字）',
         treatment='无辉光', staging='together',
         segments=[
             seg(['Fled is that music:—Do I wake or sleep?'],
                 zh=['那乐声已远去', '我是醒着，还是睡着？'],
                 ja=['あの調べは消えた', 'わたしは醒めているのか', '眠っているのか']),
         ]),
]


# ------------------------------------------------------------------------------------------- v4 (D-30)
V4 = {   # poem id: (size_cjk, size_lat, note)
    'P03_LiBai_Dream':        (2.4, 2.2, None),
    'P04a_Rilke':             (2.2, 2.0, 'D-13：里尔克 2.0° em'),
    'P04b_Urlicht':           (1.8, 1.8, 'D-30a #2：原本就定得小，小是设计（“耳语”）：拉丁 / 德文 1.8° em、CJK 1.8°'),
    'P06_Dream_Dawn':         (2.4, 2.2, None),
    'P07_HeBo':               (2.2, 2.0, None),
    'P08a_Dream_Dusk':        (2.4, 2.2, None),
    'P08b_Zhuangzi_Xiaoyao':  (2.2, 2.0, None),
    'P09_Tianwen':            (2.2, 2.0, '例外（D-30 #4）：汉字 2.2° 给所有人；不是中文的玩家下面另有一行 1.8°'),
    'P11_Zhuangzi_Butterfly': (2.0, 2.0, 'D-30a #2：原本就定得小（“小而安静”）：CJK 2.0°、拉丁 2.0° em'),
    'P12a_LiBai_Wake':        (2.4, 2.2, None),
    'P12b_Keats':             (1.8, 1.6, 'D-30a #2：原本就定得小：拉丁 1.6° em、CJK 1.8°'),
}
for p in POEMS:
    p['size_cjk'], p['size_lat'], note = V4[p['id']]
    if note:
        p['size_note'] = note
    # D-33 (main b14e579): blocks measured against the REAL bus (block_viewcheck.py)
    if p['id'] in ('P06_Dream_Dawn', 'P08a_Dream_Dusk'):
        # #1: the two dream lines rhyme -> still one place: azimuth -2°, TOP edge at -4° (was -15° / -12°: radio, centre
        # post, the ja third line under the windscreen's lower edge). Block bottom >= -14.5°; 6d's downward exit drifts
        # until the bottom would touch -15° and is faded out before that (exit_max_drift_deg)
        p['place'] = (-2, -4, p['place'][2])
        p['anchor_top'] = True
        p['place_note'] = 'D-33 #1：方位 −2°、顶边对齐在 −4°（两句同一处）；块底 ≥ −14.5°，离收音机 ≥ 1°'
        p['bottom_min'] = -14.5
        p['az_range'] = (-22.5, 16.5)
    if p['id'] == 'P07_HeBo':
        # #2: centre azimuth +6.5° (13.5° from the hall gate at -7°), every line <= 19.5° (right edge <= +16.5°),
        # top <= +10° (the block moves down when a language is taller)
        p['place'] = (6.5, p['place'][1], p['place'][2])
        p['top_max'] = 10.0
        p['line_max_deg'] = 19.5
        p['az_range'] = (-22.5, 16.5)
        p['place_note'] = 'D-33 #2：中心方位 +6.5°；每行 ≤ 19.5°；顶 ≤ +10°（高的语言整块往下挪）'
    if p['id'] in ('P03_LiBai_Dream', 'P12a_LiBai_Wake', 'P12b_Keats'):
        # #3: the side-window poems: centre azimuth +61°, elevation unchanged; block left edge >= +48.5° (door stack to
        # +46.9°, door post +40.7…+43.3°, side window from +45.5°)
        p['place'] = (61, p['place'][1], p['place'][2])
        p['az_min'] = 48.5
        p['place_note'] = 'D-33 #3：中心方位 +61°，仰角不变；左沿 ≥ +48.5°'
    if p['id'] == 'P08b_Zhuangzi_Xiaoyao':
        # #4: indigo ink #27304A (bible §6·8, AD 10-07), no dark scrim (#EADCD6 + dark scrim withdrawn)
        p['color_target'] = '#27304A'
        p['scrim'] = None
        p['color_note'] = 'D-33 #4：靛墨 #27304A（圣经 §6·8，AD 10-07），不加暗衬；#EADCD6 + 暗衬作废'
        # a dark ink over a bright sky at 90 % reads 39 codes too light in Unity's linear blend (luma 77 for 48): the same
        # reason as 6d (verify r3 MAJOR 3, law 1) -> the upright lines at 1.00, the mirrors at 0.5 (half of it)
        p['opacity'] = 1.00
        p['opacity_note'] = ('不透明度 1.00（不是 §7.2 的 90%）：靛墨写在亮的暮天上，90% 时 Unity 线性混合读出 luma 77（目标 48，差 39 码），'
                             '和晨句同一个道理（法律第 1 条）。镜像字 0.5')
        # +35° / 0° / 60 m (the key frame, never follows the gaze) crosses the folded door stack (+36.4…+46.9°) of the
        # INTACT bus; in 8-ii the cabin is eroded (bible §4.8). Not in D-33's list: reported, not moved, until the
        # director / the bus say what is left of the door at 971 s
        p['viewcheck_exempt'] = ('由 D-33 #7a 保证：车厢驱动让门组（折门四片、门柱、门口扶杆、门框上半）在 965.4 之前侵蚀掉，'
                                 '车来量（≤ 10%）；对完整的车，这一列压在门叠上')
    if p['id'] == 'P08b_Zhuangzi_Xiaoyao':
        # the ja column (2 + 2 lines, mirrored about the horizon) is 4.8 em from the horizon to L1's centre: at 2.2°
        # L1 would sit at +10.56°, over §7.3's "never above +10°". 2.08° puts it at +9.98°. 0.12° under D-30's 2.2°.
        p['size_by_lang'] = {'ja': 2.08}
        p['size_note'] = ('日文这一首 2.08°（D-30a #1 批准）：日文的镜像列 2 + 2 行，2.2° 时 L1 的中心在 +10.56°，'
                          '超过 §7.3“中心永不高于 +10°”')
    if p['id'] == 'P09_Tianwen':
        p['picture'] = True                  # D-30 #4: the Han characters are the picture; sub-line 1.8° (size_tr)
    if p['id'] == 'P04a_Rilke':
        # D-13 (2026-10-24 05:40): candidate A, centre +5.5° / -8°, 2.0° em; the final centre follows the bus's
        # single-language re-check (pkg/bus Bus/Docs~/D-13_里尔克候选.md)
        p['place'] = (5.5, -8, p['place'][2])
        p['place_note'] = 'D-13 候选 A：中心 +5.5° / −8°（「车」按单语块复核中，最后以 Bus/Docs~/D-13_里尔克候选.md 为准）'


# v4 re-breaks (D-30 #2: a line <= 28° at the v4 size; break at the pause, never inside a word). Text unchanged.
V4_LINES = {
    ('P03_LiBai_Dream', 0, 'en'): ['I would dream my way', 'to Wu and Yue,'],
    ('P04a_Rilke', 0, 'ja'): ['美とは、', '恐ろしいものの', '始まりにほかならない'],   # D-13 (bus re-check, main cae5b7e)
    ('P03_LiBai_Dream', 1, 'ja'): ['一夜飛んで度る', '鏡湖の月'],
    ('P07_HeBo', 0, 'en'): ['Houses of fish-scale,', 'halls of dragons,'],
    ('P07_HeBo', 1, 'en'): ['purple-shell gates,', 'a vermilion palace —'],
    ('P07_HeBo', 2, 'en'): ['O spirit, why do you', 'dwell in the water?'],                   # D-33 #2: <= 19.5°
    ('P07_HeBo', 0, 'ja'): ['魚鱗の屋、龍の堂'],
    ('P07_HeBo', 2, 'ja'): ['霊何為れぞ', '水中にある'],                                       # D-33 #2
    ('P08a_Dream_Dusk', 0, 'ja'): ['深い海から', 'もうひとつの空へ', '墜ちた'],
    ('P08b_Zhuangzi_Xiaoyao', 1, 'ja'): ['其の下を視るや亦た', '是くの若くならんのみ'],
    ('P12a_LiBai_Wake', 0, 'ja'): ['惟だ覚めし時の', '枕席のみ'],
    ('P12a_LiBai_Wake', 0, 'en'): ['Only the pillow and mat', 'of waking —'],
    ('P12a_LiBai_Wake', 1, 'en'): ['lost, the mists', 'and rosy clouds of before'],
}
for (pid, i, key), lines in V4_LINES.items():
    p_ = next(q for q in POEMS if q['id'] == pid)
    old = p_['segments'][i][key]
    assert ''.join(lines).replace(' ', '') == ''.join(old).replace(' ', ''), (pid, i, key)   # same words, new breaks
    p_['segments'][i][key + '_v4'] = lines
# Urlicht is word-synced (line_cues): which cue each displayed line belongs to, per shown language
for p_ in POEMS:
    if p_.get('line_cues'):
        p_['line_cues_by_shown'] = {}
        for key in ['main'] + [l for l in ('zh', 'zht', 'ja', 'en') if any(l in s_ for s_ in p_['segments'])]:
            idx = []
            for s_ in p_['segments']:
                base = s_.get(key, [])
                v4 = s_.get(key + '_v4', base)
                # a re-broken line inherits the cue of the line it came from (Urlicht ja: 'わたしは' + '引き下がらなかった！' = U8b)
                k = 0
                acc = ''
                for ln in v4:
                    idx.append(k)
                    acc += ln
                    if k < len(base) and acc.replace(' ', '') == base[k].replace(' ', ''):
                        k += 1
                        acc = ''
            p_['line_cues_by_shown'][key] = [dict(line=ln, cue=p_['line_cues'][j]['cue'], t=p_['line_cues'][j]['t'])
                                             for ln, j in zip([l for s_ in p_['segments'] for l in s_.get(key + '_v4', s_.get(key, []))], idx)]


# Traditional Chinese (zh-HK players, D-31 #1): OpenCC s2tw of the original (zh poems) or of the zh translation,
# then checked by hand for the classical texts: 李白 枕席 (s2tw gives 枕蓆; the received text has 席). Same line breaks.
ZHT = {
    'P03_LiBai_Dream': [['我欲因之夢吳越'], ['一夜飛度鏡湖月']],
    'P04a_Rilke': [['因為美無非是', '恐怖的開端']],
    'P04b_Urlicht': [['啊，不！', '我不肯被拒之門外！']],
    'P06_Dream_Dawn': [['我從天空墜入深海']],
    'P07_HeBo': [['魚鱗屋兮龍堂'], ['紫貝闕兮朱宮'], ['靈何為兮水中']],
    'P08a_Dream_Dusk': [['自深海墜入另一片天空']],
    'P08b_Zhuangzi_Xiaoyao': [['天之蒼蒼，其正色邪？'], ['其視下也，亦若是則已矣']],
    'P09_Tianwen': [['遂古之初，誰傳道之？'], ['上下未形，何由考之？']],
    'P11_Zhuangzi_Butterfly': [['不知周之夢為胡蝶與'], ['胡蝶之夢為周與']],
    'P12a_LiBai_Wake': [['惟覺時之枕席'], ['失向來之煙霞']],
    'P12b_Keats': [['那樂聲已遠去', '我是醒著，還是睡著？']],
}
for p_ in POEMS:
    for s_, lines in zip(p_['segments'], ZHT[p_['id']]):
        src = s_['main'] if p_['original']['lang'] == 'zh' else s_['zh']
        assert len(lines) == len(src) and all(len(a) == len(b) for a, b in zip(lines, src)), p_['id']
        s_['zht'] = lines
    if p_['id'] == 'P04a_Rilke':
        # D-13 final (main cae5b7e, the bus's single-language check): block TOP-aligned, TMP pivot top-centre, at
        # azimuth +5.5°, elevation -2.5° (= the top edge of every language's block), 60 m
        p_['place'] = (5.5, -2.5, p_['place'][2])
        p_['anchor_top'] = True
        # D-13 supplement (main a5d7470): the ja block (3 lines, widest 24.0° with the +0.10 em tracking) moves 1° left,
        # centre +4.5°, so its right edge is +16.5° (4° from the A pillar); line breaks, size and tracking unchanged
        p_['az_by_lang'] = {'ja': 4.5}
        p_['place_note'] = 'D-13 定稿（main cae5b7e）：单语块顶边对齐，TMP 轴心在上中，方位 +5.5°、仰角 −2.5°（块的顶边）、60 m'


def shown_strings(p):
    """v4: (font key, line, ident) of every line any player can see of poem p (charsets / subsets; no layout needed)."""
    out = []
    for pl in ('zh', 'zht', 'ja', 'en', 'de'):
        k = 'main' if p.get('picture') else shown_lang(p, pl)
        fk = p['original']['font'] if k == 'main' else TR_FONT[k]
        for s_ in p['segments']:
            for ln in s_.get(k + '_v4', s_.get(k, [])):
                out.append((fk, ln, p['id'] + ('' if k == 'main' else '/' + k)))
        sub = translation_for(p, pl)
        if sub:
            for s_ in p['segments']:
                for ln in s_.get(sub, []):
                    out.append((SUB_FONT[sub], ln, p['id'] + '/' + sub + '(sub)'))
    return out


def size_for(p, font_key, lang=None):
    o = p.get('size_by_lang', {}).get(lang)
    if o:
        return o
    return p['size_cjk'] if FONTS[font_key]['cjk'] else p['size_lat']


def hold_formula(p, segs=None):
    """§7.4-3: 3 s + 0.3 s per CJK character (or 0.35 s per Latin word) + 2 s, x 1.3 with a translation; [6, 14].
    The mirrored Zhuangzi passage is timed per line (bible §7.5 #7: L1 9.6 s, L3 10.4 s)."""
    if segs is None and p.get('mirror'):
        return [hold_formula(p, [s_])[0] for s_ in p['segments']], [hold_formula(p, [s_])[1] for s_ in p['segments']]
    segs = p['segments'] if segs is None else segs
    main = ''.join(t for s_ in segs for t in s_['main'])
    if p['original']['lang'] in ('zh', 'ja'):
        n = sum(1 for ch in main if '㐀' <= ch <= '鿿')
        base = 3 + 0.3 * n + 2
    else:
        words = ' '.join(t for s_ in segs for t in s_['main']).replace(':—', ' ').replace('—', ' ').split()
        n = len(words)
        base = 3 + 0.35 * n + 2
    return round(min(14.0, max(6.0, base * 1.3)), 1), n


for p in POEMS:
    p['hold_formula_s'], p['hold_formula_count'] = hold_formula(p)
    if p.get('hold_s') is not None:
        p['t_exit'] = round(p['t_appear'] + p['hold_s'], 2)

# fill in translations dict per poem (fonts per language)
for p in POEMS:
    langs = [l for l in ('zh', 'zht', 'ja', 'en') if any(l in s for s in p['segments'])]
    p['translations'] = {l: {'font': (SUB_FONT if p.get('picture') else TR_FONT)[l]} for l in langs}

# ------------------------------------------------------------------------------------------ credits
# bible §5.5 / §7.6 + lens_story §6 (full text), broken into lines that fit a 900 mm sheet at the 24 mm minimum.  Typography: title Barlow SemiBold (+0.3 em); 蓝白 + epigraph
# Source Han Serif SC Medium; roles EB Garamond Italic; names EB Garamond Regular or Source Han Serif SC Regular.
# NOTE: the Sign kit (deliver2/Sign) already bakes the sheet into Notice_Credits_*.png. These entries exist so
# a TMP version (e.g. to type the placeholders in the editor) never hits a missing glyph.
CREDITS = {
    'title':        {'font': 'BarlowSemiCondensed-SemiBold', 'text': 'LANBAI', 'tracking_em': 0.30, 'cap_mm': '≥ 50'},
    'title_cjk':    {'font': 'SourceHanSerifSC-Medium', 'text': '蓝白'},
    'epigraph':     {'font': 'SourceHanSerifSC-Medium', 'lines': ['我从天空坠入深海，', '自深海坠入另一片天空。'], 'size_mm': 30},
    'attribution':  {'font': 'SourceHanSerifSC-Medium', 'text': '——梦中得句',
                     'note': 'TMP：这一行字距设 0。子集字体里 U+2014 已指向全宽、居中（汉字中线）的横线字形，两条首尾相接成一条 2 em 的破折号'},
    'rows': [
        {'role': 'A dream by', 'names': [{'font': 'EBGaramond-Regular', 'text': '〔the dreamer’s name, as they wish〕', 'placeholder': True}]},
        {'role': 'Music', 'names': [
            {'font': 'EBGaramond-Regular', 'text': 'Gustav Mahler'},
            {'font': 'EBGaramond-Regular', 'text': 'Symphony No. 2, “Resurrection”'},
            {'font': 'EBGaramond-Regular', 'text': 'IV. Urlicht'},
            {'font': 'EBGaramond-Regular', 'text': 'Kathleen Ferrier · Concertgebouworkest', 'verify': True},
            {'font': 'EBGaramond-Regular', 'text': 'Otto Klemperer · 1951', 'verify': True},
            {'font': 'EBGaramond-Regular', 'text': 'V. (from Der große Appell)'},
            {'font': 'EBGaramond-Regular', 'text': 'Emilia Cundari · Maureen Forrester', 'verify': True},
            {'font': 'EBGaramond-Regular', 'text': 'Westminster Choir · New York Philharmonic', 'verify': True},
            {'font': 'EBGaramond-Regular', 'text': 'Bruno Walter · 1958', 'verify': True},
        ]},
        {'role': 'Words', 'names': [
            {'font': 'SourceHanSerifSC-Regular', 'text': '李白'}, {'font': 'SourceHanSerifSC-Regular', 'text': '《梦游天姥吟留别》'},
            {'font': 'EBGaramond-Regular', 'text': 'Rainer Maria Rilke'}, {'font': 'EBGaramond-Italic', 'text': 'Duineser Elegien, I'},
            {'font': 'EBGaramond-Regular', 'text': 'Des Knaben Wunderhorn'}, {'font': 'EBGaramond-Italic', 'text': 'Urlicht'},
            {'font': 'SourceHanSerifSC-Regular', 'text': '屈原'}, {'font': 'SourceHanSerifSC-Regular', 'text': '《九歌·河伯》《天问》'},
            {'font': 'SourceHanSerifSC-Regular', 'text': '庄子'}, {'font': 'SourceHanSerifSC-Regular', 'text': '《逍遥游》《齐物论》'},
            {'font': 'EBGaramond-Regular', 'text': 'John Keats'}, {'font': 'EBGaramond-Italic', 'text': 'Ode to a Nightingale'},
        ]},
        {'role': 'Trees', 'names': [{'font': 'EBGaramond-Regular', 'text': '〔the user’s credit for the Linluo trees〕', 'placeholder': True}]},
        {'role': 'Built by', 'names': [{'font': 'EBGaramond-Regular', 'text': '〔names, as the dreamer wishes〕', 'placeholder': True}]},
        {'role': 'Skies', 'names': [{'font': 'EBGaramond-Regular', 'text': 'Poly Haven (CC0) · NASA SVS Deep Star Maps'},
                                    {'font': 'EBGaramond-Regular', 'text': 'Milky Way: ESA/Gaia/DPAC (CC BY-SA 3.0 IGO)'}]},   # D-11
        {'role': 'Photos', 'names': [{'font': 'EBGaramond-Regular', 'text': '〔PAZ photo authors and licences, as the bus README lists them〕', 'placeholder': True}]},
        {'role': 'Type', 'names': [{'font': 'EBGaramond-Regular', 'text': 'Source Han Serif · Source Han Sans'},
                                   {'font': 'EBGaramond-Regular', 'text': 'EB Garamond · Barlow · IM FELL English'},
                                   {'font': 'EBGaramond-Regular', 'text': '(SIL Open Font License)'}]},
    ],
    'role_font': 'EBGaramond-Italic',
}

# The Sign kit's baked sheet (deliver2/Sign/Tools~/src/credits.json, 2026-09-30) uses a condensed wording.
# Copied here only so the charsets cover it as well.
CREDITS_SIGNKIT_VARIANT = {
    'EBGaramond-Italic': ['A dream by', 'Music', 'IV. Urlicht', 'V. Finale', 'Words', 'Trees', 'Built by'],
    'EBGaramond-Regular': ['Gustav Mahler', 'Symphony No. 2', '“Resurrection”',
                           'Kathleen Ferrier · Otto Klemperer · 1951', 'Bruno Walter · New York Philharmonic · 1958',
                           'Rainer Maria Rilke', 'Des Knaben Wunderhorn', 'John Keats'],
    'SourceHanSerifSC-Regular': ['李白　屈原　庄子', '〔　　　　〕'],
    'SourceHanSerifSC-Medium': ['蓝白', '我从天空坠入深海，', '自深海坠入另一片天空。', '—— 梦中得句'],
    'BarlowSemiCondensed-SemiBold': ['LANBAI'],
}

# ------------------------------------------------------------------------------------ Coleridge slip
# bible §5.5: torn half-page of the 1816 Christabel volume, IM FELL English, 7 mm; ends "The pool becomes a mirror."
# (flag: verify against a scan of the 1816 edition — bible §9-16).
COLERIDGE = {
    'head': {'font': 'IMFellEnglishSC', 'text': 'OF THE FRAGMENT OF KUBLA KHAN.'},
    'prose': {'font': 'IMFellEnglish-Roman', 'text': '…all the rest had passed away like the images on the surface of a '
              'stream into which a stone has been cast, but, alas! without the after restoration of the latter!'},
    'verse': {'font': 'IMFellEnglish-Roman', 'lines': [
        'Then all the charm',
        'Is broken—all that phantom-world so fair',
        'Vanishes, and a thousand circlets spread,',
        'And each mis-shape the other. Stay awhile,',
        'Poor youth! who scarcely dar’st lift up thine eyes—',
        'The stream will soon renew its smoothness, soon',
        'The visions will return! And lo, he stays,',
        'And soon the fragments dim of lovely forms',
        'Come trembling back, unite, and now once more',
        'The pool becomes a mirror.',
    ]},
}

# ------------------------------------------------------------------------------ destination roll
DESTINATION_ROLL = {'font': 'SourceHanSansSC-Heavy', 'text': '蓝白', 'bible': '§4.7',
                    'note': '贴图（镂空透光白字，从车内看是镜像反字；第 11 幕空白卷帘）。站牌套件 deliver2/Sign 已做好，不走 TMP。'}

# ------------------------------------------------------------------------------------------- UI
# bible §1.9: "公告板上也有手动开关" (auto-lite).  The bible gives it no label, and §6·12 bans UI prompts and any word
# after Keats. So the switch carries NO TEXT: a small enamel toggle on the case, a warm-white pilot dot beside it
# when on (art-team decision, v2 of this kit; the v1 proposal of a "LITE" plate is withdrawn). No UI strings exist.
# D-31 (main 880a0f2): the notice board at the stop gets (1) the language switch 中 / 日 / EN (only for oneself; default
# = client language) and (4) the departure notice in the player's own language, before the bus leaves. {0} = seconds
# (digits are in every charset). Nothing after departure (§6·12: no UI prompt at the end, no word after Keats).
UI_LANG = {'zh': 'SourceHanSerifSC-Regular', 'zht': 'SourceHanSerifTW-Regular', 'ja': 'SourceHanSerifJP-Regular', 'en': 'EBGaramond-Regular'}
UI = [
    dict(id='UI/lang/zh', lang='zh', font='SourceHanSerifSC-Regular', text='中', note='语言开关：中文（客户端 zh-HK 的人按它仍看繁体）'),
    dict(id='UI/lang/ja', lang='ja', font='SourceHanSerifJP-Regular', text='日', note='语言开关：日本語'),
    dict(id='UI/lang/en', lang='en', font='EBGaramond-Regular', text='EN', note='语言开关：English（其余语言）'),
    dict(id='UI/depart/zh/1', lang='zh', font=UI_LANG['zh'], text='车将在 {0} 秒后开出'),
    dict(id='UI/depart/zh/2', lang='zh', font=UI_LANG['zh'], text='之后上车的人会从路上加入'),
    dict(id='UI/depart/zht/1', lang='zht', font=UI_LANG['zht'], text='車將在 {0} 秒後開出'),
    dict(id='UI/depart/zht/2', lang='zht', font=UI_LANG['zht'], text='之後上車的人會從路上加入'),
    dict(id='UI/depart/ja/1', lang='ja', font=UI_LANG['ja'], text='バスはあと {0} 秒で発車します'),
    dict(id='UI/depart/ja/2', lang='ja', font=UI_LANG['ja'], text='そのあとに乗る人は、道の途中から合流します'),
    dict(id='UI/depart/en/1', lang='en', font=UI_LANG['en'], text='The bus leaves in {0} seconds'),
    dict(id='UI/depart/en/2', lang='en', font=UI_LANG['en'], text='Anyone who boards later joins from the road'),
] + [dict(id='UI/digits/' + k, lang=k, font=f, text='0123456789') for k, f in UI_LANG.items()]
UI_NOTE = ('D-31：公告板上有两样字——语言开关「中 / 日 / EN」（只对本人生效，默认按客户端语言）和发车提示'
           '（发车前，用玩家自己的语言；{0} 换成秒数）。发车以后世界里没有任何 UI 字（§6·12）。§1.9 的手动 auto-lite '
           '开关仍是无字的搪瓷拨钮。请日语母语者过目两句日文。')

# Characters a Latin atlas should carry anyway (names typed later: 'Zoë', 'O’Neill', numbers …).
ASCII = ''.join(chr(c) for c in range(0x20, 0x7F))
