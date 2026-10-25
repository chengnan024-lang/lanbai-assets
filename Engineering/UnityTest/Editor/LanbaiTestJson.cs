// 蓝白 · Unity 测试工具 · 极小的 JSON 读写（Dictionary<string, object> / List<object> / double / string / bool / null）
// 不用 JsonUtility：测试定义是自由结构；不用第三方库：本地工程里不一定有。
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace Lanbai.Test
{
    public static class TJson
    {
        static readonly CultureInfo IC = CultureInfo.InvariantCulture;

        // ── 读 ──────────────────────────────────────────────────────
        public static object Parse(string text)
        {
            int i = 0;
            if (text.Length > 0 && text[0] == '﻿') i = 1;
            object v = Val(text, ref i);
            Ws(text, ref i);
            if (i < text.Length) throw new FormatException("JSON：结尾多出字符 @" + i);
            return v;
        }

        static void Ws(string s, ref int i)
        {
            while (i < s.Length)
            {
                char c = s[i];
                if (char.IsWhiteSpace(c)) { i++; continue; }
                // 允许 // 注释（测试定义里写说明方便），标准 JSON 里没有
                if (c == '/' && i + 1 < s.Length && s[i + 1] == '/') { while (i < s.Length && s[i] != '\n') i++; continue; }
                break;
            }
        }

        static object Val(string s, ref int i)
        {
            Ws(s, ref i);
            if (i >= s.Length) throw new FormatException("JSON 意外结束");
            char c = s[i];
            if (c == '{')
            {
                var d = new Dictionary<string, object>();
                i++; Ws(s, ref i);
                if (i < s.Length && s[i] == '}') { i++; return d; }
                while (true)
                {
                    Ws(s, ref i);
                    string k = Str(s, ref i);
                    Ws(s, ref i);
                    if (i >= s.Length || s[i] != ':') throw new FormatException("JSON：缺冒号 @" + i);
                    i++;
                    d[k] = Val(s, ref i);
                    Ws(s, ref i);
                    if (i < s.Length && s[i] == ',') { i++; continue; }
                    if (i < s.Length && s[i] == '}') { i++; return d; }
                    throw new FormatException("JSON：对象里意外的字符 @" + i);
                }
            }
            if (c == '[')
            {
                var l = new List<object>();
                i++; Ws(s, ref i);
                if (i < s.Length && s[i] == ']') { i++; return l; }
                while (true)
                {
                    l.Add(Val(s, ref i));
                    Ws(s, ref i);
                    if (i < s.Length && s[i] == ',') { i++; continue; }
                    if (i < s.Length && s[i] == ']') { i++; return l; }
                    throw new FormatException("JSON：数组里意外的字符 @" + i);
                }
            }
            if (c == '"') return Str(s, ref i);
            if (string.CompareOrdinal(s, i, "true", 0, 4) == 0) { i += 4; return true; }
            if (string.CompareOrdinal(s, i, "false", 0, 5) == 0) { i += 5; return false; }
            if (string.CompareOrdinal(s, i, "null", 0, 4) == 0) { i += 4; return null; }
            int st = i;
            while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
            double v;
            if (st == i || !double.TryParse(s.Substring(st, i - st), NumberStyles.Float, IC, out v)) throw new FormatException("JSON：读不懂的值 @" + st);
            return v;
        }

        static string Str(string s, ref int i)
        {
            if (i >= s.Length || s[i] != '"') throw new FormatException("JSON：应该是字符串 @" + i);
            i++;
            var sb = new StringBuilder();
            while (i < s.Length && s[i] != '"')
            {
                char c = s[i++];
                if (c != '\\') { sb.Append(c); continue; }
                char e = s[i++];
                switch (e)
                {
                    case 'n': sb.Append('\n'); break;
                    case 't': sb.Append('\t'); break;
                    case 'r': sb.Append('\r'); break;
                    case 'b': sb.Append('\b'); break;
                    case 'f': sb.Append('\f'); break;
                    case 'u': sb.Append((char)Convert.ToInt32(s.Substring(i, 4), 16)); i += 4; break;
                    default: sb.Append(e); break;
                }
            }
            if (i >= s.Length) throw new FormatException("JSON：字符串没有结束");
            i++;
            return sb.ToString();
        }

        // ── 取值 ────────────────────────────────────────────────────
        public static Dictionary<string, object> M(object o) { return o as Dictionary<string, object>; }
        public static List<object> L(object o) { return o as List<object> ?? new List<object>(); }
        public static object G(object o, string k)
        {
            var d = M(o); object v;
            return d != null && d.TryGetValue(k, out v) ? v : null;
        }
        public static bool Has(object o, string k) { var d = M(o); return d != null && d.ContainsKey(k) && d[k] != null; }
        public static string S(object o, string def = null)
        {
            if (o == null) return def;
            if (o is string) return (string)o;
            if (o is double) return ((double)o).ToString("0.######", IC);
            if (o is bool) return (bool)o ? "true" : "false";
            return def;
        }
        public static double D(object o, double def = 0)
        {
            if (o is double) return (double)o;
            if (o is bool) return (bool)o ? 1 : 0;
            double v;
            if (o is string && double.TryParse((string)o, NumberStyles.Float, IC, out v)) return v;
            return def;
        }
        public static float F(object o, float def = 0f) { return (float)D(o, def); }
        public static int I(object o, int def = 0) { return o == null ? def : (int)Math.Round(D(o, def)); }
        public static bool B(object o, bool def = false) { return o is bool ? (bool)o : (o is double ? (double)o != 0 : def); }
        public static float[] Fa(object o)
        {
            var l = o as List<object>;
            if (l == null) return null;
            var r = new float[l.Count];
            for (int k = 0; k < l.Count; k++) r[k] = F(l[k]);
            return r;
        }
        public static List<string> Sa(object o)
        {
            var r = new List<string>();
            if (o is string) { r.Add((string)o); return r; }
            foreach (var x in L(o)) if (x != null) r.Add(S(x));
            return r;
        }

        /// <summary>浅合并：b 的键盖 a 的（a、b 都不改）。</summary>
        public static Dictionary<string, object> Merge(object a, object b)
        {
            var r = new Dictionary<string, object>();
            var da = M(a); var db = M(b);
            if (da != null) foreach (var kv in da) r[kv.Key] = kv.Value;
            if (db != null) foreach (var kv in db) r[kv.Key] = kv.Value;
            return r;
        }

        /// <summary>"a.b.c" 路径取值 / 设值（edit_json 用）。</summary>
        public static object GetPath(object root, string path)
        {
            object cur = root;
            foreach (var part in path.Split('.'))
            {
                int idx;
                if (cur is List<object> && int.TryParse(part, out idx)) { var l = (List<object>)cur; cur = idx >= 0 && idx < l.Count ? l[idx] : null; }
                else cur = G(cur, part);
                if (cur == null) return null;
            }
            return cur;
        }
        public static bool SetPath(object root, string path, object value)
        {
            var parts = path.Split('.');
            object cur = root;
            for (int k = 0; k < parts.Length - 1; k++)
            {
                int idx;
                if (cur is List<object> && int.TryParse(parts[k], out idx)) cur = ((List<object>)cur)[idx];
                else cur = G(cur, parts[k]);
                if (cur == null) return false;
            }
            string last = parts[parts.Length - 1];
            int li;
            if (cur is List<object> && int.TryParse(last, out li)) { ((List<object>)cur)[li] = value; return true; }
            var d = M(cur);
            if (d == null) return false;
            d[last] = value;
            return true;
        }

        // ── 写 ──────────────────────────────────────────────────────
        public static string Write(object o, bool pretty = true)
        {
            var sb = new StringBuilder();
            W(sb, o, pretty, 0);
            return sb.ToString();
        }

        static void Nl(StringBuilder sb, bool pretty, int ind)
        {
            if (!pretty) return;
            sb.Append('\n');
            sb.Append(' ', ind * 2);
        }

        static void W(StringBuilder sb, object o, bool pretty, int ind)
        {
            if (o == null) { sb.Append("null"); return; }
            if (o is string) { Q(sb, (string)o); return; }
            if (o is bool) { sb.Append((bool)o ? "true" : "false"); return; }
            if (o is double || o is float || o is int || o is long || o is decimal)
            {
                double v = Convert.ToDouble(o, IC);
                if (double.IsNaN(v) || double.IsInfinity(v)) { sb.Append("null"); return; }
                sb.Append(v.ToString("R", IC));
                return;
            }
            var d = o as System.Collections.IDictionary;
            if (d != null)
            {
                if (d.Count == 0) { sb.Append("{}"); return; }
                sb.Append('{');
                bool first = true;
                foreach (System.Collections.DictionaryEntry kv in d)
                {
                    if (!first) sb.Append(',');
                    first = false;
                    Nl(sb, pretty, ind + 1);
                    Q(sb, Convert.ToString(kv.Key, IC));
                    sb.Append(pretty ? ": " : ":");
                    W(sb, kv.Value, pretty, ind + 1);
                }
                Nl(sb, pretty, ind);
                sb.Append('}');
                return;
            }
            var e = o as System.Collections.IEnumerable;
            if (e != null)
            {
                // 纯数字的短数组写在一行上（坐标、颜色），别的一项一行
                var items = new List<object>();
                foreach (var x in e) items.Add(x);
                if (items.Count == 0) { sb.Append("[]"); return; }
                bool flat = items.Count <= 8;
                foreach (var x in items) if (!(x is double || x is float || x is int || x is long)) { flat = false; break; }
                sb.Append('[');
                for (int k = 0; k < items.Count; k++)
                {
                    if (k > 0) sb.Append(flat && pretty ? ", " : ",");
                    if (!flat) Nl(sb, pretty, ind + 1);
                    W(sb, items[k], pretty, ind + 1);
                }
                if (!flat) Nl(sb, pretty, ind);
                sb.Append(']');
                return;
            }
            Q(sb, Convert.ToString(o, IC));
        }

        static void Q(StringBuilder sb, string s)
        {
            sb.Append('"');
            foreach (char c in s)
            {
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4"));
                        else sb.Append(c);
                        break;
                }
            }
            sb.Append('"');
        }
    }
}
