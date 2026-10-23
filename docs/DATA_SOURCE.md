# Data source findings

Inspection date: 23 October 2026 (Australia/Brisbane).

Primary public page: `https://www.spacex.com/launches`

This application does **not** scrape the rendered DOM of that page. The site is an Angular SPA (`<app-root>`) that hydrates launch data from SpaceX's public CMS JSON APIs. Those APIs are the reliable structured source of truth.

## What the public page is

`https://www.spacex.com/launches` returns a ~3 KB HTML shell. There is no embedded Next.js payload, no JSON-LD launch list, and no GraphQL document in the initial HTML. Launch rows are loaded client-side.

Relevant bootstrap files:

- `https://www.spacex.com/environment.js` — sets `cmsBaseUrl` / `storageBucketBaseUrl` to `https://content.spacex.com`
- `https://www.spacex.com/main.*.js` — Angular CMS client with the endpoint list below

CSP `connect-src` also allows `https://api.spacex.com`, but that host is the customer portal API (currently unreachable / 522) and is **not** used for public launch listings.

Community APIs such as `https://api.spacexdata.com` are **not** used. They are unofficial and, as of this inspection, not the source behind spacex.com.

## Structured endpoints consumed

Base URL: `https://content.spacex.com`

| Endpoint | Role |
| --- | --- |
| `GET /api/spacex-website/launches-page-tiles/upcoming` | Upcoming missions shown on the launches page |
| `GET /cms-assets/future_missions.json` | Authoritative countdown / window timestamps, keyed by `correlationId` |
| `GET /api/spacex-website/launches-page-tiles` | Full tile catalog: upcoming, `in-progress`, and completed (`final`) missions |
| `GET /api/spacex-website/missions/{slug}` | Mission page body, webcasts, booster/landing copy, official pre/post launch timelines |
| `GET /api/spacex-website/launches-page-stats` | Aggregate launch/landing/reflight counts (not required for the dashboard) |

The Angular app cache-busts `future_missions.json` near T0 with `?{unix_seconds}`.

### Upcoming tiles

Each tile includes:

- `id`, `documentId`, `correlationId`, `link` (mission slug)
- `title`, `vehicle`, `launchSite`, `returnSite`, `missionType`
- `missionStatus` (`upcoming` \| `in-progress` \| `final`)
- `launchDate` / `launchTime` / `endDate` / `endTime` (often `null` for upcoming; times on completed tiles are **local to the launch site**)
- `isLive` (official live flag)
- `callToAction` (`WATCH`, `REWATCH`, `LEARN MORE`, …)
- `showLaunchTimeInsteadOfWindow`
- `override` (optional date/time or window that supersedes the tile clock)
- `toTheIssEnabled` / ISS tense live only on the mission document, not the tile

### Timing document (`future_missions.json`)

Keyed by tile `correlationId`. Unix timestamps are UTC.

```json
{
  "PrimaryLaunchDate": { "Seconds": 1792791000, "Nanos": 0 },
  "PrimaryLaunchWindow": {
    "Open": { "Seconds": 1792791000 },
    "Close": { "Seconds": 1792805400 }
  },
  "TZeroLaunchDate": null,
  "TZeroPaused": null,
  "TZeroValue": null,
  "IsPrimaryLaunchTimeGiven": false
}
```

Interpretation used by this app (matching SpaceX's own client):

- Prefer `TZeroLaunchDate` when present and not paused.
- If `TZeroPaused` is true, freeze countdown at `TZeroValue` seconds (hold clock).
- Otherwise use `PrimaryLaunchDate` / `PrimaryLaunchWindow`.
- `IsPrimaryLaunchTimeGiven === false` with a multi-hour window means **do not treat window open as T−0**.

On 23 October 2026 the next mission (`sl-15-15`) had a four-hour window opening `2026-10-23T21:30:00Z`.

### Mission documents

`GET /api/spacex-website/missions/{slug}` returns:

- `paragraphs[].content` — HTML fragments (treated as untrusted; stripped to text)
- `webcasts[]` — `{ videoId, streamingVideoType, title, isFeatured }`
- `preLaunchTimeline` / `postLaunchTimeline` — official but usually marked **All Times Approximate**
- Dragon/ISS flags: `toTheIssEnabled`, `toTheIssTense` (`present` = currently docked), `followDragonEnabled`, `returnFromIssEnabled`

Webcast URL construction:

- `streamingVideoType: "x-live-studio"` → `https://x.com/i/broadcasts/{videoId}`
- `streamingVideoType: "x.com"` with a numeric status id → `https://x.com/i/status/{videoId}`

Official mission page: `https://www.spacex.com/launches/{slug}`

### Local tile timestamps

When a tile includes `launchDate` + `launchTime` and no UTC timing document, SpaceX interprets that clock in the launch site's timezone (DST-aware):

| Site fragment | IANA timezone |
| --- | --- |
| Florida (`LC-39A`, `SLC-40`, `SLC-37`) | `America/New_York` |
| California (`SLC-4E`) | `America/Los_Angeles` |
| Starbase / Texas | `America/Chicago` |
| Omelek Island | `Pacific/Kwajalein` |

This app uses IANA zones rather than SpaceX's hardcoded offset maps.

## Status mapping

SpaceX CMS `missionStatus` is **not** copied into the product model.

| CMS value | Internal starting point |
| --- | --- |
| `upcoming` | `scheduled` (engine may promote to `countdown` / `window_open`) |
| `in-progress` | `in_flight` (ISS missions may stay here for months while docked) |
| `final` | `mission_complete` |

`isLive` plus webcast + window + T+ window are combined by `LiveStatusService`. A `WATCH` CTA alone does **not** mean the mission is live; completed missions often still say `WATCH`.

## What we do not scrape

- The launches HTML table
- Photographic globes or copyrighted infographic artwork
- Customer portal `api.spacex.com`
- Community SpaceX APIs

HTML/Playwright remains a reserved fallback only if the CMS JSON contract disappears. It is disabled by default.

## Rate limits

Do not fetch the full 700+ tile catalog on the fast loop.

| Resource | Typical cadence |
| --- | --- |
| `future_missions.json` | follows proximity schedule (10 min / 2 min / 30–60 s / 15–30 s) |
| upcoming tiles | same as timings when a launch is near |
| full tile catalog | every 10 minutes, or when timing correlation IDs change |
| mission documents | upcoming + in-progress + recent only |

User-Agent: `SpaceXMissionControl/1.0 (+https://github.com; mission-status dashboard)`.

## Fixtures

Parser tests use frozen samples in `backend/tests/fixtures/` captured from the endpoints above. The test suite never hits spacex.com.
