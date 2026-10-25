// 蓝白 · Unity 测试工具 · Console 抓取
//  * 开跑前 Console 里已有的（编译错误、UdonSharp 的输出都在这里）：读 UnityEditor.LogEntries（内部 API，反射；读不到就记一条说明）；
//  * 跑的过程中新来的：Application.logMessageReceivedThreaded，带类型和堆栈；
//  * 跑的过程中如果触发了编译：CompilationPipeline.assemblyCompilationFinished 的每条编译消息。
// 全部写成 console.jsonl，一行一条。
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEngine;

namespace Lanbai.Test
{
    public sealed class LogCapture
    {
        public const string TAG = "[LanbaiTest]";
        readonly object _lock = new object();
        readonly List<Dictionary<string, object>> _rows = new List<Dictionary<string, object>>();
        readonly DateTime _t0 = DateTime.UtcNow;
        bool _on;

        public int Count { get { lock (_lock) return _rows.Count; } }

        public void Start()
        {
            if (_on) return;
            _on = true;
            Application.logMessageReceivedThreaded += OnLog;
            CompilationPipeline.assemblyCompilationFinished += OnCompiled;
        }

        public void Stop()
        {
            if (!_on) return;
            _on = false;
            Application.logMessageReceivedThreaded -= OnLog;
            CompilationPipeline.assemblyCompilationFinished -= OnCompiled;
        }

        void Add(string source, string type, string msg, string stack, string file, int line)
        {
            var r = new Dictionary<string, object>();
            r["t"] = Math.Round((DateTime.UtcNow - _t0).TotalSeconds, 3);
            r["source"] = source;
            r["type"] = type;
            r["msg"] = msg ?? "";
            if (!string.IsNullOrEmpty(stack)) r["stack"] = stack;
            if (!string.IsNullOrEmpty(file)) { r["file"] = file; r["line"] = (double)line; }
            if ((msg ?? "").IndexOf("UdonSharp", StringComparison.OrdinalIgnoreCase) >= 0 ||
                (msg ?? "").IndexOf("U#", StringComparison.Ordinal) >= 0) r["udonsharp"] = true;
            if ((msg ?? "").StartsWith(TAG, StringComparison.Ordinal)) r["tool"] = true;
            lock (_lock) _rows.Add(r);
        }

        void OnLog(string msg, string stack, LogType type) { Add("live", type.ToString(), msg, stack, null, 0); }

        void OnCompiled(string assembly, CompilerMessage[] msgs)
        {
            foreach (var m in msgs)
                Add("compile", m.type == CompilerMessageType.Error ? "CompileError" : "CompileWarning", assembly + ": " + m.message, null, m.file, m.line);
        }

        /// <summary>开跑前 Console 窗口里已有的条目（含编译错误、UdonSharp）。返回读到几条；读不到返回 -1。</summary>
        public int SnapshotConsole()
        {
            try
            {
                var asm = typeof(EditorWindow).Assembly;
                var tEntries = asm.GetType("UnityEditor.LogEntries");
                var tEntry = asm.GetType("UnityEditor.LogEntry");
                if (tEntries == null || tEntry == null) throw new Exception("UnityEditor.LogEntries / LogEntry 不在");
                const BindingFlags SF = BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
                var start = tEntries.GetMethod("StartGettingEntries", SF);
                var end = tEntries.GetMethod("EndGettingEntries", SF);
                var count = tEntries.GetMethod("GetCount", SF);
                var get = tEntries.GetMethod("GetEntryInternal", SF);
                if (start == null || end == null || count == null || get == null) throw new Exception("LogEntries 的方法变了");
                var entry = Activator.CreateInstance(tEntry);
                const BindingFlags IF = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
                var fMsg = tEntry.GetField("message", IF);
                var fFile = tEntry.GetField("file", IF);
                var fLine = tEntry.GetField("line", IF);
                var fMode = tEntry.GetField("mode", IF);
                int n = 0;
                start.Invoke(null, null);
                try
                {
                    n = (int)count.Invoke(null, null);
                    for (int i = 0; i < n; i++)
                    {
                        get.Invoke(null, new object[] { i, entry });
                        string full = fMsg != null ? (string)fMsg.GetValue(entry) : "";
                        int mode = fMode != null ? Convert.ToInt32(fMode.GetValue(entry)) : 0;
                        string file = fFile != null ? (string)fFile.GetValue(entry) : null;
                        int line = fLine != null ? Convert.ToInt32(fLine.GetValue(entry)) : 0;
                        // 第一行是消息，后面是堆栈（Console 里存的就是这样）
                        string msg = full, stack = null;
                        int nl = full.IndexOf('\n');
                        if (nl >= 0) { msg = full.Substring(0, nl); stack = full.Substring(nl + 1); }
                        Add("console_snapshot", ModeToType(mode, msg), msg, stack, file, line);
                    }
                }
                finally { end.Invoke(null, null); }
                return n;
            }
            catch (Exception e)
            {
                Add("tool", "Warning", TAG + " 读不到开跑前的 Console（" + e.Message + "）；编译错误看 EditorUtility.scriptCompilationFailed 和 -logFile", null, null, 0);
                return -1;
            }
        }

        // LogEntry.mode 的位（Unity 2022.3 的 ConsoleWindow.Mode）：没有公开定义，按已知的位读，读不准时退回看消息文本
        static string ModeToType(int mode, string msg)
        {
            const int Error = 1 << 0, Assert = 1 << 1, Fatal = 1 << 4, AssetImportError = 1 << 6, AssetImportWarning = 1 << 7,
                ScriptingError = 1 << 8, ScriptingWarning = 1 << 9, ScriptCompileError = 1 << 11, ScriptCompileWarning = 1 << 12,
                ScriptingException = 1 << 17, ScriptingAssertion = 1 << 21;
            if ((mode & ScriptCompileError) != 0) return "CompileError";
            if ((mode & ScriptCompileWarning) != 0) return "CompileWarning";
            if ((mode & ScriptingException) != 0) return "Exception";
            if ((mode & (ScriptingAssertion | Assert)) != 0) return "Assert";
            if ((mode & (Error | Fatal | AssetImportError | ScriptingError)) != 0) return "Error";
            if ((mode & (ScriptingWarning | AssetImportWarning)) != 0) return "Warning";
            if (msg.Contains("error CS")) return "CompileError";
            if (msg.Contains("warning CS")) return "CompileWarning";
            return "Log";
        }

        /// <summary>从 index 起的新条目里，有没有包含 text 的消息。</summary>
        public bool ContainsSince(int index, string text)
        {
            lock (_lock)
                for (int i = Math.Max(0, index); i < _rows.Count; i++)
                    if (((string)_rows[i]["msg"]).IndexOf(text, StringComparison.Ordinal) >= 0) return true;
            return false;
        }

        public int CountWhere(Func<Dictionary<string, object>, bool> f)
        {
            int n = 0;
            lock (_lock) foreach (var r in _rows) if (f(r)) n++;
            return n;
        }

        public List<string> MessagesWhere(Func<Dictionary<string, object>, bool> f, int max)
        {
            var l = new List<string>();
            lock (_lock) foreach (var r in _rows) if (f(r)) { if (l.Count >= max) break; l.Add((string)r["msg"]); }
            return l;
        }

        public static bool IsTool(Dictionary<string, object> r) { return r.ContainsKey("tool"); }
        public static string Type(Dictionary<string, object> r) { return (string)r["type"]; }
        public static string Source(Dictionary<string, object> r) { return (string)r["source"]; }

        /// <summary>Play 阶段（1.2.0）：进 Play 之前的 Console 行存进文件，reload 以后读回来接着记。</summary>
        public List<Dictionary<string, object>> Rows() { lock (_lock) return new List<Dictionary<string, object>>(_rows); }
        public void Preload(IEnumerable<Dictionary<string, object>> rows) { lock (_lock) _rows.InsertRange(0, rows); }
        public void Append(IEnumerable<Dictionary<string, object>> rows) { if (rows != null) lock (_lock) _rows.AddRange(rows); }
        public void Clear() { lock (_lock) _rows.Clear(); }

        public void WriteJsonl(string path)
        {
            var sb = new StringBuilder();
            lock (_lock) foreach (var r in _rows) sb.Append(TJson.Write(r, false)).Append('\n');
            File.WriteAllText(path, sb.ToString(), new UTF8Encoding(false));
        }
    }
}
