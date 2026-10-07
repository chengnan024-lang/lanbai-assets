"""numpy port of LanbaiLamps.cginc :: LanbaiLampSpecOne / LanbaiLampSpecular (Karis line + sphere light GGX).
Used to solve the still-water gain (bible §6·12 '静水里的灯影 #DDE8EA') and to check the puddle shading."""
import numpy as np


def nrm(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def dot(a, b):
    return (a * b).sum(-1)


def spec_one(lamp_pos, I, col, radius, axis, cone_dir, cone_cos, P, N, V, alpha, F0, boost=1.0, peak=1e9):
    toC = lamp_pos - P
    dist2 = np.maximum(dot(toC, toC), 1e-4)
    R = 2 * dot(N, V)[..., None] * N - V
    seg = 2 * np.asarray(axis, float)
    segLen2 = dot(seg, seg)
    Lvec = toC; lineNorm = 1.0
    if segLen2 > 1e-6:
        L0 = toC - axis
        RoS = dot(R, seg)
        t = np.clip((dot(R, L0) * RoS - dot(L0, seg)) / np.maximum(segLen2 - RoS * RoS, 1e-6), 0, 1)
        Lvec = L0 + seg * t[..., None]
        lineNorm = alpha / np.clip(alpha + 0.5 * np.sqrt(segLen2) / (2 * np.sqrt(dist2)), 0, 1)
    centerToRay = dot(Lvec, R)[..., None] * R - Lvec
    closest = Lvec + centerToRay * np.clip(radius / np.maximum(np.linalg.norm(centerToRay, axis=-1), 1e-5), 0, 1)[..., None]
    L = nrm(closest)
    dL = np.maximum(np.linalg.norm(Lvec, axis=-1), 1e-3)
    aP = np.clip(alpha + radius / (2 * dL), 0, 1)
    sphereNorm = (alpha / aP) ** 2
    NdotL = np.clip(dot(N, L), 0, 1)
    NdotV = np.maximum(dot(N, V), 1e-4)
    H = nrm(L + V)
    NdotH = np.clip(dot(N, H), 0, 1); VdotH = np.clip(dot(V, H), 0, 1)
    a2 = alpha * alpha
    d = NdotH * NdotH * (a2 - 1) + 1
    D = a2 / (np.pi * d * d + 1e-14)
    Vis = 0.5 / (NdotL * (NdotV * (1 - alpha) + alpha) + NdotV * (NdotL * (1 - alpha) + alpha) + 1e-5)
    F = F0 + (1 - F0) * (1 - VdotH) ** 5
    c = dot(nrm(-toC), np.asarray(cone_dir, float))
    cone = np.clip((c - (cone_cos - 0.08)) / 0.16, 0, 1); cone = cone * cone * (3 - 2 * cone)
    E = I / dist2 * cone
    common = E * NdotL * Vis * np.pi * sphereNorm * lineNorm
    Fc = F0 + (1 - F0) * (1 - NdotV) ** 5
    core = np.asarray(col)[None] * (common / (np.pi * a2) * Fc)[..., None]
    g = np.minimum(boost, peak / np.maximum(core.max(-1), 1e-6))
    return np.asarray(col)[None] * (common * D * F * g)[..., None] * (NdotL > 0)[..., None]
