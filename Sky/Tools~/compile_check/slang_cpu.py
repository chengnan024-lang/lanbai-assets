"""Run real shader functions on the CPU (slangpy, CPU device): build one compute kernel around a body of HLSL and
dispatch it over N items. Used by the equivalence checks and the reference renders, so the numbers come from the
SAME code Unity compiles (through the Unity stub in unity_stub.slang)."""
import os, re, tempfile
import numpy as np
import slangpy as spy

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(tempfile.gettempdir(), 'lanbai_slang_cpu'); os.makedirs(OUT, exist_ok=True)
_dev = None


def device():
    global _dev
    if _dev is None:
        _dev = spy.create_device(type=spy.DeviceType.cpu)
    return _dev


def read(rel):
    return open(os.path.join(REPO, rel)).read()


def stub(static_camera=True):
    s = open(os.path.join(HERE, 'unity_stub.slang')).read()
    if static_camera:
        s = s.replace('float3 _WorldSpaceCameraPos;', 'static float3 _WorldSpaceCameraPos;')
    return s


def strip_includes(text):
    return re.sub(r'#include\s+"[^"]+"', '', text)


def run(prelude, body, n, inputs, outputs, name='k'):
    """prelude: HLSL source (functions). body: statements inside the kernel, item index 'id'.
    inputs: {name: (array float32 shape (n, c)), ...} -> StructuredBuffer<floatC> name.
    outputs: {name: c} -> RWStructuredBuffer<floatC> name. Returns {name: array (n, c)}."""
    dev = device()
    decl = []
    for k, a in inputs.items():
        c = a.shape[1] if a.ndim == 2 else 1
        decl.append('StructuredBuffer<%s> %s;' % ('float' if c == 1 else 'float%d' % c, k))
    for k, c in outputs.items():
        decl.append('RWStructuredBuffer<%s> %s;' % ('float' if c == 1 else 'float%d' % c, k))
    src = prelude + '\n' + '\n'.join(decl) + '\nuniform uint LB_N;\n[shader("compute")]\n[numthreads(64,1,1)]\nvoid cs_kernel(uint3 tid : SV_DispatchThreadID)\n{\n uint id = tid.x; if (id >= LB_N) return;\n' + body + '\n}\n'
    fn = os.path.join(OUT, name + '.slang')
    open(fn, 'w').write(src)
    k = dev.create_compute_kernel(dev.load_program(fn, ['cs_kernel']))
    vars = {'LB_N': n}
    bufs = {}
    for kname, a in inputs.items():
        a = np.ascontiguousarray(a, np.float32)
        c = a.shape[1] if a.ndim == 2 else 1
        vars[kname] = dev.create_buffer(element_count=n, struct_size=4 * c, usage=spy.BufferUsage.shader_resource, data=a)
    for kname, c in outputs.items():
        bufs[kname] = dev.create_buffer(element_count=n, struct_size=4 * c, usage=spy.BufferUsage.unordered_access)
        vars[kname] = bufs[kname]
    k.dispatch(thread_count=[n, 1, 1], vars=vars)
    return {kname: b.to_numpy().view(np.float32).reshape(n, c) for (kname, b), c in zip(bufs.items(), outputs.values())}
