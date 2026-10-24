<#
蓝白 · 仓库 → Unity 工程 同步脚本（D-40a #5）· 总工程师
  只同步 HANDOFF_LOG 当前那一条点名的文件夹 / 文件：仓库里的 X/... → 工程的 Assets/Lanbai/X/...
  默认只列出要做什么（新增 / 覆盖 / 删除），不改任何东西；加 -Apply 才动手。
  动手之前：要覆盖或删除的文件先打包进 <工程>\LanbaiSyncBackup\<时间>.zip。
  上次同步时每个文件的哈希记在 Assets\Lanbai\.lanbai_sync.json；工程里的文件在那之后被本地改过的，不覆盖、不删，除非加 -Force。
  只删上次由本脚本拷进去、现在仓库里没有了的文件；工程里本来就有的（搭建脚本生成的、本地自己加的）一概不动。.meta 不碰（删文件时连它的 .meta 一起删）。

用法（PowerShell 5.1 或 7）：
  powershell -ExecutionPolicy Bypass -File lanbai_sync.ps1 -Project "D:\Unity\Lanbai"                 # 只列出（看当前那一条）
  powershell -ExecutionPolicy Bypass -File lanbai_sync.ps1 -Project "D:\Unity\Lanbai" -Apply          # 照列出的做
  -Repo <路径>        仓库，默认 E:\IDMdownload\VRCC\lanbai-assets
  -Entry <n>          HANDOFF_LOG 的第 n 条（1 = 最上面、最新的，默认）
  -EntryMatch <字>    标题里含这几个字的那一条（比 -Entry 优先）
  -Paths a/,b/c.json  不看 HANDOFF_LOG，直接指定（只在总导演 / 总工程师明说时用）
  -AcceptGuess        这一条没有“同步：”行、路径是从反引号里猜的时候，确认按猜的做
  -Force              本地改过的文件也覆盖 / 删除（照样先进备份）
退出码：0 完成（或只列出）；1 没有可同步的；2 有本地改过的文件被拒绝（什么都没改）；3 脚本出错。
#>
[CmdletBinding()]
param(
    [string]$Repo = 'E:\IDMdownload\VRCC\lanbai-assets',
    [Parameter(Mandatory = $true)][string]$Project,
    [int]$Entry = 1,
    [string]$EntryMatch = '',
    [string[]]$Paths = @(),
    [switch]$Apply,
    [switch]$Force,
    [switch]$AcceptGuess
)

$ErrorActionPreference = 'Stop'
$ToolVersion = '1.0.0'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }
$Utf8NoBom = New-Object Text.UTF8Encoding $false

# 永远不同步的：顶层的这些、任何一层叫这些名字的文件夹、这些扩展名（.py 会被 Unity 当文本导入；Source/、Renders/ 是云端的生成脚本和渲染图）
$SkipTop = @('FromLocal', 'Art', '.git', '.github', '.claude')
$SkipDirs = @('Source', 'Renders', '__pycache__', '.git')
$SkipExt = @('.py', '.pyc', '.blend', '.blend1', '.ps1', '.sh')
$LocalModified = 'LOCAL_MODIFIED'

function Say([string]$s) { Write-Host $s }
function Norm([string]$p) { return ($p -replace '\\', '/').Trim('/') }
function Sha([string]$file) { return (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() }
function GitOut([string]$dir, [string[]]$gitArgs) {
    try {
        $o = & git -C $dir @gitArgs 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        return (($o | Out-String).Trim())
    } catch { return $null }
}

function Skip([string]$rel) {
    $parts = (Norm $rel).Split('/')
    if ($parts.Count -eq 1) { return $true }                    # 仓库根上的单个文件（PLAN、HANDOFF_LOG……）不进工程
    if ($SkipTop -contains $parts[0]) { return $true }
    for ($i = 0; $i -lt $parts.Count - 1; $i++) { if ($SkipDirs -contains $parts[$i]) { return $true } }
    $ext = [IO.Path]::GetExtension($rel).ToLowerInvariant()
    if ($SkipExt -contains $ext) { return $true }
    return $false
}

try {
    $Repo = (Resolve-Path -LiteralPath $Repo).Path
    $Project = (Resolve-Path -LiteralPath $Project).Path
    if (-not (Test-Path -LiteralPath (Join-Path $Project 'Assets'))) { throw "不是 Unity 工程（没有 Assets 文件夹）：$Project" }
    $Lanbai = Join-Path (Join-Path $Project 'Assets') 'Lanbai'
    $RecordPath = Join-Path $Lanbai '.lanbai_sync.json'
    $Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

    # ── 1. 这次同步哪些路径 ─────────────────────────────────────
    $mode = 'entry'
    $entryTitle = ''
    $sel = New-Object System.Collections.Generic.List[string]
    $excl = New-Object System.Collections.Generic.List[string]
    if ($Paths.Count -gt 0) {
        $mode = 'paths'
        foreach ($p in $Paths) { foreach ($q in ($p -split ',')) { if ($q.Trim()) { $sel.Add((Norm $q.Trim())) } } }
        $entryTitle = '（-Paths 指定）'
    } else {
        $log = Join-Path $Repo 'HANDOFF_LOG.md'
        if (-not (Test-Path -LiteralPath $log)) { throw "仓库里没有 HANDOFF_LOG.md：$Repo" }
        $lines = [IO.File]::ReadAllLines($log, [Text.Encoding]::UTF8)
        $entries = @()
        $cur = $null
        foreach ($l in $lines) {
            if ($l.StartsWith('## ')) { $cur = @{ title = $l.Substring(3).Trim(); body = New-Object System.Collections.Generic.List[string] }; $entries += $cur; continue }
            if ($cur -ne $null) { $cur.body.Add($l) }
        }
        if ($entries.Count -eq 0) { throw 'HANDOFF_LOG.md 里没有 “## ” 开头的条目' }
        $pick = $null
        if ($EntryMatch) { foreach ($e in $entries) { if ($e.title.Contains($EntryMatch)) { $pick = $e; break } } ; if ($pick -eq $null) { throw "没有标题含「$EntryMatch」的条目" } }
        else { if ($Entry -lt 1 -or $Entry -gt $entries.Count) { throw "没有第 $Entry 条（一共 $($entries.Count) 条）" }; $pick = $entries[$Entry - 1] }
        $entryTitle = $pick.title
        $rx = [regex]'`([^`]+)`'
        $explicit = $false
        foreach ($l in $pick.body) {
            $t = $l.Trim().TrimStart('-', '*', ' ')
            if ($t -match '^(\*\*)?不同步[:：]') { foreach ($m in $rx.Matches($l)) { $excl.Add((Norm $m.Groups[1].Value)) }; continue }
            if ($t -match '^(\*\*)?同步[:：]') { $explicit = $true; foreach ($m in $rx.Matches($l)) { $sel.Add((Norm $m.Groups[1].Value)) } }
        }
        if (-not $explicit) {
            # 没有“同步：”行：从反引号里猜（只认仓库里真有的路径；“不要拷 / 别拷 / 先别导入”那几行里的当成排除）
            $mode = 'guess'
            $negRx = [regex]'不要拷|别拷|不拷|不同步|别导入|先别导入|不要导入|不用拷'
            foreach ($l in $pick.body) {
                # 一行里“不要拷”后面的路径算排除，前面的照样算要拷（“拷 `Gate/`，不要拷 `Gate/Source/`”）
                $nm = $negRx.Match($l)
                $negAt = $(if ($nm.Success) { $nm.Index } else { [int]::MaxValue })
                foreach ($m in $rx.Matches($l)) {
                    $neg = $m.Index -gt $negAt
                    $tok = Norm $m.Groups[1].Value
                    if ($tok -notmatch '^[A-Za-z0-9_][A-Za-z0-9_~.\-/]*$') { continue }
                    $full = Join-Path $Repo $tok
                    if (-not (Test-Path -LiteralPath $full)) { continue }
                    if ((Norm $tok).Split('/').Count -eq 1 -and -not (Test-Path -LiteralPath $full -PathType Container)) { continue }
                    if ($neg) { $excl.Add($tok) } else { $sel.Add($tok) }
                }
            }
        }
    }
    $sel = @($sel | Select-Object -Unique)
    $excl = @($excl | Select-Object -Unique)

    Say "蓝白同步 $ToolVersion"
    Say "  仓库 $Repo"
    Say "  工程 $Project"
    Say "  条目「$entryTitle」（$(if ($mode -eq 'guess') { '没有“同步：”行，路径是猜的' } elseif ($mode -eq 'paths') { '-Paths 指定' } else { '按“同步：”行' })）"
    Say "  同步：$(if ($sel.Count) { $sel -join '  ' } else { '（没有）' })"
    if ($excl.Count) { Say "  不同步：$($excl -join '  ')" }
    if ($sel.Count -eq 0) { Say '没有要同步的路径。'; exit 1 }

    # ── 2. 仓库的状态 ───────────────────────────────────────────
    $commit = GitOut $Repo @('rev-parse', 'HEAD')
    $branch = GitOut $Repo @('rev-parse', '--abbrev-ref', 'HEAD')
    $dirty = GitOut $Repo @('status', '--porcelain')
    Say "  仓库提交 $(if ($commit) { $commit } else { '（读不到：没装 git 或不是 git 仓库）' })  分支 $branch$(if ($dirty) { '  ⚠ 仓库里有没提交的改动' } else { '' })"
    if ($branch -and $branch -ne 'main') { Say "  ⚠ 仓库不在 main 上（$branch）：本地测试应该用 main" }

    # ── 3. 上次的记录 ───────────────────────────────────────────
    $rec = @{}
    $recRaw = $null
    if (Test-Path -LiteralPath $RecordPath) {
        $recRaw = [IO.File]::ReadAllText($RecordPath, [Text.Encoding]::UTF8)
        $j = $recRaw | ConvertFrom-Json
        if ($j.files) { foreach ($p in $j.files.PSObject.Properties) { $rec[$p.Name] = @{ sha256 = $p.Value.sha256; repo = $p.Value.repo; synced_at = $p.Value.synced_at } } }
    }

    # ── 4. 逐个文件比 ───────────────────────────────────────────
    $plan = New-Object System.Collections.Generic.List[object]
    $repoFiles = @{}
    foreach ($s in $sel) {
        if (Skip ($s + '/x')) { if ((Norm $s).Split('/')[0] -in $SkipTop) { Say "  跳过 $s（这个文件夹从不进工程）"; continue } }
        $full = Join-Path $Repo $s
        if (-not (Test-Path -LiteralPath $full)) { Say "  ⚠ 仓库里没有 $s，跳过"; continue }
        if (Test-Path -LiteralPath $full -PathType Container) { $files = Get-ChildItem -LiteralPath $full -Recurse -File -Force }
        else { $files = @(Get-Item -LiteralPath $full) }
        foreach ($f in $files) {
            $rel = Norm ($f.FullName.Substring($Repo.Length))
            if (Skip $rel) { continue }
            $ex = $false
            foreach ($x in $excl) { if ($rel -eq $x -or $rel.StartsWith($x.TrimEnd('/') + '/')) { $ex = $true; break } }
            if ($ex) { continue }
            $repoFiles[$rel] = $f.FullName
        }
    }
    foreach ($rel in ($repoFiles.Keys | Sort-Object)) {
        $key = 'Assets/Lanbai/' + $rel
        $dst = Join-Path $Lanbai ($rel -replace '/', [IO.Path]::DirectorySeparatorChar)
        $src = $repoFiles[$rel]
        $hs = Sha $src
        if (-not (Test-Path -LiteralPath $dst)) { $plan.Add(@{ op = 'ADD'; key = $key; src = $src; dst = $dst; sha = $hs; repo = $rel }); continue }
        $hd = Sha $dst
        if ($hd -eq $hs) { $plan.Add(@{ op = 'SAME'; key = $key; src = $src; dst = $dst; sha = $hs; repo = $rel }); continue }
        $r = $rec[$key]
        if ($r -ne $null -and $r.sha256 -eq $hd) { $plan.Add(@{ op = 'OVERWRITE'; key = $key; src = $src; dst = $dst; sha = $hs; repo = $rel }) }
        else { $plan.Add(@{ op = $LocalModified; key = $key; src = $src; dst = $dst; sha = $hs; repo = $rel; why = $(if ($r -eq $null) { '没有同步记录，和仓库不一样' } else { '上次同步以后在本地改过' }) }) }
    }
    # 删除：上次由本脚本拷进去、在这次同步的路径下、现在仓库里没有了（或现在被排除）的文件
    foreach ($key in @($rec.Keys)) {
        $rel = $key.Substring('Assets/Lanbai/'.Length)
        $under = $false
        foreach ($s in $sel) { if ($rel -eq $s -or $rel.StartsWith($s.TrimEnd('/') + '/')) { $under = $true; break } }
        if (-not $under -or $repoFiles.ContainsKey($rel)) { continue }
        $dst = Join-Path $Lanbai ($rel -replace '/', [IO.Path]::DirectorySeparatorChar)
        if (-not (Test-Path -LiteralPath $dst)) { $plan.Add(@{ op = 'FORGET'; key = $key; dst = $dst }); continue }
        $hd = Sha $dst
        if ($hd -eq $rec[$key].sha256) { $plan.Add(@{ op = 'DELETE'; key = $key; dst = $dst }) }
        else { $plan.Add(@{ op = $LocalModified + '_DELETE'; key = $key; dst = $dst; why = '仓库里没有了，但本地改过' }) }
    }
    # 工程里多出来的（不是本脚本拷的）：只数一下，不动
    $extra = 0
    foreach ($s in $sel) {
        $d = Join-Path $Lanbai ($s -replace '/', [IO.Path]::DirectorySeparatorChar)
        if (Test-Path -LiteralPath $d -PathType Container) {
            foreach ($f in (Get-ChildItem -LiteralPath $d -Recurse -File -Force)) {
                if ($f.Name.EndsWith('.meta')) { continue }
                $k = 'Assets/Lanbai/' + (Norm ($f.FullName.Substring($Lanbai.Length)))
                $r2 = $k.Substring('Assets/Lanbai/'.Length)
                if (-not $repoFiles.ContainsKey($r2) -and -not $rec.ContainsKey($k)) { $extra++ }
            }
        }
    }

    $count = @{}
    foreach ($p in $plan) { $count[$p.op] = 1 + [int]$count[$p.op] }
    Say ''
    Say "计划：新增 $([int]$count['ADD'])，覆盖 $([int]$count['OVERWRITE'])，删除 $([int]$count['DELETE'])，一样的 $([int]$count['SAME'])，本地改过的 $([int]$count[$LocalModified] + [int]$count[$LocalModified + '_DELETE'])；工程里多出来的 $extra 个不动"
    foreach ($op in @('ADD', 'OVERWRITE', 'DELETE', $LocalModified, ($LocalModified + '_DELETE'))) {
        foreach ($p in ($plan | Where-Object { $_.op -eq $op })) {
            $tag = @{ 'ADD' = '  + 新增  '; 'OVERWRITE' = '  ~ 覆盖  '; 'DELETE' = '  - 删除  '
                      $LocalModified = $(if ($Force) { '  ! 本地改过，-Force 照样覆盖 ' } else { '  ! 本地改过，不覆盖 ' })
                      ($LocalModified + '_DELETE') = $(if ($Force) { '  ! 本地改过，-Force 照样删 ' } else { '  ! 本地改过，不删 ' }) }[$op]
            Say ("$tag$($p.key)" + $(if ($p.why) { "（$($p.why)）" } else { '' }))
        }
    }

    # 计划另存一份（工程的 LanbaiReports/sync/，不在 Assets 里）
    $repDir = Join-Path (Join-Path $Project 'LanbaiReports') 'sync'
    New-Item -ItemType Directory -Force -Path $repDir | Out-Null
    $planOut = @{ tool_version = $ToolVersion; at = (Get-Date -Format 'o'); applied = [bool]$Apply; force = [bool]$Force; mode = $mode; entry = $entryTitle; repo_commit = $commit; paths = $sel; excluded = $excl;
                  plan = @($plan | Where-Object { $_.op -ne 'SAME' } | ForEach-Object { @{ op = $_.op; file = $_.key; why = $_.why } }); same = [int]$count['SAME']; extra_untouched = $extra }
    [IO.File]::WriteAllText((Join-Path $repDir "$Stamp`_plan.json"), ($planOut | ConvertTo-Json -Depth 6), $Utf8NoBom)

    $blocked = @($plan | Where-Object { $_.op -like ($LocalModified + '*') })
    if (-not $Apply) {
        Say ''
        Say '只列出，没有改任何东西。照这个做：加 -Apply。'
        if ($blocked.Count -gt 0 -and -not $Force) { Say "有 $($blocked.Count) 个本地改过的文件：-Apply 时会整个拒绝；确认要用仓库的版本盖掉，再加 -Force（盖之前会进备份）。" }
        if ($mode -eq 'guess') { Say '这一条没有“同步：”行，路径是猜的：核对上面的“同步：”一行，对的话 -Apply 时再加 -AcceptGuess。' }
        exit 0
    }
    if ($mode -eq 'guess' -and -not $AcceptGuess) { Say '这一条没有“同步：”行，路径是猜的；核对过就加 -AcceptGuess 再跑。什么都没改。'; exit 1 }
    if ($blocked.Count -gt 0 -and -not $Force) { Say "拒绝：$($blocked.Count) 个文件在本地改过（见上面的 !）。什么都没改。要盖掉就加 -Force。"; exit 2 }

    # ── 5. 备份要覆盖 / 删除的 ─────────────────────────────────
    $touch = @($plan | Where-Object { $_.op -in @('OVERWRITE', 'DELETE', $LocalModified, ($LocalModified + '_DELETE')) })
    if ($touch.Count -gt 0 -or $recRaw) {
        Add-Type -AssemblyName System.IO.Compression -ErrorAction SilentlyContinue
        Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction SilentlyContinue
        $bdir = Join-Path $Project 'LanbaiSyncBackup'
        New-Item -ItemType Directory -Force -Path $bdir | Out-Null
        $zipPath = Join-Path $bdir "$Stamp.zip"
        $zip = [IO.Compression.ZipFile]::Open($zipPath, [IO.Compression.ZipArchiveMode]::Create)
        try {
            foreach ($p in $touch) {
                [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $p.dst, $p.key) | Out-Null
                if (Test-Path -LiteralPath ($p.dst + '.meta')) { [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, ($p.dst + '.meta'), ($p.key + '.meta')) | Out-Null }
            }
            if ($recRaw) { [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $RecordPath, 'Assets/Lanbai/.lanbai_sync.json') | Out-Null }
        } finally { $zip.Dispose() }
        Say "备份：$zipPath（$($touch.Count) 个文件$(if ($recRaw) { ' + 上次的同步记录' } else { '' })）"
    }

    # ── 6. 照计划做 ─────────────────────────────────────────────
    $now = Get-Date -Format 'o'
    foreach ($p in $plan) {
        switch -Wildcard ($p.op) {
            'ADD' { New-Item -ItemType Directory -Force -Path (Split-Path -Parent $p.dst) | Out-Null; Copy-Item -LiteralPath $p.src -Destination $p.dst -Force; $rec[$p.key] = @{ sha256 = $p.sha; repo = $p.repo; synced_at = $now } }
            'OVERWRITE' { Copy-Item -LiteralPath $p.src -Destination $p.dst -Force; $rec[$p.key] = @{ sha256 = $p.sha; repo = $p.repo; synced_at = $now } }
            'SAME' { $rec[$p.key] = @{ sha256 = $p.sha; repo = $p.repo; synced_at = $now } }
            'DELETE' { Remove-Item -LiteralPath $p.dst -Force; if (Test-Path -LiteralPath ($p.dst + '.meta')) { Remove-Item -LiteralPath ($p.dst + '.meta') -Force }; $rec.Remove($p.key) }
            'FORGET' { $rec.Remove($p.key) }
            ($LocalModified + '_DELETE') { Remove-Item -LiteralPath $p.dst -Force; if (Test-Path -LiteralPath ($p.dst + '.meta')) { Remove-Item -LiteralPath ($p.dst + '.meta') -Force }; $rec.Remove($p.key) }
            $LocalModified { Copy-Item -LiteralPath $p.src -Destination $p.dst -Force; $rec[$p.key] = @{ sha256 = $p.sha; repo = $p.repo; synced_at = $now } }
        }
    }

    # ── 7. 记录 ─────────────────────────────────────────────────
    $filesObj = [ordered]@{}
    foreach ($k in ($rec.Keys | Sort-Object)) { $filesObj[$k] = [ordered]@{ sha256 = $rec[$k].sha256; repo = $rec[$k].repo; synced_at = $rec[$k].synced_at } }
    $out = [ordered]@{
        tool = 'lanbai_sync.ps1'; tool_version = $ToolVersion; synced_at = $now; repo_path = $Repo; repo_commit = $commit; repo_branch = $branch; repo_dirty = [bool]$dirty
        entry = $entryTitle; mode = $mode; paths = $sel; excluded = $excl; forced = [bool]$Force; files = $filesObj
    }
    New-Item -ItemType Directory -Force -Path $Lanbai | Out-Null
    [IO.File]::WriteAllText($RecordPath, ($out | ConvertTo-Json -Depth 6), $Utf8NoBom)
    Say "完成：新增 $([int]$count['ADD'])，覆盖 $([int]$count['OVERWRITE'] + $(if ($Force) { [int]$count[$LocalModified] } else { 0 }))，删除 $([int]$count['DELETE'] + $(if ($Force) { [int]$count[$LocalModified + '_DELETE'] } else { 0 }))。记录：$RecordPath"
    Say '回到 Unity，等它导入、编译完，再跑测试。'
    exit 0
} catch {
    Write-Host "同步脚本出错：$($_.Exception.Message)"
    Write-Host $_.ScriptStackTrace
    exit 3
}
