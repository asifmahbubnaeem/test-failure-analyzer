# Test Failure Analyzer

An AI agent that reads a failed CI run and says **why** it failed: a bug in the product, a bug in
the test, a flaky test, a broken environment, or a CI infrastructure problem. Every version is
scored against labelled failures before it ships.

**Status: week 1 of 6.** The eval harness and a one-prompt baseline exist; the agent doesn't yet.
The plan is to beat the baseline step by step, with numbers published here.

## How it is measured

The failures come from [tfa-failure-lab](https://github.com/asifmahbubnaeem/tfa-failure-lab), a
small shop with an end-to-end suite and switches that break it on purpose. Because each failure is
caused on purpose, its label is known for certain. The current set has 25 failed CI runs from 12
scenarios:

| Category | Cases | Example |
| --- | --- | --- |
| product_bug | 9 | Tax truncated but total rounded, so item + tax ≠ total |
| test_bug | 8 | A locator that no longer exists; a typo in test data |
| flaky | 4 | The cart API returns HTTP 500 on some calls |
| environment | 4 | Database unreachable; a missing config value |

The analyzer sees only what a CI run produces (JUnit report, test log, application log), never
the label. Several cases are deliberately hard: four different root causes all surface as a
Playwright timeout.

Two scores are reported: plain accuracy, and accuracy with each scenario counted once (so
repeated identical failures don't inflate the number).

## Results

| Version | Accuracy | Each scenario once | Notes |
| --- | --- | --- | --- |
| Majority guess (always `product_bug`) | 36% | 33% | The floor |
| One-prompt baseline, qwen3:8b | 56% | 54% | Environment 4/4; misses need test source or a rerun (see below) |

Full reports, including every answer, are in `evals/results/`.

What the baseline gets wrong is mostly information a single run doesn't contain:

- **Is it intermittent?** Cart API errors were called product bugs; a missing validation message and a wrong locator were called flaky. All three need to know whether the failure repeats on a rerun.
- **What does the test actually check?** A test asserting A-to-Z order after sorting Z-to-A was blamed on the app, and a correct "item should be gone" check was blamed on the test. Both need the test's source code.

Those two gaps decide the agent's first tools.

## Run it

Python 3.11+, standard library only. The baseline needs [Ollama](https://ollama.com) with
`qwen3:8b`.

```sh
git clone https://github.com/asifmahbubnaeem/tfa-failure-lab ../tfa-failure-lab

python3 evals/run_eval.py --cases ../tfa-failure-lab/cases --predictor majority
python3 evals/run_eval.py --cases ../tfa-failure-lab/cases --predictor baseline --model qwen3:8b

python3 -m unittest discover -s tests -t .
```

## Layout

| Path | What |
| --- | --- |
| `tfa/parsers/` | JUnit reader; log summaries (exception lines, HTTP status counts) |
| `tfa/case.py` | Loads a case's files, never its label |
| `tfa/schema.py` | Failure categories and the verdict the model must return |
| `tfa/baseline.py` | One prompt, no tools |
| `evals/` | Runs a predictor over labelled cases and writes accuracy, per-category scores and a confusion matrix |
