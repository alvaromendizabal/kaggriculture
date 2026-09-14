# Reviewed notebook-09 result

## Bottom line

The corrected notebook completed successfully and the research stop rule fired. The all-final-day cash-alignment treatment should **not** be promoted. The first primary comparison finished three coins worse. No further source pairs were run after that negative result.

| Item | Verified returned result |
|---|---|
| Bundle file hashes | 29 of 29 matched |
| Notebook | 14 executed code cells, no error outputs |
| Unit tests in AWS report | 86 passed; zero failures/errors/skips |
| Corrected mechanics | Both fixtures passed |
| Research completed | One pair / two branches / 46 suffix transitions |
| Control source checks | All 23 suffix transitions reproduced |
| Control final cash | 44,840 |
| Aligned final cash | 44,837 |
| Own cash / margin changes | −3 / −3 |
| Opponent cash | 44,082 in both branches |
| Match outcome | Win in both; delta 0 |
| Residual product units | Zero in both branches |
| Maximum candidate callback | 38.0534 ms |
| Reported worker elapsed time | 7.5123 seconds |
| Decision | STOP_NEGATIVE_TERMINAL_EFFECT |
| New official submission score | None recorded |

The old `failure.json` and `failure_worker.json` are historical files from 23:37 UTC. They predate the successful corrected run at 23:58 UTC. They remain preserved, not erased. No repeated setup or mechanics repair is required now.

## Cash mechanism

The aligned branch led by 714 coins after decision 716, by 83 after decision 717, and lost three by decision 718. Farm actions match for all 23 steps and opponent actions match throughout. Both branches sell all their products by the endpoint.

Four tomatoes account for the net difference: 332 coins when sold at step 716 versus 335 at step 717. The ledger reconciles per-product conditional liquidation values to actual cash movements and confirms no competing same-product orders in those attribution steps. Other late-sale product totals have zero net difference. Earlier sale receipts did not become extra final wealth.

## Decision

Keep the stopped treatment as negative evidence. Test a new, fixed last-callback gate that preserves the control policy on every earlier observation. Never rerun notebook 09 until it happens to pass, waive the negative endpoint gate, or promote immediate cash gains as season improvements.

This is a development-selected hypothesis, not independent validation. The next package supplies 120 new timing descriptors but changes actions using only the fixed final-callback indicator. Other known-demand scenarios are diagnostics until controlled outcome evidence justifies using them.
