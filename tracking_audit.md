# Meta tracking audit: CM ads → Gumroad (2026-10-08)

Read-only audit. No tracking or ad settings were changed.

## Dataset

| | |
|---|---|
| Pixel / dataset | `2239569883568957` "LumiGoods Pixel" |
| Owner | ad account `act_2524309034712212` |
| Created | 2026-10-06 |
| Status | active; first-party cookies on; data use "advertising and analytics" |
| Automatic advanced matching | **off** |
| Conversions API (server) | **never received an event** (`server_last_fired_time` is empty) |

## Where tracking is installed

- **This repo has no tracking code.** The scripts only read Meta insights
  (`ad_monitor.py`, `daily_report.py`) and attach the pixel to ads
  (`launch_campaign.py`, plus the ads built with the connector).
- All events come from `lumigoods.gumroad.com`, and all are browser events.
  That points to **Gumroad's built-in Meta Pixel setting**. Gumroad's settings
  couldn't be opened from here, so this is inferred from Meta's data and not
  confirmed.
- Gumroad's help docs say Gumroad doesn't support the Conversions API
  ([source](https://gumroad.com/help/article/174-third-party-analytics)).

## Events received (last 26 days, all browser)

| Event | Count |
|---|---|
| ViewContent | 24 |
| InitiateCheckout | 2 |
| PageView | 1 |
| **Purchase** | **0** |

Meta reports every event's URL as `https://lumigoods.gumroad.com/` only, so
this data can't show whether the UTM parameters reached the page.

## Ads

- All 6 new ads have `tracking_specs` set to pixel `2239569883568957`, the
  correct dataset.
- Every ad's link is
  `https://lumigoods.gumroad.com/l/client-machine?utm_source=meta&utm_medium=paid&utm_campaign=cm-validation&utm_content=<problem|workflow|demo>`.
  `url_tags` is empty, so no UTM parameters are added twice.
- The previous campaign got 12 link clicks and 11 landing page views; the
  pixel credited 3 ViewContent to it and **0 Purchases**.

## Verdict

- **Verified:** the pixel is live on the Gumroad store and receives
  ViewContent and InitiateCheckout from real visitors. The ads point at the
  right dataset.
- **Not verified: Purchase.** No Purchase event has ever reached this
  dataset. Either there were no sales, or Purchase isn't firing. Without
  Gumroad sales data the two can't be told apart.
- **Not verified: UTM survival.** Gumroad is blocked by this environment's
  network policy, so the redirect chain couldn't be followed.
- **No CAPI, and no duplicate Purchases**, because there are no Purchases at
  all.

## Manual test results (2026-10-08, by the account owner)

- **Events Manager → Test events** (window opened from Events Manager):
  View content ×2, Initiate checkout and SubscribedButtonClick arrived from
  `lumigoods.gumroad.com` in dataset `2239569883568957`, all Browser,
  "Manual setup", status Processed, no duplicates. **Verified.**
- **Purchase:** not seen during the test. **Still unverified.**
- **UTM survival:** opening the Ad1 link in an incognito window kept the full
  query string on the Gumroad product page
  (`/l/client-machine?utm_campaign=cm-validation&utm_content=problem&utm_medium=paid&utm_source=meta`).
  **Verified.** So Gumroad receives the `utm_content` that identifies each
  ad (`problem`, `workflow`, `demo`).

## Decision: split monitoring

The owner chose to keep the two sides separate rather than reconcile them:

- **Meta side (Claude):** spend, clicks, landing page views, Initiate
  checkouts per ad, delivery issues.
- **Sales side (owner):** Gumroad Analytics for sales and revenue, using the
  `utm_content` breakdown for sales per ad.

Purchase stays unverified on purpose. Meta's purchase and ROAS columns will
read 0 even when there are sales, so don't use them. Gumroad is the source of
truth for sales.

## Manual checks in Meta Events Manager / Gumroad

1. Gumroad → Settings → Advanced: confirm the Meta Pixel ID is exactly
   `2239569883568957` and that no second pixel is pasted anywhere else.
2. Events Manager → dataset → **Test events**: open an ad link with its UTMs,
   then buy the product with a 100%-off discount code. Confirm PageView,
   ViewContent, InitiateCheckout and **one** Purchase (value 47, currency USD)
   arrive in this dataset.
3. During that test, check that the address bar on the Gumroad page still
   shows the `utm_*` parameters, and that the sale appears under that source
   in Gumroad's analytics.
4. After the first real sale, check Overview → Purchase → Event Match Quality.

## Proposed fixes (not applied; need approval)

1. Run the test purchase above before launching, since ROAS reporting
   depends on Purchase.
2. Turn on **automatic advanced matching** in Events Manager for better
   attribution.
3. Set `GUMROAD_ACCESS_TOKEN` (and `GUMROAD_PRODUCT_ID`) so `daily_report.py`
   can compare Gumroad sales with the Purchases the pixel reports.
4. Optional, later: send server-side Purchases from Gumroad Ping to the
   Conversions API. Gumroad's browser pixel and Ping share no `event_id`, so
   Meta can't de-duplicate them and each sale could count twice. Only do this
   if the test shows the browser Purchase is missing or unreliable.
5. Allow `lumigoods.gumroad.com` in this environment's network settings so
   the redirect and UTM check can be automated.

## Changes applied (2026-10-08, approved)

- Automatic advanced matching turned **on** for `2239569883568957`
  (fields: em, ph, fn, ln, ct, st, zp, country, external_id). Confirmed by
  reading the setting back.
- No Conversions API and no Gumroad token, by decision (see Split monitoring).

Re-run `python final_check.py` before launch; it checks pixel and ad settings
read-only.
