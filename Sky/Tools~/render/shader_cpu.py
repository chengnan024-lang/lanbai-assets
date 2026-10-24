"""Run the Lanbai shader includes on the CPU (slangpy CPU device) with textures emulated by buffers, so the cloud
reference renders use the SAME code Unity compiles. Textures: sampler2D / samplerCUBE become handles {id}; every
texture is an equirect / 2D float4 buffer with manual bilinear filtering (u wraps, v clamps).
samplerCUBE handles sample a lat-long image with UNITY's lat-long import convention (Skybox/Panoramic, the cubemap
importer's 'Latitude-Longitude Layout'): u = 0.5 - atan2(z, x) / 2pi, v = 1 - acos(y) / pi, v = 1 = top row of the
file. texCUBElod with lod >= 1.5 reads the texture's blurred copy (id + 1)."""
import os, re, sys
import numpy as np
import slangpy as spy

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(HERE, '..', 'compile_check'))
from slang_cpu import device, OUT, read, strip_includes   # noqa: E402

MAXTEX = 8
TEX_PRELUDE = '''
struct LBTex { int id; };
#define sampler2D LBTex
#define samplerCUBE LBTex
''' + ''.join('StructuredBuffer<float4> LB_T%d; uniform int2 LB_D%d;\n' % (i, i) for i in range(MAXTEX)) + '''
float4 LB_Fetch(int id, int x, int y)
{
''' + ''.join('    if (id == %d) { x = (x %% LB_D%d.x + LB_D%d.x) %% LB_D%d.x; y = clamp(y, 0, LB_D%d.y - 1); return LB_T%d[y * LB_D%d.x + x]; }\n' % ((i,) * 7) for i in range(MAXTEX)) + '''    return float4(0, 0, 0, 0);
}
int2 LB_Dim(int id)
{
''' + ''.join('    if (id == %d) return LB_D%d;\n' % (i, i) for i in range(MAXTEX)) + '''    return int2(1, 1);
}
float4 LB_Sample(int id, float2 uv)       // uv: v = 1 is the TOP row of the stored image (row 0)
{
    if (id < 0) return float4(0, 0, 0, 0);
    int2 d = LB_Dim(id);
    float x = uv.x * d.x - 0.5, y = (1.0 - uv.y) * d.y - 0.5;
    int x0 = (int)floor(x), y0 = (int)floor(y);
    float fx = x - x0, fy = y - y0;
    return lerp(lerp(LB_Fetch(id, x0, y0), LB_Fetch(id, x0 + 1, y0), fx), lerp(LB_Fetch(id, x0, y0 + 1), LB_Fetch(id, x0 + 1, y0 + 1), fx), fy);
}
float2 LB_LatLong(float3 d)
{
    d = normalize(d);
    return float2(0.5 - atan2(d.z, d.x) / (2.0 * 3.14159265), 1.0 - acos(clamp(d.y, -1.0, 1.0)) / 3.14159265);
}
float4 tex2D(LBTex s, float2 uv) { return LB_Sample(s.id, uv); }
float4 tex2Dlod(LBTex s, float4 uv) { return LB_Sample(s.id, uv.xy); }
float4 texCUBE(LBTex s, float3 d) { return LB_Sample(s.id, LB_LatLong(d)); }
float4 texCUBElod(LBTex s, float4 d) { return LB_Sample(d.w >= 1.5 && s.id >= 0 ? s.id + 1 : s.id, LB_LatLong(d.xyz)); }
'''


def cpu_stub():
    s = open(os.path.join(REPO, 'Sky', 'Tools~', 'compile_check', 'unity_stub.slang')).read()
    # drop the texture-object versions of the samplers / tex functions; TEX_PRELUDE replaces them
    drop = ('struct sampler2D', 'struct samplerCUBE', 'float4 tex2D(', 'float4 tex2Dlod(', 'float4 tex2Dgrad(', 'float4 texCUBE(',
            'float4 texCUBElod(', 'float4 texCUBEbias(', 'float4 tex2Dbias(')
    s = '\n'.join(l for l in s.split('\n') if not l.strip().startswith(drop))
    return TEX_PRELUDE + s


def blur_equirect(img, sigma_px):
    from scipy import ndimage
    out = ndimage.gaussian_filter1d(img, sigma_px, axis=0, mode='nearest')
    return ndimage.gaussian_filter1d(out, sigma_px, axis=1, mode='wrap')


class Renderer:
    """prelude = HLSL (stub + includes + extra), body uses V[id] (unit dir) and writes OUT[id]."""
    def __init__(self, prelude, body, name):
        self.dev = device()
        src = prelude + '\nStructuredBuffer<float3> V;\nRWStructuredBuffer<float3> OUTC;\nuniform uint LB_N;\n' \
            '[shader("compute")]\n[numthreads(64,1,1)]\nvoid cs_kernel(uint3 tid : SV_DispatchThreadID)\n{ uint id = tid.x; if (id >= LB_N) return;\n' + body + '\n}\n'
        fn = os.path.join(OUT, name + '.slang')
        open(fn, 'w').write(src)
        self.kernel = self.dev.create_compute_kernel(self.dev.load_program(fn, ['cs_kernel']))
        self.tex = {}

    def set_texture(self, slot, img):
        img = np.ascontiguousarray(img, np.float32)
        if img.shape[2] == 3:
            img = np.concatenate([img, np.ones(img.shape[:2] + (1,), np.float32)], 2)
        self.tex[slot] = img

    def run(self, dirs, uniforms):
        n = dirs.shape[0]
        vars = {'LB_N': n}
        for i in range(MAXTEX):
            img = self.tex.get(i, np.zeros((1, 1, 4), np.float32))
            vars['LB_T%d' % i] = self.dev.create_buffer(element_count=img.shape[0] * img.shape[1], struct_size=16,
                                                       usage=spy.BufferUsage.shader_resource, data=img.reshape(-1, 4))
            vars['LB_D%d' % i] = spy.int2(img.shape[1], img.shape[0])
        for k, v in uniforms.items():
            if isinstance(v, dict):
                vars[k] = v
            elif np.ndim(v) == 0:
                vars[k] = float(v)
            else:
                v = list(map(float, np.ravel(v)))
                if len(v) == 16:
                    vars[k] = spy.float4x4(v)
                else:
                    vars[k] = {2: spy.float2, 3: spy.float3, 4: spy.float4}[len(v)](*v)
        vars['V'] = self.dev.create_buffer(element_count=n, struct_size=12, usage=spy.BufferUsage.shader_resource,
                                           data=np.ascontiguousarray(dirs, np.float32))
        ob = self.dev.create_buffer(element_count=n, struct_size=12, usage=spy.BufferUsage.unordered_access)
        vars['OUTC'] = ob
        self.kernel.dispatch(thread_count=[n, 1, 1], vars=vars)
        return ob.to_numpy().view(np.float32).reshape(n, 3)


def camera_dirs(w, h, hfov_deg, yaw_deg, pitch_deg):
    """Unity camera: yaw = azimuth clockwise from +Z, pitch up positive; returns (h*w, 3) unit dirs, row 0 = top."""
    t = np.tan(np.radians(hfov_deg) / 2)
    xs = (np.arange(w) + 0.5) / w * 2 - 1
    ys = 1 - (np.arange(h) + 0.5) / h * 2
    X, Y = np.meshgrid(xs * t, ys * t * h / w)
    d = np.stack([X, Y, np.ones_like(X)], -1)
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    p, yw = np.radians(pitch_deg), np.radians(yaw_deg)
    Rx = np.array([[1, 0, 0], [0, np.cos(p), np.sin(p)], [0, -np.sin(p), np.cos(p)]])
    Ry = np.array([[np.cos(yw), 0, np.sin(yw)], [0, 1, 0], [-np.sin(yw), 0, np.cos(yw)]])
    d = d @ Rx.T @ Ry.T
    return d.reshape(-1, 3)
