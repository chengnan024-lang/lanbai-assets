#!/bin/bash
# Re-download every original font + licence of the Lanbai Fonts kit into ../Originals~ and ../Licenses.
# Sources: Adobe's release branches (region-specific SubsetOTF) and the google/fonts repo (all SIL OFL 1.1).
set -e
H=$(cd "$(dirname "$0")" && pwd); O="$H/../Originals~"; Lc="$H/../Licenses"; mkdir -p "$O" "$Lc"
R=https://raw.githubusercontent.com
g(){ curl -sSfL --retry 3 -o "$2" "$1" && echo "ok $(basename "$2")"; }
g $R/adobe-fonts/source-han-serif/release/SubsetOTF/CN/SourceHanSerifCN-Regular.otf "$O/SourceHanSerifCN-Regular.otf"
g $R/adobe-fonts/source-han-serif/release/SubsetOTF/CN/SourceHanSerifCN-Medium.otf  "$O/SourceHanSerifCN-Medium.otf"
g $R/adobe-fonts/source-han-serif/release/SubsetOTF/TW/SourceHanSerifTW-Regular.otf "$O/SourceHanSerifTW-Regular.otf"   # v4: Traditional (zh-HK players, D-31)
g $R/adobe-fonts/source-han-serif/release/SubsetOTF/JP/SourceHanSerifJP-Regular.otf "$O/SourceHanSerifJP-Regular.otf"
g $R/adobe-fonts/source-han-serif/release/SubsetOTF/JP/SourceHanSerifJP-Medium.otf  "$O/SourceHanSerifJP-Medium.otf"
g $R/adobe-fonts/source-han-sans/release/SubsetOTF/CN/SourceHanSansCN-Heavy.otf     "$O/SourceHanSansCN-Heavy.otf"
g "$R/google/fonts/main/ofl/ebgaramond/EBGaramond%5Bwght%5D.ttf"                "$O/EBGaramond[wght].ttf"
g "$R/google/fonts/main/ofl/ebgaramond/EBGaramond-Italic%5Bwght%5D.ttf"         "$O/EBGaramond-Italic[wght].ttf"
g $R/google/fonts/main/ofl/barlowsemicondensed/BarlowSemiCondensed-SemiBold.ttf "$O/BarlowSemiCondensed-SemiBold.ttf"
g $R/google/fonts/main/ofl/imfellenglish/IMFeENrm28P.ttf   "$O/IMFeENrm28P.ttf"
g $R/google/fonts/main/ofl/imfellenglish/IMFeENit28P.ttf   "$O/IMFeENit28P.ttf"
g $R/google/fonts/main/ofl/imfellenglishsc/IMFeENsc28P.ttf "$O/IMFeENsc28P.ttf"
g $R/adobe-fonts/source-han-serif/release/LICENSE.txt "$Lc/LICENSE_SourceHanSerif.txt"
g $R/adobe-fonts/source-han-sans/release/LICENSE.txt  "$Lc/LICENSE_SourceHanSans.txt"
g $R/google/fonts/main/ofl/ebgaramond/OFL.txt          "$Lc/OFL_EBGaramond.txt"
g $R/google/fonts/main/ofl/barlowsemicondensed/OFL.txt "$Lc/OFL_BarlowSemiCondensed.txt"
g $R/google/fonts/main/ofl/imfellenglish/OFL.txt       "$Lc/OFL_IMFellEnglish.txt"
g $R/google/fonts/main/ofl/imfellenglishsc/OFL.txt     "$Lc/OFL_IMFellEnglishSC.txt"
echo "done; now: python3 build_fonts.py && python3 make_proofs.py"
