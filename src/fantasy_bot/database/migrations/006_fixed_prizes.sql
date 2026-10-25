-- The prize split is now one fixed rule in code (money/prizes.py: 50/30/15/5), the same every
-- season, so the per-season payout_rank table goes. See docs/plans/simplify.md, step 4.
DROP TABLE payout_rank;
