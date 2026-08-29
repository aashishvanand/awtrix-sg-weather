# Ulanzi SG Weather — Live Weather for AWTRIX (Singapore)

An n8n workflow that replaces the native `Temperature` and `Humidity` apps on a
Ulanzi Pixel Clock (**AWTRIX NG** firmware) with live outdoor data for a
Singapore location. The clock's onboard sensor sits indoors next to a power
supply, so it is a poor proxy for outdoor conditions; this workflow pushes
readings from [data.gov.sg](https://data.gov.sg)'s NEA real-time APIs instead.

Everything runs on the LAN — n8n pushes directly to the clock's HTTP API. The
workflow drives up to five rotating apps: current conditions, the next forecast
window, air quality, and, at the relevant times of day, sunrise/sunset and the
moon phase.

## Architecture

```
Schedule trigger (n8n, every 5 min)
  → data.gov.sg: air temperature, relative humidity        — fetched every run
  → data.gov.sg: 2-hour forecast, PM2.5  +  USNO: sun/moon — cached 30 min
  → nearest station / area / region to the configured coordinates
  → Build Payloads: pick icons, gate the time-of-day apps
  → PUT to AWTRIX NG's pushed-app API, once per app
```

### Nearest-match

None of the data.gov.sg endpoints accept a lat/lon filter — each returns its
full dataset on every call. Temperature and humidity are reported from a network
of roughly 16 physical stations, the 2-hour forecast per named area (Ang Mo Kio,
Bedok, …), and PM2.5 per one of five regions (north / south / east / west /
central). `Build Payloads` haversine-sorts each dataset and uses whichever
station, area, or region is physically closest to `HOME_LAT` / `HOME_LON`.

This logic is Singapore-specific. For another location, replace the `Fetch`
nodes with an API that covers your region.

## Hardware and firmware

1. Flash **AWTRIX NG** with the official web flasher (Chrome / Edge / Opera):
   <https://blueforcer.github.io/awtrix3/#/flasher>. Connect over USB-C, click
   **Connect**, select the serial port, tick **Erase Device**, then **Install**.
2. On first boot the clock broadcasts an `AWTRIX_xxxxx` Wi-Fi hotspot
   (password `12345678`). Join it and enter your home Wi-Fi credentials.
3. Give the clock a static IP on your router. This README uses `<CLOCK_IP>` as a
   placeholder throughout.
4. The clock needs no WAN access for this workflow — every push is over the LAN.
   It only needs internet briefly when you add an icon, which the web UI fetches
   from LaMetric's gallery.

The web UI at `http://<CLOCK_IP>` is where icons, apps, and settings live.

## One-time clock setup

Disable the native sensor apps so they do not compete with the pushed ones:

```bash
curl --location 'http://<CLOCK_IP>/api/settings' \
  --header 'Content-Type: application/json' \
  --data '{ "HUM": false, "TEMP": false }'
curl --location --request POST 'http://<CLOCK_IP>/api/reboot'
```

Both settings take effect only after the reboot.

## Icons

Pushed payloads reference AWTRIX's built-in numeric icon IDs (for example
`icon: "2286"`). **Every icon must be added to the clock by hand:** open the icon
picker in the web UI, choose **Fetch from LaMetric gallery**, enter the ID, and
**Save to AWTRIX**. If a payload references an icon that is not present, the
payload still validates and nothing errors — that slot simply renders nothing.

> **Check Settings → Storage before adding icons.** The icon partition is small
> (512 KB) and fills quickly. An earlier version of this project uploaded icon
> files over the REST API directly; once the partition was full
> (512.0 / 512.0 KB, 0 B free) every write panicked the ESP32 mid-write, which
> is also why the same bytes could upload once and then fail on retry. The web
> UI's fetch-and-save path is bound by the same limit. Delete unused icons if
> the partition is near full.

### Weather condition icons

Chosen to match [this Alta Weather AWTRIX flow](https://flows.blueforcer.de/flow/QZ0sO0JQb7ut),
extended to cover conditions that data.gov.sg reports but that flow's source
(open-meteo) does not. Singapore never reports snow, so there is no snow icon.

| Condition(s) | Icon ID |
|---|---|
| Fair / Fair and Warm (day) | `53386` |
| Fair (Night) | current moon-phase icon — see [Moon phase](#moon-phase) |
| Partly Cloudy / Windy (day) | `2286` |
| Partly Cloudy (Night) | `43737` |
| Cloudy | `53384` |
| Hazy / Slightly Hazy / Mist / Fog | `17055` |
| Light Rain / Passing / Light Showers | `2720` |
| Moderate/Heavy Rain, Showers, Heavy Showers | `49300` |
| Thundery Showers (all variants) | `29839` |
| fallback | `36637` |

**Why `Partly Cloudy (Night)` is a separate entry.** data.gov.sg suffixes
dark-hours forecasts with `(Night)`. Previously every "Partly Cloudy" string
resolved to the daytime sun-and-cloud icon (`2286`), so a cloudy night still
displayed a sun. The `NIGHT_ICON` map in `Build Payloads` overrides it with a
moon-and-cloud icon (`43737`).

`NIGHT_ICON` is consulted only for conditions that data.gov.sg actually tags
with `(Night)` — in practice only `Fair` and `Partly Cloudy` — so `Partly
Cloudy` is the sole key that has any effect today. If icon `43737` has not been
added to the clock, set that key's value to `''`; the workflow then falls back
to the daytime icon rather than leaving the slot blank. The gallery also has
matching night icons for wetter conditions (`43738` rain, `43739` heavier rain,
`43747` drizzle, `43748` thunderstorm), noted in a code comment but not wired
up, because data.gov.sg does not currently tag those conditions as night.

### Moon phase

`curphase` from the USNO response maps to one of eight icons:

| Phase | Icon ID |
|---|---|
| New Moon | `2318` |
| Waxing Crescent (~25%) | `2317` |
| First Quarter (~50%) | `2316` |
| Waxing Gibbous (~75%) | `2315` |
| Full Moon | `2314` |
| Waning Gibbous (~75%) | `2319` |
| Last Quarter (~50%) | `2320` |
| Waning Crescent (~25%) | `2321` |

The named phase comes from the
[US Naval Observatory Astronomical Data API](https://aa.usno.navy.mil/data/api)
(`GET /api/rstt/oneday?date=…&coords=HOME_LAT,HOME_LON&tz=8`, no key required),
fetched together with the forecast and PM2.5 data on the same 30-minute cache.
The same response also carries the sunrise and sunset times. If USNO is
unreachable, or returns a phase name outside the table, `Build Payloads` falls
back to a local synodic-month calculation so the icon still resolves.

This icon is used in two places: the dedicated `moon_phase` app, and — in place
of the daytime `Fair` sun — the `current_weather` icon on a clear night. The
second case is driven by the forecast string, so it is not time-gated the way
the standalone app is.

### Sunrise and sunset icons

| Event | Icon ID |
|---|---|
| Sunrise (`Sunrise II`) | `22588` |
| Sunset | `12061` |

Times come from the USNO `sundata` field (same 30-minute cache as the moon
phase). If USNO is unavailable, fixed Singapore values (`07:01` / `19:10`) are
used — local sunrise and sunset shift only a few minutes across the year.

### AQI severity icons

A 12-tier ramp from the LaMetric gallery, banded against the raw PM2.5 reading
in µg/m³. This is a threshold walk for display purposes, not a PSI or US-EPA AQI
conversion.

| PM2.5 (µg/m³) up to | Icon ID |
|---|---|
| 25 | `39706` |
| 40 | `39709` |
| 60 | `39710` |
| 90 | `39711` |
| 110 | `39712` |
| 140 | `39713` |
| 160 | `39714` |
| 190 | `39715` |
| 210 | `39716` |
| 290 | `39717` |
| 310 | `39718` |
| over 310 | `39719` |

## The n8n workflow

`n8n_weather_workflow.json` is the importable workflow with placeholder config,
safe to publish. `n8n_weather_workflow.local.json` (gitignored through the
`*_workflow.local.json` pattern) is your working copy with real coordinates, IP,
and API key — deploy from that one so secrets are never committed.

Import through n8n's **Import from File**, then fill in the **Config** node:

| Field | Description |
|---|---|
| `HOME_LAT` / `HOME_LON` | Coordinates used for the nearest station / area / region match |
| `CLOCK_IP` | The clock's static IP |
| `DATA_GOV_SG_API_KEY` | From [data.gov.sg](https://guide.data.gov.sg/developer-guide/api-keys). The endpoints work without a key, but one raises the rate limit and is more reliable |

### Execution flow

```
Every 5 min → Config
  → Fetch Air Temperature (data.gov.sg)      [every run]
  → Fetch Relative Humidity (data.gov.sg)    [every run]
  → Fetch Forecast/PM2.5 (cached 30 min)     [forecast + PM2.5 + USNO sun/moon]
  → Build Payloads                           [nearest-match, icon and app selection]
  → Push to Clock: PUT /api/v1/apps/pushed/<app>, once per app
```

**Why the forecast, PM2.5, and sun/moon data are cached for 30 minutes.**
Temperature and humidity change minute to minute and are fetched on every run.
The 2-hour forecast, PM2.5, and USNO data change far more slowly — the moon
phase and sunrise/sunset need only day-level precision — so polling them every
5 minutes returns no fresher data. `Fetch Forecast/PM2.5` caches the combined
response in workflow static data (`$getWorkflowStaticData('global')`) and
re-fetches only once it is older than 30 minutes, reducing those API calls by
roughly 6×.

### Apps pushed to the clock

| App | When | Content |
|---|---|---|
| `current_weather` | every run | Temperature and humidity; icon from the current 2-hour forecast condition |
| `weather_forecast` | every run | The forecast's valid window (e.g. `NEXT 5-7PM`), same icon. data.gov.sg's 2-hour forecast is effectively "conditions for the next ~2 hours" — there is no finer-grained data |
| `aqi` | every run | Nearest-region PM2.5 with a severity-band icon. UV was dropped because data.gov.sg's UV index reads `0` outside daylight hours |
| `sunrise_sunset` | within ±2 h of sunrise or sunset | `RISE 6-8AM` around sunrise, `SET 6-8PM` around sunset |
| `moon_phase` | between sunset and the next sunrise | Phase icon and illuminated fraction (e.g. `WANING GIBBOUS 99%`) |

The native **clock** (`Time`) app and the **airline** app (from the separate
[Awtrix Feeder](../Awtrix%20Feeder) workflow) are outside this workflow's scope.

**Why `sunrise_sunset` and `moon_phase` are time-gated.** The moon phase is only
meaningful after dark, and a sunrise or sunset window is only interesting near
the event; pushing them all day would crowd the rotation. `sunrise_sunset`
therefore appears only in a 4-hour band centred on each event, and `moon_phase`
only at night. `sunrise_sunset` shows an approximate ±1-hour window
(`RISE 6-8AM`) rather than a to-the-minute time, matching the
`weather_forecast` app's `NEXT 5-7PM` style.

**How the time-gated apps are removed.** A pushed app stays on the clock until
it is re-pushed or expires. `sunrise_sunset` and `moon_phase` are sent with
`lifetime: 360` and `lifetimeMode: 0`, so once the workflow stops pushing them
the clock removes them within about six minutes — just over one 5-minute cycle,
which absorbs a single missed run without the app flickering in and out. The
always-on apps carry no `lifetime` and are simply re-pushed every run.

**App names.** A name is the final path segment of
`PUT /api/v1/apps/pushed/<name>`, so names use underscores, not spaces. The apps
were renamed for clarity: `weather` → `current_weather`, `sun` →
`sunrise_sunset`, `moon` → `moon_phase` (`weather_forecast` and `aqi`
unchanged). A pushed app is not renamed in place, so any app pushed under an old
name stays on the clock showing its last state. Remove the stale ones once —
either by swiping them away in the Apps view, or with the delete endpoint
(`PUT` with an empty body is rejected; the firmware requires `DELETE`):

```bash
for app in weather sun moon; do
  curl -X DELETE "http://<CLOCK_IP>/api/v1/apps/$app"
done
```

`GET http://<CLOCK_IP>/api/v1/apps` lists what is currently on the clock
(`"origin":"pushed"` entries are the workflow-managed ones).

### AWTRIX NG payload schema

The pushed-app API rejects unknown keys and validates enums strictly:

- Duration is `durationMs` (milliseconds), not `duration`.
- `textCase` must be `"inherit"`, `"upper"`, or `"asTyped"`; the older numeric
  codes (`0` / `1` / `2`) are rejected.
- The push endpoint is `PUT /api/v1/apps/pushed/<name>`, not the older
  `POST /api/custom?name=<name>`. To remove an app, use
  `DELETE /api/v1/apps/<name>` — a `PUT` with an empty body is rejected.
- `lifetime` (seconds; `0` = never) and `lifetimeMode` (`0` = delete, `1` =
  mark stale) are accepted, and are used by the time-gated apps.

### Deploying and updating

The workflow runs on its own 5-minute schedule trigger. After importing, set it
to **Active** in n8n.

n8n's schedule trigger executes from a snapshot taken when the workflow was
activated. Editing `Build Payloads` afterwards — in the UI or through the REST
API — does **not** affect the next run until the workflow is toggled off and on
again (the Active switch, or `POST /api/v1/workflows/<id>/deactivate` followed
by `POST /api/v1/workflows/<id>/activate`).

## Repository layout

```
.
├── README.md
├── n8n_weather_workflow.json        # importable workflow, secrets scrubbed
└── n8n_weather_workflow.local.json  # working copy with real secrets (gitignored)
```

## Before publishing this repository

- **`.env`** holds the data.gov.sg and n8n API keys. It is gitignored; keep it
  that way.
- **`n8n_weather_workflow.json`** — confirm the `Config` node's
  `DATA_GOV_SG_API_KEY` is a placeholder. Deploy from
  `n8n_weather_workflow.local.json` (gitignored) instead.
