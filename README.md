# client-machine

## ad_monitor.py

Pulls ad-level metrics for the **active** Meta (Facebook/Instagram) ad
campaigns in the `CM` project. For each ad in those campaigns it prints the
status, effective status, Spend, Clicks and CTR, plus a total row per campaign.
Below the table it lists any delivery issues or review feedback Meta reports,
and any active ad that got no impressions in the period.

A campaign counts as part of the project when its name contains `CM`
(case-insensitive).

### Setup

1. Install Python 3.8 or newer, then install the one dependency:

   ```bash
   pip install -r requirements.txt
   ```

2. Get your credentials:
   - **Access Token**: a token with the `ads_read` permission. A System User
     token from Business Manager is the best choice because it doesn't expire
     quickly. You can also make one in the Graph API Explorer for testing.
   - **Ad Account ID**: in Ads Manager, the number next to your account name.
     You can include the `act_` prefix or leave it off.

3. Provide them. Environment variables are the recommended way, because they
   keep the token out of git:

   ```bash
   export META_ACCESS_TOKEN="your-token"
   export META_AD_ACCOUNT_ID="1234567890"
   ```

   You can also replace the `YOUR_ACCESS_TOKEN_HERE` and
   `YOUR_AD_ACCOUNT_ID_HERE` placeholders at the top of `ad_monitor.py`. If you
   do, don't commit the file with a real token in it.

### Run

```bash
python ad_monitor.py                        # last 7 days (default)
python ad_monitor.py --date-preset today
python ad_monitor.py --date-preset last_30d
python ad_monitor.py --keyword other-project
```

Example output:

```
Ads in active 'CM' campaigns in act_1234567890 (last_7d)

Campaign: CM · Spring Launch (120200000000000000)
Ad                             Status   Effective status        Spend  Clicks   CTR %
-------------------------------------------------------------------------------------
Ad1 · Problem                  ACTIVE   ACTIVE                 152.40     913    1.89
Ad2 · Demo                     ACTIVE   ACTIVE                   0.00       0    0.00
-------------------------------------------------------------------------------------
TOTAL                                                          152.40     913    1.89

Issues:
  - Ad2 · Demo: active but has no impressions in this period
```

Spend is shown in the ad account's currency.

The script calls Graph API `v23.0` by default. To use a different version, set
`META_API_VERSION`, for example `export META_API_VERSION=v24.0`.
