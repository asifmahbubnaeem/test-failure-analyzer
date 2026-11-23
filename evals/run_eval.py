#!/usr/bin/env python3
"""Score an analyzer against labelled cases.

    python3 evals/run_eval.py --cases ../tfa-failure-lab/cases --predictor majority
    python3 evals/run_eval.py --cases ../tfa-failure-lab/cases --predictor baseline --model qwen3:8b

Writes evals/results/<time>-<predictor>.json (every answer) and .md (the summary) and prints the
summary. Labels are read here, and only here: the predictors get the case files, never the label.
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals import metrics  # noqa: E402
from tfa import baseline, case as case_mod  # noqa: E402
from tfa.llm import Ollama  # noqa: E402
from tfa.schema import InvalidVerdict  # noqa: E402


def load_labels(cases_dir: Path) -> dict[str, dict]:
    return {p.parent.name: json.loads(p.read_text()) for p in sorted(cases_dir.glob("*/label.json"))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", required=True, help="folder of case folders (each with label.json)")
    ap.add_argument("--predictor", choices=["majority", "baseline"], required=True)
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--ollama-url", default="http://localhost:11434")
    ap.add_argument("--only", help="comma-separated case ids")
    ap.add_argument("--out", default=str(ROOT / "evals" / "results"))
    args = ap.parse_args()

    cases_dir = Path(args.cases)
    labels = load_labels(cases_dir)
    if args.only:
        labels = {k: v for k, v in labels.items() if k in args.only.split(",")}
    if not labels:
        print(f"No labelled cases found in {cases_dir}", file=sys.stderr)
        return 1

    majority = Counter(v["category"] for v in labels.values()).most_common(1)[0][0]
    client = Ollama(args.model, args.ollama_url)
    rows = []
    started = time.time()
    for i, (case_id, label) in enumerate(labels.items(), 1):
        row = {"case_id": case_id, "scenario": label["scenario"], "expected": label["category"]}
        if args.predictor == "majority":
            row["predicted"] = majority
        else:
            try:
                verdict, usage = baseline.classify(case_mod.load(cases_dir / case_id), client)
                row.update(predicted=verdict.category, verdict=verdict.to_dict(), usage=usage)
            except (InvalidVerdict, RuntimeError) as e:
                row.update(predicted=metrics.ERROR, error=str(e))
        rows.append(row)
        mark = "ok " if row["expected"] == row["predicted"] else "MISS"
        took = f" {row['usage']['seconds']:.0f}s" if "usage" in row else ""
        print(f"[{i:>2}/{len(labels)}] {mark} {case_id} expected={row['expected']:<12} got={row['predicted']}{took}", flush=True)

    pairs = [(r["expected"], r["predicted"]) for r in rows]
    used = [r["usage"] for r in rows if "usage" in r]
    summary = {
        "predictor": args.predictor,
        "model": args.model if args.predictor != "majority" else None,
        "cases": len(rows),
        "scenarios": len({r["scenario"] for r in rows}),
        "accuracy": round(metrics.accuracy(pairs), 3),
        "scenario_weighted_accuracy": round(metrics.scenario_weighted_accuracy(rows), 3),
        "no_answer": sum(r["predicted"] == metrics.ERROR for r in rows),
        "per_category": metrics.per_category(pairs),
        "seconds_total": round(time.time() - started, 1),
        "seconds_per_case": round(sum(u["seconds"] for u in used) / len(used), 1) if used else None,
        "prompt_tokens_per_case": round(sum(u["prompt_tokens"] for u in used) / len(used)) if used else None,
    }

    name = f"{time.strftime('%Y%m%d-%H%M%S')}-{args.predictor}"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2) + "\n")
    md = [
        f"# {args.predictor}" + (f" ({args.model})" if summary["model"] else ""),
        "",
        f"- Cases: {summary['cases']} from {summary['scenarios']} scenarios",
        f"- Accuracy: {summary['accuracy']:.0%} (each scenario counted once: {summary['scenario_weighted_accuracy']:.0%})",
        f"- No valid answer: {summary['no_answer']}",
    ]
    if used:
        md.append(f"- Per case: {summary['seconds_per_case']} s, {summary['prompt_tokens_per_case']} prompt tokens")
    md += ["", "| Category | Cases | Precision | Recall |", "| --- | --- | --- | --- |"]
    for c, s in summary["per_category"].items():
        md.append(f"| {c} | {s['support']} | {s['precision']:.0%} | {s['recall']:.0%} |")
    md += ["", "Confusion matrix (rows: true category):", "", metrics.confusion_table(pairs), ""]
    misses = [r for r in rows if r["expected"] != r["predicted"]]
    if misses:
        md += ["Misses:", ""] + [
            f"- {r['case_id']} ({r['scenario']}): expected {r['expected']}, got {r['predicted']}"
            + (f": {r['verdict']['root_cause']}" if "verdict" in r else f": {r.get('error', '')}")
            for r in misses
        ]
    (out / f"{name}.md").write_text("\n".join(md) + "\n")
    print("\n" + "\n".join(md))
    print(f"Saved: {out / name}.json and .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
