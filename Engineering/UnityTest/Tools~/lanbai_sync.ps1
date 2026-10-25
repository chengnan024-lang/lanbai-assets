<#
蓝白 · 仓库 → Unity 工程 同步脚本（D-40a #5；v2 按总导演终审改）· 总工程师
  只同步 HANDOFF_LOG 当前那一条点名的文件夹 / 文件：仓库里的 X/... → 工程的 Assets/Lanbai/X/...
  * 文件从 **commit** 取，不从工作区取：用 git ls-tree -r HEAD 列、git cat-file 逐个取出（D-41 #5 批准的部分检出里，
    工作区里可能根本没有这些文件；以前从工作区列，会悄悄少拷）。HANDOFF_LOG 也从 HEAD 读。
  * -Repo 必须写；HEAD 必须等于 origin/main（不等就停：先在仓库里照 HANDOFF_CHATGPT 更新到最新的 main）。
  * 默认只列出（新增 / 覆盖 / 本地改过 / 仓库里没有了），不改任何东西；加 -Apply 才动手。
  * 原地覆盖文件，从不删文件夹再拷；工程里的 .meta 一概不碰，仓库里的 .meta 一律不同步（GUID 在工程的 .meta 里）。
  * 动手之前：要覆盖的文件（连 .meta）和上次的同步记录先打包进 <工程>\LanbaiSyncBackup\<时间>.zip。
  * 同步记录 Assets\Lanbai\.lanbai_sync.json：每个文件的 git blob 哈希、来自哪个提交、什么时候同步的。
    工程里的文件在那之后被本地改过的（或没有记录、又和仓库不一样的），整次拒绝，除非加 -Force。
    **-Force 属于批量替换（HANDOFF_CHATGPT §F）**：先整工程备份、把只列出的清单推到 FromLocal/takeover/、小楠确认以后才用。
  * 从不自动删除：仓库里没有了的文件只列出来，要删照 §F（挪到 _to_delete，经小楠确认）。
  * git 的任何一步出错都当作出错（不当成“干净”），停下（退出码 4），不自动修。

用法（PowerShell 5.1 或 7）：
  powershell -ExecutionPolicy Bypass -File lanbai_sync.ps1 -Repo "<仓库>" -Project "<工程>"            # 只列出（看当前那一条）
  powershell -ExecutionPolicy Bypass -File lanbai_sync.ps1 -Repo "<仓库>" -Project "<工程>" -Apply     # 照列出的做
  -Repo <路径>        仓库（必填；要是更新到最新 main 的那一个，HANDOFF_CHATGPT §C 第 5 步）
  -Project <路径>     Unity 工程（必填）
  -Entry <n>          HANDOFF_LOG 的第 n 条（1 = 最上面、最新的，默认）
  -EntryMatch <字>    标题里含这几个字的那一条（比 -Entry 优先）
  -Paths a/,b/c.json  不看 HANDOFF_LOG，直接指定（只在总导演 / 总工程师明说时用）
  -AcceptGuess        这一条没有“同步：”行、路径是从反引号里猜的时候，确认按猜的做
  -Force              本地改过的文件也覆盖（照样先进备份；见上面 §F）
退出码：0 完成（或只列出）；1 没有可同步的；2 有本地改过的文件被拒绝（什么都没改）；3 脚本出错；4 仓库状态不对（什么都没改）。
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Repo,
    [Parameter(Mandatory = $true)][string]$Project,
    [int]$Entry = 1,
    [string]$EntryMatch = '',
    [string[]]$Paths = @(),
    [switch]$Apply,
    [switch]$Force,
    [switch]$AcceptGuess
)

$ErrorActionPreference = 'Stop'
$ToolVersion = '2.0.0'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }
$Utf8NoBom = New-Object Text.UTF8Encoding $false

# 永远不同步的：顶层的这些、任何一层叫这些名字的文件夹、这些扩展名
$SkipTop = @('FromLocal', 'Art', '.git', '.github', '.claude')
$SkipDirs = @('Source', 'Renders', '__pycache__', '.git')
$SkipExt = @('.py', '.pyc', '.blend', '.blend1', '.ps1', '.sh', '.meta')
$LocalModified = 'LOCAL_MODIFIED'

function Say([string]$s) { Write-Host $s }
function Norm([string]$p) { return ($p -replace '\\', '/').Trim('/') }
function Stop4([string]$msg) { Say ("停：" + $msg + " 什么都没改。"); exit 4 }

# git：用 Process 跑，stdout / stderr 分开读（PowerShell 5.1 下 `& git ... 2>$null` 会把 stderr 变成异常或吞掉）
function GitRun([string[]]$gitArgs, [string]$outFile = $null) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'git'
    $q = @('-C', $Repo) + $gitArgs | ForEach-Object { if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ } }
    $psi.Arguments = ($q -join ' ')
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    try { $p = [System.Diagnostics.Process]::Start($psi) } catch { return @{ ok = $false; code = -1; out = ''; err = 'git 跑不起来：' + $_.Exception.Message } }
    $errTask = $p.StandardError.ReadToEndAsync()
    $out = ''
    if ($outFile) {
        $fs = [System.IO.File]::Create($outFile)
        try { $p.StandardOutput.BaseStream.CopyTo($fs) } finally { $fs.Dispose() }        # 原样的字节（二进制文件）
    } else {
        $ms = New-Object System.IO.MemoryStream
        $p.StandardOutput.BaseStream.CopyTo($ms)
        $out = [Text.Encoding]::UTF8.GetString($ms.ToArray())
    }
    $p.WaitForExit()
    return @{ ok = ($p.ExitCode -eq 0); code = $p.ExitCode; out = $out; err = $errTask.Result }
}
function GitText([string[]]$gitArgs, [string]$what) {
    $r = GitRun $gitArgs
    if (-not $r.ok) { Stop4 ($what + " 失败（git " + ($gitArgs -join ' ') + "，退出码 " + $r.code + "）：" + $r.err.Trim()) }
    return $r.out
}

# 文件的 git blob 哈希（sha1("blob <长度>\0" + 内容)），和 ls-tree 给的一样，用来比“工程里的这个文件是不是仓库里那一版”
function BlobSha([string]$file) {
    $bytes = [System.IO.File]::ReadAllBytes($file)
    $head = [Text.Encoding]::ASCII.GetBytes("blob " + $bytes.Length + [char]0)
    $sha = [System.Security.Cryptography.SHA1]::Create()
    try {
        $sha.TransformBlock($head, 0, $head.Length, $null, 0) | Out-Null
        $sha.TransformFinalBlock($bytes, 0, $bytes.Length) | Out-Null
        return (($sha.Hash | ForEach-Object { $_.ToString('x2') }) -join '')
    } finally { $sha.Dispose() }
}
function Sha256([string]$file) { return (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() }

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
    if (-not (Test-Path -LiteralPath $Repo)) { Stop4 "仓库不在：$Repo" }
    $Repo = (Resolve-Path -LiteralPath $Repo).Path
    $Project = (Resolve-Path -LiteralPath $Project).Path
    if (-not (Test-Path -LiteralPath (Join-Path $Project 'Assets'))) { throw "不是 Unity 工程（没有 Assets 文件夹）：$Project" }
    $Lanbai = Join-Path (Join-Path $Project 'Assets') 'Lanbai'
    $RecordPath = Join-Path $Lanbai '.lanbai_sync.json'
    $Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

    # ── 1. 仓库的状态（任何一步出错都停，fail closed）─────────────
    $lock = Join-Path (Join-Path $Repo '.git') 'index.lock'
    if (Test-Path -LiteralPath $lock) { Stop4 "仓库里有 $lock（上一次 git 没正常结束，或者还有 git 在跑）。不自动删它：确认没有 git 在跑以后人工处理，再重跑。" }
    $commit = (GitText @('rev-parse', 'HEAD') '读 HEAD').Trim()
    $branch = (GitText @('rev-parse', '--abbrev-ref', 'HEAD') '读分支').Trim()
    $originMain = (GitText @('rev-parse', 'origin/main') '读 origin/main').Trim()
    $status = GitText @('status', '--porcelain') 'git status'
    Say "蓝白同步 $ToolVersion"
    Say "  仓库 $Repo"
    Say "  工程 $Project"
    Say "  仓库 HEAD $commit（$branch），origin/main $originMain"
    if ($commit -ne $originMain) { Stop4 "仓库的 HEAD 不是 origin/main（$commit ≠ $originMain）。先照 HANDOFF_CHATGPT §C 第 5 步把这个仓库更新到最新的 main，或者 -Repo 换成更新过的那一个。" }
    if ($status.Trim().Length -gt 0) { Say $status; Stop4 "仓库里有没提交的改动（git status --porcelain 不是空的）。不自动处理：人工看过再重跑。" }

    # ── 2. 这次同步哪些路径（HANDOFF_LOG 从 HEAD 读）──────────────
    $mode = 'entry'
    $entryTitle = ''
    $sel = New-Object System.Collections.Generic.List[string]
    $excl = New-Object System.Collections.Generic.List[string]
    if ($Paths.Count -gt 0) {
        $mode = 'paths'
        foreach ($p in $Paths) { foreach ($q in ($p -split ',')) { if ($q.Trim()) { $sel.Add((Norm $q.Trim())) } } }
        $entryTitle = '（-Paths 指定）'
    } else {
        $logText = GitText @('show', 'HEAD:HANDOFF_LOG.md') '从 HEAD 读 HANDOFF_LOG.md'
        $lines = $logText -split "`r?`n"
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
            $mode = 'guess'
            $negRx = [regex]'不要拷|别拷|不拷|不同步|别导入|先别导入|不要导入|不用拷'
            foreach ($l in $pick.body) {
                $nm = $negRx.Match($l)
                $negAt = $(if ($nm.Success) { $nm.Index } else { [int]::MaxValue })
                foreach ($m in $rx.Matches($l)) {
                    $neg = $m.Index -gt $negAt
                    $tok = Norm $m.Groups[1].Value
                    if ($tok -notmatch '^[A-Za-z0-9_][A-Za-z0-9_~.\-/]*$') { continue }
                    if ($tok.Split('/').Count -eq 1 -and $tok -notmatch '/$' -and $m.Groups[1].Value -notmatch '/$') { continue }
                    if ($neg) { $excl.Add($tok) } else { $sel.Add($tok) }
                }
            }
        }
    }
    $sel = @($sel | Select-Object -Unique)
    $excl = @($excl | Select-Object -Unique)
    Say "  条目「$entryTitle」（$(if ($mode -eq 'guess') { '没有“同步：”行，路径是猜的' } elseif ($mode -eq 'paths') { '-Paths 指定' } else { '按“同步：”行' })）"
    Say "  同步：$(if ($sel.Count) { $sel -join '  ' } else { '（没有）' })"
    if ($excl.Count) { Say "  不同步：$($excl -join '  ')" }
    if ($sel.Count -eq 0) { Say '没有要同步的路径。'; exit 1 }

    # ── 3. 从 commit 列文件（git ls-tree -r HEAD）───────────────
    $repoFiles = @{}          # 相对路径 → blob 哈希
    foreach ($s in $sel) {
        if ($SkipTop -contains $s.Split('/')[0]) { Say "  跳过 $s（这个文件夹从不进工程）"; continue }
        $lt = GitText @('ls-tree', '-r', '-z', '--full-tree', 'HEAD', '--', $s) "列 HEAD 里的 $s"
        $n = 0
        foreach ($rec in ($lt -split [char]0)) {
            if (-not $rec) { continue }
            $tab = $rec.IndexOf("`t")
            if ($tab -lt 0) { continue }
            $meta = $rec.Substring(0, $tab).Split(' ')
            $rel = Norm $rec.Substring($tab + 1)
            if ($meta.Count -lt 3 -or $meta[1] -ne 'blob' -or $meta[0] -eq '120000') { continue }   # 只要普通文件（不要子模块、软链接）
            if ($rel -ne $s -and -not $rel.StartsWith($s.TrimEnd('/') + '/')) { continue }
            if (Skip $rel) { continue }
            $ex = $false
            foreach ($x in $excl) { if ($rel -eq $x -or $rel.StartsWith($x.TrimEnd('/') + '/')) { $ex = $true; break } }
            if ($ex) { continue }
            $repoFiles[$rel] = $meta[2]
            $n++
        }
        if ($n -eq 0) { Say "  ⚠ HEAD 里没有 $s 下的文件（或全被排除了）" }
    }

    # ── 4. 上次的记录 ───────────────────────────────────────────
    $rec = @{}
    $recRaw = $null
    if (Test-Path -LiteralPath $RecordPath) {
        $recRaw = [IO.File]::ReadAllText($RecordPath, [Text.Encoding]::UTF8)
        $j = $recRaw | ConvertFrom-Json
        if ($j.files) { foreach ($p in $j.files.PSObject.Properties) { $rec[$p.Name] = @{ blob = $p.Value.blob; sha256 = $p.Value.sha256; commit = $p.Value.commit; repo = $p.Value.repo; synced_at = $p.Value.synced_at } } }
    }
    function SameAsRecord($r, [string]$file) {
        if ($r -eq $null) { return $false }
        if ($r.blob) { return (BlobSha $file) -eq $r.blob }
        if ($r.sha256) { return (Sha256 $file) -eq $r.sha256 }      # v1 的记录
        return $false
    }

    # ── 5. 逐个文件比 ───────────────────────────────────────────
    $plan = New-Object System.Collections.Generic.List[object]
    foreach ($rel in ($repoFiles.Keys | Sort-Object)) {
        $key = 'Assets/Lanbai/' + $rel
        $dst = Join-Path $Lanbai ($rel -replace '/', [IO.Path]::DirectorySeparatorChar)
        $blob = $repoFiles[$rel]
        if (-not (Test-Path -LiteralPath $dst)) { $plan.Add(@{ op = 'ADD'; key = $key; dst = $dst; blob = $blob; repo = $rel }); continue }
        if ((BlobSha $dst) -eq $blob) { $plan.Add(@{ op = 'SAME'; key = $key; dst = $dst; blob = $blob; repo = $rel }); continue }
        $r = $rec[$key]
        if (SameAsRecord $r $dst) { $plan.Add(@{ op = 'OVERWRITE'; key = $key; dst = $dst; blob = $blob; repo = $rel }) }
        else { $plan.Add(@{ op = $LocalModified; key = $key; dst = $dst; blob = $blob; repo = $rel; why = $(if ($r -eq $null) { '没有同步记录，和仓库不一样' } else { '上次同步以后在本地改过' }) }) }
    }
    foreach ($key in @($rec.Keys)) {
        $rel = $key.Substring('Assets/Lanbai/'.Length)
        $under = $false
        foreach ($s in $sel) { if ($rel -eq $s -or $rel.StartsWith($s.TrimEnd('/') + '/')) { $under = $true; break } }
        if (-not $under -or $repoFiles.ContainsKey($rel)) { continue }
        $dst = Join-Path $Lanbai ($rel -replace '/', [IO.Path]::DirectorySeparatorChar)
        if (-not (Test-Path -LiteralPath $dst)) { $plan.Add(@{ op = 'FORGET'; key = $key; dst = $dst }); continue }
        $plan.Add(@{ op = 'GONE'; key = $key; dst = $dst; why = $(if (SameAsRecord $rec[$key] $dst) { '上次同步以后没改过' } else { '本地改过' }) })
    }
    $extra = 0
    foreach ($s in $sel) {
        $d = Join-Path $Lanbai ($s -replace '/', [IO.Path]::DirectorySeparatorChar)
        if (Test-Path -LiteralPath $d -PathType Container) {
            foreach ($f in (Get-ChildItem -LiteralPath $d -Recurse -File -Force)) {
                if ($f.Name.EndsWith('.meta')) { continue }
                $r2 = Norm ($f.FullName.Substring($Lanbai.Length))
                if (-not $repoFiles.ContainsKey($r2) -and -not $rec.ContainsKey('Assets/Lanbai/' + $r2)) { $extra++ }
            }
        }
    }

    $count = @{}
    foreach ($p in $plan) { $count[$p.op] = 1 + [int]$count[$p.op] }
    Say ''
    Say "计划：新增 $([int]$count['ADD'])，覆盖 $([int]$count['OVERWRITE'])，一样的 $([int]$count['SAME'])，本地改过的 $([int]$count[$LocalModified])；仓库里没有了的 $([int]$count['GONE']) 个只列出、不删；工程里多出来的 $extra 个不动"
    foreach ($op in @('ADD', 'OVERWRITE', $LocalModified, 'GONE')) {
        foreach ($p in ($plan | Where-Object { $_.op -eq $op })) {
            $tag = @{ 'ADD' = '  + 新增  '; 'OVERWRITE' = '  ~ 覆盖  '; 'GONE' = '  ? 仓库里没有了（不自动删）'
                      $LocalModified = $(if ($Force) { '  ! 本地改过，-Force 照样覆盖 ' } else { '  ! 本地改过，不覆盖 ' }) }[$op]
            Say ("$tag$($p.key)" + $(if ($p.why) { "（$($p.why)）" } else { '' }))
        }
    }
    $repDir = Join-Path (Join-Path $Project 'LanbaiReports') 'sync'
    New-Item -ItemType Directory -Force -Path $repDir | Out-Null
    $planOut = @{ tool_version = $ToolVersion; at = (Get-Date -Format 'o'); applied = [bool]$Apply; force = [bool]$Force; mode = $mode; entry = $entryTitle; repo_commit = $commit; paths = $sel; excluded = $excl;
                  plan = @($plan | Where-Object { $_.op -ne 'SAME' } | ForEach-Object { @{ op = $_.op; file = $_.key; why = $_.why } }); same = [int]$count['SAME']; extra_untouched = $extra }
    [IO.File]::WriteAllText((Join-Path $repDir "$Stamp`_plan.json"), ($planOut | ConvertTo-Json -Depth 6), $Utf8NoBom)

    $blocked = @($plan | Where-Object { $_.op -eq $LocalModified })
    if (-not $Apply) {
        Say ''
        Say '只列出，没有改任何东西。照这个做：加 -Apply。'
        if ($blocked.Count -gt 0 -and -not $Force) { Say "有 $($blocked.Count) 个本地改过的文件：-Apply 时会整个拒绝。-Force 属于批量替换（HANDOFF_CHATGPT §F）：先整工程备份、把这份清单推到 FromLocal/takeover/、小楠确认以后才用。" }
        if ($mode -eq 'guess') { Say '这一条没有“同步：”行，路径是猜的：核对上面的“同步：”一行，对的话 -Apply 时再加 -AcceptGuess。' }
        exit 0
    }
    if ($mode -eq 'guess' -and -not $AcceptGuess) { Say '这一条没有“同步：”行，路径是猜的；核对过就加 -AcceptGuess 再跑。什么都没改。'; exit 1 }
    if ($blocked.Count -gt 0 -and -not $Force) { Say "拒绝：$($blocked.Count) 个文件在本地改过（见上面的 !）。什么都没改。停，告诉小楠；要用仓库的版本盖掉，照 §F 先备份、推清单、经小楠确认再加 -Force。"; exit 2 }

    # ── 6. 备份要覆盖的 ─────────────────────────────────────────
    $touch = @($plan | Where-Object { $_.op -in @('OVERWRITE', $LocalModified) })
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

    # ── 7. 照计划做：从 commit 取出（git cat-file blob），先写临时文件、核对哈希，再原地覆盖 ───
    $now = Get-Date -Format 'o'
    foreach ($p in $plan) {
        if ($p.op -in @('ADD', 'OVERWRITE', $LocalModified)) {
            $dir = Split-Path -Parent $p.dst
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
            $tmp = $p.dst + '.lanbai_sync_tmp'
            $r = GitRun @('cat-file', 'blob', $p.blob) $tmp
            if (-not $r.ok) { if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force }; throw ("取不出 " + $p.repo + "（" + $p.blob + "）：" + $r.err.Trim()) }
            if ((BlobSha $tmp) -ne $p.blob) { Remove-Item -LiteralPath $tmp -Force; throw ("取出来的 " + $p.repo + " 哈希不对") }
            Move-Item -LiteralPath $tmp -Destination $p.dst -Force
            $rec[$p.key] = @{ blob = $p.blob; commit = $commit; repo = $p.repo; synced_at = $now }
        }
        elseif ($p.op -eq 'SAME') {
            $old = $rec[$p.key]
            $rec[$p.key] = @{ blob = $p.blob; commit = $(if ($old -and $old.blob -eq $p.blob -and $old.commit) { $old.commit } else { $commit }); repo = $p.repo; synced_at = $(if ($old -and $old.synced_at) { $old.synced_at } else { $now }) }
        }
        elseif ($p.op -eq 'FORGET') { $rec.Remove($p.key) }
    }

    # ── 8. 记录（每个文件记它来自哪个提交）─────────────────────
    $filesObj = [ordered]@{}
    foreach ($k in ($rec.Keys | Sort-Object)) { $filesObj[$k] = [ordered]@{ blob = $rec[$k].blob; sha256 = $rec[$k].sha256; commit = $rec[$k].commit; repo = $rec[$k].repo; synced_at = $rec[$k].synced_at } }
    $out = [ordered]@{
        tool = 'lanbai_sync.ps1'; tool_version = $ToolVersion; synced_at = $now; repo_path = $Repo; repo_commit = $commit; repo_branch = $branch; origin_main = $originMain
        entry = $entryTitle; mode = $mode; paths = $sel; excluded = $excl; forced = [bool]$Force; files = $filesObj
    }
    New-Item -ItemType Directory -Force -Path $Lanbai | Out-Null
    [IO.File]::WriteAllText($RecordPath, ($out | ConvertTo-Json -Depth 6), $Utf8NoBom)
    Say "完成：新增 $([int]$count['ADD'])，覆盖 $([int]$count['OVERWRITE'] + $(if ($Force) { [int]$count[$LocalModified] } else { 0 }))（都从提交 $commit 取）；仓库里没有了的 $([int]$count['GONE']) 个没删。记录：$RecordPath"
    if ([int]$count['GONE'] -gt 0) { Say '仓库里没有了的文件还留在工程里：要删照 HANDOFF_CHATGPT §F（挪到 _to_delete、连 .meta、经小楠确认）。' }
    Say '回到 Unity，等它导入、编译完，再跑测试。'
    exit 0
} catch {
    Write-Host "同步脚本出错：$($_.Exception.Message)"
    Write-Host $_.ScriptStackTrace
    exit 3
}
