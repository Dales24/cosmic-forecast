# Sampled ephemeris comparison

On 2026-09-20, `scripts.validate_ephemeris` compared the corrected local approximations
against JPL Horizons geometric geocentric ICRF vectors. Inputs and outputs used
UTC and distances in km. Each body was sampled on January, April, July and
October 2 in 1800, 1850, 1900, 1950, 2000, 2026 and 2050: 28 dates per body.
January 2 avoids the start boundary of Neptune's available body ephemeris.

| Body | Maximum sampled angular difference (degrees) |
| --- | ---: |
| Sun | 0.00634 |
| Moon | 0.00183 |
| Mercury | 0.00801 |
| Venus | 0.00701 |
| Mars | 0.01545 |
| Jupiter | 0.09504 |
| Saturn | 0.19106 |
| Uranus | 0.02563 |
| Neptune | 0.01440 |

The previous abbreviated lunar model peaked at 3.06225 degrees on the same
28 dates. ERFA Moon98 replaces it with the full series and rotation to GCRS.
The input is converted to TT: pre-1960 dates use historical UT and NASA's
Espenak/Meeus delta-T polynomial estimates; modern dates use ERFA's TAI-UTC
table plus 32.184 seconds. Future dates hold the last known leap-second offset,
without forecasting future leap seconds. Dates before 1800 are not validated.

A denser lunar-only check sampled January, April, July and October 2 of every
year from 1800 through 2050 (1,004 positions). Its maximum angular difference
was 0.003926 degrees (about 14.1 arcseconds). These are sampled differences,
not continuous error bounds or telescope-pointing validation.

Reproduce with:

```powershell
uv run python -m scripts.validate_ephemeris
```

For the dense lunar comparison in PowerShell:

```powershell
$sampleYears = 1800..2050
uv run python -m scripts.validate_ephemeris --years $sampleYears --bodies moon --output data/lunar-dense-validation.json
```

Reference requests are batched at 50 dates to keep Horizons date lists short.
Seven fixed Horizons vectors spanning the period are checked offline in tests.

The raw report at ignored `data/ephemeris-validation.json` includes reference
xyz coordinates, per-date angular/distance differences and retrieval time.
`--years` accepts alternate sample years; `--output` controls the report path.
Relative output paths resolve from the repository. Reference calls require
network access; the normal test suite uses offline fixtures.

Reference: [JPL Horizons API](https://ssd-api.jpl.nasa.gov/doc/horizons.html).
Algorithm: [ERFA Moon98](https://github.com/liberfa/erfa/blob/master/src/moon98.c).
Historical time: [NASA delta-T polynomials](https://eclipse.gsfc.nasa.gov/SEcat5/deltatpoly.html).
