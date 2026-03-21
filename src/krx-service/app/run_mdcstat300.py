from __future__ import annotations

import argparse
import json
from pathlib import Path

from .mdcstat300 import fetch_mdcstat300


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch KRX MDCSTAT300 data via internal JSON endpoint"
    )
    parser.add_argument("--isu-cd", required=True, help="KRX issue code, e.g. 033640")
    parser.add_argument("--start", required=True, help="Start date: YYYYMMDD or YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date: YYYYMMDD or YYYY-MM-DD")
    parser.add_argument(
        "--bld",
        required=True,
        help="KRX internal bld id (capture via browser Network tab)",
    )
    parser.add_argument("--screen-id", default="MDCSTAT300", help="KRX screen id")
    parser.add_argument(
        "--extra-json",
        default="{}",
        help="Extra payload JSON string, e.g. '{\"mktId\":\"STK\"}'",
    )
    parser.add_argument("--out-csv", default="", help="Optional CSV output path")
    parser.add_argument("--out-json", default="", help="Optional raw JSON output path")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        extra_payload = json.loads(args.extra_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid --extra-json: {exc}") from exc

    if not isinstance(extra_payload, dict):
        raise SystemExit("--extra-json must decode to a JSON object")

    df, raw = fetch_mdcstat300(
        isu_cd=args.isu_cd,
        start_date=args.start,
        end_date=args.end,
        bld=args.bld,
        screen_id=args.screen_id,
        extra_payload=extra_payload,
    )

    print(f"rows={len(df)} cols={len(df.columns)}")
    if not df.empty:
        print(df.head(5).to_string(index=False))

    if args.out_csv:
        out_csv = Path(args.out_csv)
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_csv, index=False, encoding="utf-8-sig")
        print(f"saved csv: {out_csv}")

    if args.out_json:
        out_json = Path(args.out_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"saved raw json: {out_json}")


if __name__ == "__main__":
    main()
