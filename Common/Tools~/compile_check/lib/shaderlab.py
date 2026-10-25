"""ShaderLab side of a .shader file: program blocks, their pass / tags, the Properties block, and the ShaderLab lints
that no HLSL compiler sees (Unity's ShaderLab parser does):
  * [Header(...)] text with ':' (syntax error: the whole shader fails to import) or '(' ')' ',' (the drawer fails:
    'Failed to create material drawer Header with arguments ...') - CONTROL_总控.md §6 item 2.
  * a property line the parser would not accept (warning: the pattern below is ours, not Unity's grammar).
  * [KeywordEnum] / [Toggle(KW)] keywords never declared by a #pragma (the material control would do nothing).
  * ZTest Always (CONTROL §3: only the overlay / mask sphere may use it; D-45 #10 adds the poem subtitles and their
    line halos; the desktop letterbox (D-45 #15.3) is listed too, pending the director's wording in the bible).
"""
import re

PROGRAM_RE = re.compile(r'\b(CGPROGRAM|CGINCLUDE|HLSLPROGRAM|HLSLINCLUDE)\b(.*?)\b(ENDCG|ENDHLSL)\b', re.S)


def blank_comments(text):
    """Same length / same newlines, with // and /* */ comments replaced by spaces (strings kept)."""
    out, i, n = [], 0, len(text)
    while i < n:
        if text.startswith('//', i):
            j = text.find('\n', i)
            j = n if j < 0 else j
            out.append(' ' * (j - i)); i = j
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r'[^\n]', ' ', text[i:j])); i = j
        elif text[i] == '"':
            j = text.find('"', i + 1)
            j = n if j < 0 else j + 1
            out.append(text[i:j]); i = j
        else:
            out.append(text[i]); i += 1
    return ''.join(out)


def line_of(text, pos):
    return text.count('\n', 0, pos) + 1



ZTEST_ALWAYS_OK = {'Lanbai/Overlay', 'Lanbai/Subtitle', 'Lanbai/SubtitleHalo', 'Lanbai/Letterbox'}

class Block:
    def __init__(self, kind, text, line, start):
        self.kind = kind            # CGPROGRAM / CGINCLUDE / HLSLPROGRAM / HLSLINCLUDE
        self.text = text            # the code between the keywords (original text, comments kept)
        self.line = line            # 1-based line of the first character of self.text
        self.start = start
        self.pass_index = None      # index of the enclosing Pass in its SubShader (None = SubShader level)
        self.subshader = 0
        self.pass_name = None
        self.tags = {}              # merged SubShader + Pass tags


class ShaderFile:
    def __init__(self, path):
        self.path = path
        self.text = open(path, encoding='utf-8-sig').read()
        self.clean = blank_comments(self.text)
        self.name = None
        self.blocks = []
        self.properties = []        # (line, text) of every line inside Properties { }
        self.props_span = None
        self.ztest_always = []      # lines
        self._parse()

    def _parse(self):
        clean = self.clean
        spans = []
        for m in PROGRAM_RE.finditer(clean):
            body_start = m.start(2)
            b = Block(m.group(1), self.text[body_start:m.end(2)], line_of(self.text, body_start), body_start)
            self.blocks.append(b)
            spans.append((m.start(), m.end()))
        # ShaderLab outside the programs: blank the programs, then walk the braces
        sl = list(clean)
        for a, e in spans:
            for k in range(a, e):
                if sl[k] != '\n':
                    sl[k] = ' '
        sl = ''.join(sl)
        m = re.search(r'\bShader\s+"([^"]*)"', sl)
        self.name = m.group(1) if m else None
        contexts = []           # (kind, start, end, info)
        stack = []
        tokens = list(re.finditer(r'"[^"]*"|[{}\[\]=]|\w+', sl))
        pending = None          # keyword waiting for its '{'
        tags_target = None
        for i, t in enumerate(tokens):
            s = t.group(0)
            if s in ('SubShader', 'Pass', 'Properties', 'Tags', 'GrabPass', 'Stencil', 'CGPROGRAM'):
                pending = s
                continue
            if s == '{':
                kind = pending or 'brace'
                stack.append([kind, t.start(), None, {}])
                pending = None
                continue
            if s == '}':
                if stack:
                    c = stack.pop()
                    c[2] = t.end()
                    contexts.append(c)
                continue
            if stack and stack[-1][0] == 'Tags' and s.startswith('"'):
                # "Key" = "Value"
                if i + 2 < len(tokens) and tokens[i + 1].group(0) == '=' and tokens[i + 2].group(0).startswith('"'):
                    owner = next((c for c in reversed(stack[:-1]) if c[0] in ('Pass', 'SubShader')), None)
                    if owner is not None:
                        owner[3].setdefault('tags', {})[s.strip('"')] = tokens[i + 2].group(0).strip('"')
            if s == 'Name' and stack and stack[-1][0] == 'Pass' and i + 1 < len(tokens) and tokens[i + 1].group(0).startswith('"'):
                stack[-1][3]['name'] = tokens[i + 1].group(0).strip('"')
            if pending and s not in ('{',):
                pending = None if not s.startswith('"') else pending
        subs = sorted([c for c in contexts if c[0] == 'SubShader'], key=lambda c: c[1])
        passes = sorted([c for c in contexts if c[0] == 'Pass'], key=lambda c: c[1])
        for b in self.blocks:
            sub = next((k for k, c in enumerate(subs) if c[1] <= b.start <= c[2]), 0)
            b.subshader = sub
            tags = dict(subs[sub][3].get('tags', {})) if subs else {}
            in_sub = [p for p in passes if subs and subs[sub][1] <= p[1] <= subs[sub][2]]
            for k, p in enumerate(in_sub):
                if p[1] <= b.start <= p[2]:
                    b.pass_index = k
                    b.pass_name = p[3].get('name')
                    tags.update(p[3].get('tags', {}))
            b.tags = tags
        props = [c for c in contexts if c[0] == 'Properties']
        if props:
            a, e = props[0][1], props[0][2]
            self.props_span = (line_of(self.text, a), line_of(self.text, e))
            for ln in range(self.props_span[0] + 1, self.props_span[1]):
                self.properties.append((ln, self.clean.split('\n')[ln - 1]))
        for m in re.finditer(r'\bZTest\s+Always\b', sl):
            self.ztest_always.append(line_of(self.text, m.start()))

    # ---------------------------------------------------------------------------------------- lints
    PROP_RE = re.compile(r'^\s*((?:\[[^\]]*\]\s*)*)(\w+)\s*\(\s*"[^"]*"\s*,\s*'
                         r'(Float|Int|Integer|Range\s*\(\s*[-+.\deE]+\s*,\s*[-+.\deE]+\s*\)|Color|Vector|2D|3D|Cube|2DArray|3DArray|CubeArray|Any)'
                         r'\s*\)\s*=\s*(.+?)\s*$')

    def lint(self, declared_keywords):
        """-> list of (level, line, message). declared_keywords: set of keywords from every #pragma of the file."""
        out = []
        for ln, line in self.properties:
            for m in re.finditer(r'\[\s*Header\s*\((.*?)\)\s*\]', line):
                bad = sorted(set(c for c in m.group(1) if c in ':(),'))
                if bad:
                    what = 'a syntax error (the whole shader fails to import)' if ':' in bad else \
                        "a warning 'Failed to create material drawer Header' (the header is not drawn)"
                    out.append(('ERROR' if ':' in bad else 'WARN', ln, '[Header(%s)] contains %s: Unity gives %s. Use only letters, digits, '
                                'spaces, - and . in headers (CONTROL §6 item 2)' % (m.group(1), ' '.join("'%s'" % c for c in bad), what)))
            rest = re.sub(r'\[[^\]]*\]', '', line).strip()
            if rest and not self.PROP_RE.match(line):
                out.append(('WARN', ln, 'property line not recognised: %s' % line.strip()[:120]))
            for m in re.finditer(r'\[\s*KeywordEnum\s*\(([^)]*)\)\s*\]\s*(\w+)', line):
                for e in [x.strip() for x in m.group(1).split(',') if x.strip()]:
                    kw = ('%s_%s' % (m.group(2), e)).upper().replace(' ', '_')
                    if kw not in declared_keywords:
                        out.append(('WARN', ln, '[KeywordEnum] %s sets keyword %s, which no #pragma multi_compile / shader_feature declares (the option does nothing)' % (m.group(2), kw)))
            for m in re.finditer(r'\[\s*(Toggle|ToggleOff)\s*\(\s*(\w+)\s*\)\s*\]\s*(\w+)', line):
                if m.group(2) not in declared_keywords:
                    out.append(('WARN', ln, '[%s(%s)] %s: keyword %s is not declared by any #pragma' % (m.group(1), m.group(2), m.group(3), m.group(2))))
        for ln in self.ztest_always:
            if self.name not in ZTEST_ALWAYS_OK:
                out.append(('WARN', ln, 'ZTest Always: CONTROL §3 allows it only on the overlay / mask sphere and the poem subtitles (D-45 #10)'))
        return out
