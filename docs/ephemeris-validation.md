# Sampled ephemeris comparison

On 2026-09-19, `scripts.validate_ephemeris` compared the local approximations
against JPL Horizons geometric geocentric ICRF vectors. Inputs and outputs used
UTC and distances in km. Each body was sampled on January, April, July and
October 2 in 1800, 1850, 1900, 1950, 2000, 2026 and 2050: 28 dates per body.
January 2 avoids the start boundary of Neptune's available body ephemeris.

| Body | Maximum sampled angular difference (degrees) |
| --- | ---: |
| Sun | 0.00634 |
| Moon | 3.06225 |
| Mercury | 0.00801 |
| Venus | 0.00701 |
| Mars | 0.01545 |
| Jupiter | 0.09504 |
| Saturn | 0.19106 |
| Uranus | 0.02563 |
| Neptune | 0.01440 |

These are sampled differences, not continuous error bounds. The abbreviated
Moon model needs further work, including frame/time treatment, before making
accuracy claims. No telescope-pointing accuracy is established. The previous
blanket arc-minute claim has been removed.

Reproduce with:

```powershell
uv run python -m scripts.validate_ephemeris
```

The raw report at ignored `data/ephemeris-validation.json` includes reference
xyz coordinates, per-date angular/distance differences and retrieval time.
`--years` accepts alternate sample years; `--output` controls the report path.
Relative output paths resolve from the repository. Reference calls require
network access; the normal test suite uses offline fixtures.

Reference: [JPL Horizons API](https://ssd-api.jpl.nasa.gov/doc/horizons.html).
