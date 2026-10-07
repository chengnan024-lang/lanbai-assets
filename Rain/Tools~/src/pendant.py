"""Young-Laplace pendant drop (axisymmetric), hanging from a lip of radius r_lip.
z downward from the apex; s = arc length from the apex; phi = tangent angle.
    dx/ds = cos(phi), dz/ds = sin(phi), dphi/ds = 2/b - z/lc^2 - sin(phi)/x    (z measured UP from apex -> sign)
For a pendant drop the apex is the lowest point; with z measured upward from the apex the hydrostatic term is -z/lc^2
(pressure falls with height)."""
import numpy as np

SIGMA, RHO, G = 0.072, 1000.0, 9.81
LC = np.sqrt(SIGMA / (RHO * G))


def profile(b, r_lip, ds=2e-6, smax=0.03):
    """integrate from the apex (x=0, z=0) upward; stop when x returns to r_lip above the equator. returns x(z) arrays."""
    x, z, phi = 1e-9, 0.0, 0.0
    xs, zs = [0.0], [0.0]
    passed_eq = False
    s = 0.0
    while s < smax:
        if x < 1e-7:
            dphi = 1.0 / b                    # near apex: sin(phi)/x -> dphi/ds, so dphi/ds = 1/b
        else:
            dphi = 2.0 / b - z / LC ** 2 - np.sin(phi) / x
        # midpoint RK2
        xm = x + 0.5 * ds * np.cos(phi); zm = z + 0.5 * ds * np.sin(phi); pm = phi + 0.5 * ds * dphi
        dphim = (2.0 / b - zm / LC ** 2 - np.sin(pm) / max(xm, 1e-9)) if xm > 1e-7 else 1.0 / b
        x += ds * np.cos(pm); z += ds * np.sin(pm); phi += ds * dphim; s += ds
        xs.append(x); zs.append(z)
        if phi > np.pi / 2:
            passed_eq = True
        if passed_eq and x <= r_lip:
            return np.array(xs), np.array(zs), True
        if x < 0 or phi > 2.8 * np.pi / 2 + 1.0:
            break
    return np.array(xs), np.array(zs), False


def volume(xs, zs):
    return float(np.sum(np.pi * 0.5 * (xs[1:] ** 2 + xs[:-1] ** 2) * np.abs(np.diff(zs))))


def family(r_lip, n=400):
    out = []
    for b in np.geomspace(0.8e-3, 12e-3, n):
        xs, zs, ok = profile(b, r_lip)
        if ok:
            out.append((b, volume(xs, zs), xs, zs))
    return out
