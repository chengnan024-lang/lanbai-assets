"""Linear axisymmetric capillary-gravity ripples from a raindrop impact on a shallow puddle.

eta(r,t) = int_0^inf k F(k) J0(kr) cos(w(k) t) exp(-gamma(k) t) dk            (height)
d eta/dr = -int_0^inf k^2 F(k) J1(kr) cos(w(k) t) exp(-gamma(k) t) dk          (radial slope)

  w^2   = (g k + sigma/rho k^3) tanh(k h)                 dispersion, finite depth h
  gamma = 2 nu k^2 + k sqrt(nu w / 8)                     viscous + inextensible-film damping (dirty road water)
  F(k)  = Hankel transform of the initial crater  eta0(r) = -A exp(-r^2/a^2)  ->  -A a^2/2 exp(-k^2 a^2/4)
A Worthington-jet fallback (a second, smaller impulse at the same centre ~0.1 s later) is optional per drop.
All lengths in metres, time in seconds.
"""
import numpy as np
from scipy.special import j0, j1

G, SIGMA, RHO, NU = 9.81, 0.060, 1000.0, 1.0e-6     # sigma 0.060: road water carries surfactant


def omega(k, h):
    return np.sqrt((G * k + SIGMA / RHO * k ** 3) * np.tanh(k * h))


def gamma(k, h):
    w = omega(k, h)
    return 2 * NU * k ** 2 + k * np.sqrt(NU * w / 8.0)


class RadialSolver:
    def __init__(self, r_max=0.30, n_r=1200, k_max=2600.0, n_k=1400, depth=0.012):
        self.r = np.linspace(0, r_max, n_r)
        self.k = np.linspace(k_max / n_k, k_max, n_k)
        self.dk = self.k[1] - self.k[0]
        self.depth = depth
        kr = np.outer(self.r, self.k)
        self.J0 = j0(kr)
        self.J1 = j1(kr)
        self.w = omega(self.k, depth)
        self.g = gamma(self.k, depth)

    def spectrum(self, a):
        return -0.5 * a * a * np.exp(-(self.k * a) ** 2 / 4.0)

    def profile(self, a, amp, age, second=None, kc=None):
        """returns (height, slope) on self.r for one drop at the given age (s). second = (delay, a2, amp2 relative to amp).
        kc (rad/m): optional Gaussian low-pass exp(-(k/kc)^2) - the rings as a coarse pixel footprint can show them."""
        h = np.zeros_like(self.r); s = np.zeros_like(self.r)
        for (t, aa, A) in [(age, a, amp)] + ([(age - second[0], second[1], amp * second[2])] if second else []):
            if t < 0:
                continue
            F = A * self.spectrum(aa)
            if kc:
                F = F * np.exp(-(self.k / kc) ** 2)
            tw = np.cos(self.w * t) * np.exp(-self.g * t) * self.dk
            h += self.J0 @ (self.k * F * tw)
            s += -(self.J1 @ (self.k ** 2 * F * tw))
        return h, s
