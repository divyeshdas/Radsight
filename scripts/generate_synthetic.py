#!/usr/bin/env python3
"""
Generates synthetic radiology reports and ingests them into MongoDB.
Usage:
  python scripts/generate_synthetic.py --count 50000
  python scripts/generate_synthetic.py --count 1000 --spikes --seasonal
"""
import argparse
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datasets.generators.trend_generator import TrendGenerator
from datasets.generators.report_generator import SyntheticReportGenerator
from datasets.pipelines.validator import validate_batch, compute_dataset_stats
from datasets.pipelines.ingestion import ingest_reports
from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="Generate synthetic RadSight dataset")
    parser.add_argument("--count", type=int, default=10000, help="Number of reports to generate")
    parser.add_argument("--spikes", action="store_true", help="Include disease spike events")
    parser.add_argument("--seasonal", action="store_true", help="Include seasonal patterns")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--batch-size", type=int, default=500, help="MongoDB insertion batch size")
    parser.add_argument("--dry-run", action="store_true", help="Generate but do not insert into MongoDB")
    parser.add_argument("--stats-only", action="store_true", help="Print stats and exit")
    return parser.parse_args()


def progress(inserted: int, total: int) -> None:
    pct = inserted / max(total, 1) * 100
    bar = "=" * int(pct / 2) + ">" + " " * (50 - int(pct / 2))
    print(f"\r  [{bar}] {inserted:,}/{total:,} ({pct:.1f}%)", end="", flush=True)


async def main():
    args = parse_args()

    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri and not args.dry_run:
        print("Error: MONGODB_URI not set. Use --dry-run to skip insertion.")
        sys.exit(1)

    print(f"\nRadSight Synthetic Data Generator")
    print(f"  Count:    {args.count:,}")
    print(f"  Spikes:   {args.spikes}")
    print(f"  Seasonal: {args.seasonal}")
    print(f"  Seed:     {args.seed}")
    print(f"  Dry run:  {args.dry_run}\n")

    print("Generating reports...")
    if args.spikes or args.seasonal:
        gen = TrendGenerator(seed=args.seed)
        reports = gen.generate_full_simulation(
            total_reports=args.count,
            include_spikes=args.spikes,
            include_seasonal=args.seasonal,
        )
    else:
        gen = SyntheticReportGenerator(seed=args.seed)
        reports = gen.generate_batch(count=args.count)

    print(f"  Generated {len(reports):,} reports")

    print("\nValidating...")
    validation = validate_batch(reports)
    print(f"  Valid:    {validation['valid']:,} ({validation['pass_rate']}%)")
    print(f"  Invalid:  {validation['invalid']:,}")

    if args.stats_only or args.dry_run:
        stats = compute_dataset_stats(validation["valid_reports"])
        print("\nDataset Statistics:")
        print(f"  Severity distribution: {stats.get('severity_distribution')}")
        print(f"  Disease distribution:  {stats.get('disease_distribution')}")
        print(f"  Risk score mean:       {stats.get('risk_score_stats', {}).get('mean')}")
        print(f"  Critical cases:        {stats.get('critical_cases')}")
        print(f"  Flagged for review:    {stats.get('flagged_count')}")
        if args.dry_run:
            print("\nDry run complete — no data inserted.")
            return

    print(f"\nInserting into MongoDB ({args.batch_size} per batch)...")
    result = await ingest_reports(
        reports=validation["valid_reports"],
        mongodb_uri=mongodb_uri,
        preprocess=True,
        progress_callback=progress,
        batch_size=args.batch_size,
    )
    print()

    print("\nIngestion complete:")
    print(f"  Inserted:   {result['inserted']:,}")
    print(f"  Failed:     {result['failed']:,}")
    print(f"  Elapsed:    {result['elapsed_seconds']}s")
    print(f"  Throughput: {result['throughput_per_second']} reports/sec\n")


if __name__ == "__main__":
    asyncio.run(main())
