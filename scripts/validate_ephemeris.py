"""Compare approximate positions with JPL Horizons; save sampled errors, not an accuracy guarantee."""

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app import ephemeris
from app.horizons import fetch_vectors
from app.paths import PROJECT_ROOT

BODIES = {
    "sun": "10",
    "moon": "301",
    "mercury": "199",
    "venus": "299",
    "mars": "499",
    "jupiter": "599",
    "saturn": "699",
    "uranus": "799",
    "neptune": "899",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=[1800, 1850, 1900, 1950, 2000, 2026, 2050],
    )
    parser.add_argument(
        "--output", type=Path, default=PROJECT_ROOT / "data/ephemeris-validation.json"
    )
    args = parser.parse_args()
    dates = [
        datetime(year, month, 2, tzinfo=timezone.utc)
        for year in sorted(set(args.years))
        for month in (1, 4, 7, 10)
    ]
    report = {
        "reference": "JPL Horizons geometric geocentric ICRF, UTC input, km",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Sampled comparisons only; not a continuous error bound or telescope-pointing validation",
        "bodies": {},
    }
    for body, command in BODIES.items():
        vectors = fetch_vectors(command, dates)
        samples = []
        for date, vector in zip(dates, vectors):
            if body in ("sun", "moon"):
                ra, dec, distance = getattr(ephemeris, body + "_geocentric")(date)
            else:
                ra, dec, distance = ephemeris.planet_geocentric(body, date)
            unit = np.array(
                [
                    math.cos(dec) * math.cos(ra),
                    math.cos(dec) * math.sin(ra),
                    math.sin(dec),
                ]
            )
            reference_distance = np.linalg.norm(vector[:3])
            angle = math.degrees(
                math.acos(np.clip(np.dot(unit, vector[:3] / reference_distance), -1, 1))
            )
            samples.append(
                {
                    "utc": date.isoformat(),
                    "angular_error_deg": angle,
                    "distance_error_km": float(abs(distance - reference_distance)),
                    "reference_xyz_km": vector[:3].tolist(),
                }
            )
        report["bodies"][body] = {
            "max_angular_error_deg": max(s["angular_error_deg"] for s in samples),
            "samples": samples,
        }
        print(body, report["bodies"][body]["max_angular_error_deg"], flush=True)
    output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
