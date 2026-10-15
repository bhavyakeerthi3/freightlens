# 10-minute walkthrough

## 0:00-1:00 - Problem and result

Open the README. Explain that the assistant identifies rising route costs and distinguishes evidence-supported changes from unexplained ones. The full dataset has 2,940 shipments and 728 route-weeks; the configured policy produces 11 unexplained alerts and 2 justified candidate rises.

## 1:00-3:00 - Correct arithmetic

Show `aggregate` and `analyze` in assistant.py. Explain Monday-Sunday grouping, sum of costs divided by sum of tonne-km, eight prior calendar weeks with no current-week leakage, and equal-weight other-route peer means. Open audit.json to show actual unrounded baselines. Explain why the prior-week rise condition and 20% threshold are policy choices rather than grading definitions.

## 3:00-5:00 - Live demo

Run `python demo.py` and open http://127.0.0.1:8000. Show the overview metrics and Mumbai-Pune trend against history and peers. Filter evidence-supported findings, then inspect Chennai-Bangalore's flood note and numeric baselines. Ask 'Why did Chennai-Bangalore get pricier in March 2025?' to show the expired flood note is not reused. Visit the Evidence library, then export the full CSV. Explain the question parser supports explicit routes and periods without general LLM reasoning.

## 5:00-7:00 - Trust and retrieval

Show context_notes.csv, reviewed_evidence.json, and NoteIndex. Explain TF-IDF cosine vectors, eligibility before ranking, and why a normal-conditions note never justifies a rise. Contrast the flood's expiry with later recovery. Show why the fuel note's 7% ceiling does not excuse a large spike. Discuss weekly overlap and unquantified-event limitations candidly.

## 7:00-8:30 - Verification

Run `python verify.py`. Show evaluation.txt and reproducibility.json. Explain the independent CLI processes and byte hashes. Highlight tests for the wrong-route note, expired event, no-impact statement, weighted rate, peer exclusion, and future-data isolation. Clarify these are implementation/evidence tests, not an independently labeled business-accuracy benchmark.

## 8:30-9:00 - Cost

Open cost_log.json: zero LLM calls, input tokens, output tokens and API cost. Explain why template generation and a small local index are sufficient for this supplied corpus. Do not claim an open-source language model was used.

## 9:00-10:00 - Trade-offs and next steps

Discuss threshold sensitivity, plateau/gradual-rise misses, manual evidence annotations, coarse weekly overlap, and quadratic scans. Next steps: historical threshold calibration, human feedback, structured evidence review, faster rolling computations, and optional LLM wording that cannot change numeric decisions or citations. Invite questions on baseline definitions and grounding boundaries.
