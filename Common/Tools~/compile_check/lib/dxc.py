"""Minimal ctypes driver for Microsoft's DirectX Shader Compiler (libdxcompiler.so, IDxcCompiler3::Compile).

Why DXC: it is a real HLSL compiler with the same C-like rules Unity's d3d11 compiler (FXC) enforces and slang does not
(declare before use, every path returns, entry-point semantics, ...). Unity itself can compile built-in-pipeline shaders
with DXC (#pragma use_dxc); its CGIncludes carry a UNITY_COMPILER_DXC path (sampler2D / tex2D emulation) for that.
It is still NOT FXC: FXC-only diagnostics (e.g. X4008 'floating point division by zero' after constant folding) are not
reproduced, and DXC is stricter in a few corners. Treat a DXC error as 'very likely a Unity error too'.

The library comes from the NuGet package Vortice.Dxc.Native (built from github.com/microsoft/DirectXShaderCompiler);
setup.sh pins the version and records the vtable layout it probed (see VTABLE_BASE) in env.json.
"""
import ctypes as C
import uuid

# IUnknown slots before an interface's own methods. 3 for this build (QueryInterface, AddRef, Release); older Linux DXC
# builds declared a virtual destructor on IUnknown, which adds 2 Itanium-ABI slots (-> 5). setup.sh probes it.
VTABLE_BASE = 3


class _GUID(C.Structure):
    _fields_ = [('d1', C.c_uint32), ('d2', C.c_uint16), ('d3', C.c_uint16), ('d4', C.c_ubyte * 8)]


def _guid(s):
    b = uuid.UUID(s).bytes
    g = _GUID()
    g.d1, g.d2, g.d3 = int.from_bytes(b[0:4], 'big'), int.from_bytes(b[4:6], 'big'), int.from_bytes(b[6:8], 'big')
    for i in range(8):
        g.d4[i] = b[8 + i]
    return g


class _DxcBuffer(C.Structure):
    _fields_ = [('Ptr', C.c_void_p), ('Size', C.c_size_t), ('Encoding', C.c_uint32)]


CLSID_DxcCompiler = _guid('73e22d93-e6ce-47f3-b5bf-f0664f39c1b0')
IID_IDxcCompiler3 = _guid('228b4687-5a6a-4730-900c-9702b2203f54')
IID_IDxcResult = _guid('58346cda-dde7-4497-9461-6f87af5e0659')


class Dxc:
    def __init__(self, libpath, base=None):
        self.base = VTABLE_BASE if base is None else int(base)
        self.lib = C.CDLL(libpath)
        self.lib.DxcCreateInstance.argtypes = [C.POINTER(_GUID), C.POINTER(_GUID), C.POINTER(C.c_void_p)]
        self.lib.DxcCreateInstance.restype = C.c_int32
        self.comp = C.c_void_p()
        hr = self.lib.DxcCreateInstance(C.byref(CLSID_DxcCompiler), C.byref(IID_IDxcCompiler3), C.byref(self.comp))
        if hr != 0 or not self.comp.value:
            raise RuntimeError('DxcCreateInstance failed: 0x%08x' % (hr & 0xffffffff))

    def _method(self, obj, idx, restype, *argtypes):
        vtbl = C.cast(obj, C.POINTER(C.POINTER(C.c_void_p))).contents
        f = C.CFUNCTYPE(restype, C.c_void_p, *argtypes)(vtbl[self.base + idx])
        return lambda *a: f(obj, *a)

    def _release(self, obj):
        if obj:
            self._method(obj, -1, C.c_uint32)()          # Release is the slot right before the interface methods

    def compile(self, source, args):
        """source: str (UTF-8); args: list of dxc command-line arguments. Returns (ok, diagnostics_text)."""
        data = source.encode('utf-8')
        buf = C.create_string_buffer(data, len(data))
        db = _DxcBuffer(C.cast(buf, C.c_void_p), len(data), 65001)   # DXC_CP_UTF8
        argv = (C.c_wchar_p * len(args))(*args)
        res = C.c_void_p()
        compile_ = self._method(self.comp, 0, C.c_int32, C.POINTER(_DxcBuffer), C.POINTER(C.c_wchar_p), C.c_uint32,
                                C.c_void_p, C.POINTER(_GUID), C.POINTER(C.c_void_p))
        hr = compile_(C.byref(db), argv, len(args), None, C.byref(IID_IDxcResult), C.byref(res))
        if hr != 0 or not res.value:
            return False, 'IDxcCompiler3::Compile failed: 0x%08x' % (hr & 0xffffffff)
        try:
            status = C.c_int32()
            self._method(res, 0, C.c_int32, C.POINTER(C.c_int32))(C.byref(status))          # GetStatus
            eb = C.c_void_p()
            self._method(res, 2, C.c_int32, C.POINTER(C.c_void_p))(C.byref(eb))             # GetErrorBuffer
            text = ''
            if eb.value:
                p = self._method(eb, 0, C.c_void_p)()                                         # GetBufferPointer
                n = self._method(eb, 1, C.c_size_t)()                                         # GetBufferSize
                text = C.string_at(p, n).decode('utf-8', 'replace').rstrip('\x00') if p and n else ''
                self._release(eb)
            return status.value == 0, text
        finally:
            self._release(res)


SELFTEST_SRC = 'float f() { return _Late * 2; }\nfloat _Late;\nfloat4 main() : SV_Target { return f(); }\n'


def selftest(libpath, base):
    """True if this library + vtable layout reports the declare-before-use error it must report."""
    ok, text = Dxc(libpath, base).compile(SELFTEST_SRC, ['-T', 'ps_6_0', '-E', 'main', '-HV', '2018', '-Vd'])
    return (not ok) and "undeclared identifier '_Late'" in text


if __name__ == '__main__':
    import sys
    print('ok' if selftest(sys.argv[1], int(sys.argv[2])) else 'bad')
