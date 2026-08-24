# Ulanzi SG Weather — Live Weather for AWTRIX (Singapore)

Replaces the native `Temperature`/`Humidity` apps on a Ulanzi Pixel Clock
(**AWTRIX NG** firmware) with live outdoor readings, since the onboard sensor
sits indoors next to a wall wart and isn't a great proxy for outdoor
conditions. This is a **standalone n8n workflow** that pulls live readings
from [data.gov.sg](https://data.gov.sg)'s NEA real-time APIs and pushes three
rotating apps to the clock: current conditions, the next forecast window, and
air quality (PM2.5).

```
Schedule Trigger (n8n, every 5min)
  -> data.gov.sg: air temperature, relative humidity (fetched live every run)
  -> data.gov.sg: 2hr forecast, PM2.5 (cached 30min - see below)
  -> nearest station/area/region to home coords
  -> Build Payloads: weather / weather_forecast / aqi
  -> PUT to AWTRIX NG's pushed-app API, once per app
```

data.gov.sg's air-temperature and relative-humidity endpoints report from a
network of ~16 physical weather stations, the 2-hour forecast endpoint
reports per named area (Ang Mo Kio, Bedok, ...), and PM2.5 reports per one of
5 regions (north/south/east/west/central) — none of these are a single point
reading, so the workflow haversine-sorts each and uses whichever
station/area/region is physically closest to `HOME_LAT`/`HOME_LON`. There's
no server-side lat/lon filter on any of these APIs; the full dataset comes
back every time and the nearest-match happens client-side in the `Build
Payloads` code node. This only makes sense for Singapore locations — if
you're elsewhere, swap the `Fetch` nodes for whatever weather API covers your
region.

## Hardware / firmware

1. Flash **AWTRIX NG** onto the clock using the official web flasher (Chrome/Edge/Opera):
   https://blueforcer.github.io/awtrix3/#/flasher
   - Connect via USB-C, click **Connect**, select the serial port, check **Erase Device**,
     click **Install**.
2. On first boot the clock broadcasts a `AWTRIX_xxxxx` WiFi hotspot
   (password `12345678`). Connect to it and hand it your home WiFi credentials.
3. Give it a static IP on your router/UniFi controller (this project uses `YOUR_CLOCK_IP` as a placeholder throughout).
4. This clock never needs WAN access for the weather workflow itself — n8n
   pushes readings to it entirely over the LAN. It does need internet
   briefly whenever you add a new icon (see below), since that's fetched
   from LaMetric's gallery through the clock's own web UI.

The clock's web UI lives at `http://<CLOCK_IP>` — icons, apps, and settings all
live there.

## Forecast and AQI icons

The custom apps below reference AWTRIX's built-in numeric icon IDs (e.g.
`icon: "2286"`). Add each one to the clock **manually through its web UI**:
open the icon picker, use **Fetch from LaMetric gallery** with the ID below,
then **Save to AWTRIX**. (An earlier version of this README had a script
that uploaded icon files directly via the REST API — that path turned out to
reliably crash the ESP32 mid-write, traced back to the icon storage
partition being completely full: 512.0 KB / 512.0 KB, 0 B free. Any write
attempt panics once the filesystem has no room left, regardless of which
file or how it's uploaded, which is also why identical bytes could succeed
once and then fail consistently afterward. The web UI's own fetch-and-save
flow doesn't dodge that limit, so **check Settings -> Storage on the clock's
web UI first** and delete unused icons if it's near full before adding new
ones.)

Without the matching icon added, the `icon` field still gets set correctly
in the payload and nothing errors — the icon file just silently doesn't
exist on the clock, so nothing renders for that spot.

**Weather icons** (picked to match [this Alta Weather AWTRIX
flow](https://flows.blueforcer.de/flow/QZ0sO0JQb7ut), extended to cover
conditions Singapore reports that the original flow's source (open-meteo)
doesn't — Singapore never reports snow, so unlike that flow there's no snow
icon here):

| Condition(s) | Icon ID |
|---|---|
| Fair / Fair and Warm (day) | `53386` |
| Fair (Night) | moon phase — see below |
| Partly Cloudy / Windy | `2286` |
| Cloudy | `53384` |
| Hazy / Slightly Hazy / Mist / Fog | `17055` |
| Light Rain / Passing / Light Showers | `2720` |
| Moderate/Heavy Rain, Showers, Heavy Showers | `49300` |
| Thundery Showers (all variants) | `29839` |
| fallback | `36637` |

**Clear sky at night** shows the actual moon phase instead of the sun icon
used for daytime `Fair` — the named phase comes from the
[US Naval Observatory's free Astronomical Data API](https://aa.usno.navy.mil/data/api)
(`GET /api/rstt/oneday?date=...&coords=HOME_LAT,HOME_LON&tz=8`, no API key
needed), fetched alongside the forecast/PM2.5 data in the same 30-minute
cache. Its `curphase` field maps directly to one of 8 icons:

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

If USNO is unreachable or returns a phase name outside this map, the
workflow falls back to a local synodic-month calculation so the icon still
shows something reasonable.

**AQI icons** — a 12-tier severity ramp (also from the LaMetric gallery),
banded against the raw PM2.5 reading in µg/m³. This is a simplification, not
a real PSI/US-EPA AQI conversion — it just walks up these thresholds:

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

## One-time setup — disable the native sensor apps

```bash
curl --location 'http://<CLOCK_IP>/api/settings' \
  --header 'Content-Type: application/json' \
  --data '{ "HUM": false, "TEMP": false }'
curl --location 'http://<CLOCK_IP>/api/reboot' --request POST
```

Both settings require a reboot to take effect.

## n8n workflow

`n8n_weather_workflow.json` is an importable n8n workflow with placeholder
config values, safe to publish. `n8n_weather_workflow.local.json` (gitignored,
matching the `*_workflow.local.json` pattern) is your personal copy with real
coordinates/IP/API key filled in — keep using that one for actual deploys so
your secrets never get committed.

Import via n8n's **Import from File** and fill in the placeholders in its own
**Config** node:

| Field | What it is |
|---|---|
| `HOME_LAT` / `HOME_LON` | Your coordinates — used to find the nearest station/area/region |
| `CLOCK_IP` | The AWTRIX device's static IP |
| `DATA_GOV_SG_API_KEY` | From [data.gov.sg](https://guide.data.gov.sg/developer-guide/api-keys) — the endpoints work without one, but a key raises your rate limit and is more reliable long-term |

**Flow:**

```
Every 5min -> Config
  -> Fetch Air Temperature (data.gov.sg)       [live every run]
  -> Fetch Relative Humidity (data.gov.sg)     [live every run]
  -> Fetch Forecast/PM2.5 (cached 30min)       [see below]
  -> Build Payloads (nearest station/area/region + icon selection, 3 apps)
  -> Push to Clock: PUT /api/v1/apps/pushed/<app>, once per app
```

**Why the 30-minute cache:** temperature and humidity are live sensor
readings that genuinely change minute to minute, but the 2hr-forecast,
PM2.5, and moon-phase data all change far slower (the moon phase alone
only needs day-level precision), so polling them every 5 minutes anyway
just burns API calls for no fresher data. The `Fetch Forecast/PM2.5`
code node caches their combined response (including the USNO moon-phase
lookup) in n8n's
workflow static data (`$getWorkflowStaticData('global')`, the same pattern
used for the OpenSky token in the aircraft-tracker sibling project) and only
re-fetches once the cache is older than 30 minutes. This cuts those API
calls roughly 6x while temp/humidity keep updating every run.

**The three apps pushed to the clock:**

| App name | Shows |
|---|---|
| `weather` | Current temp + humidity, icon from the current 2hr-forecast condition |
| `weather_forecast` | The forecast's valid time window (e.g. `NEXT 5-7PM`), same icon — data.gov.sg's 2hr-forecast is really "the forecast for the upcoming ~2hr window," so this is the closest thing to an hourly forecast the API offers; there's no finer-grained data available |
| `aqi` | Nearest-region PM2.5, icon reflecting its severity band (UV was dropped — data.gov.sg's UV index reads `0` outside daylight hours, which made it a mostly-useless field on the display) |

**AWTRIX NG payload schema** (learned the hard way — the pushed-app API
rejects unknown keys and validates enums strictly):
- Duration is `durationMs` (milliseconds), not `duration`.
- `textCase` must be one of `"inherit"`, `"upper"`, `"asTyped"` — the legacy
  numeric codes (`0`/`1`/`2`) from older AWTRIX firmware are rejected.
- The endpoint itself is `PUT /api/v1/apps/pushed/<name>`, not the old
  `POST /api/custom?name=<name>`.

Weather doesn't need 30s polling like a flight tracker does, so it runs on
its own 5-minute trigger. Remember to flip it to **Active** in n8n after
import.

## Repo layout

```
.
├── README.md
├── n8n_weather_workflow.json        # importable n8n workflow (secrets scrubbed)
├── n8n_weather_workflow.local.json  # your personal copy with real secrets (gitignored)
├── upload_icons.sh                  # bulk-upload icons/ to the clock
└── icons/                           # AWTRIX built-in icon files, by numeric ID (gitignored - third-party)
```

## Before you publish this repo

- **`.env`** holds your `data.gov.sg` and n8n API keys — already gitignored, do not
  remove that entry.
- **`n8n_weather_workflow.json`** — its `Config` node's `DATA_GOV_SG_API_KEY`
  should be a placeholder before publishing. Use
  `n8n_weather_workflow.local.json` (gitignored) for your real deploy.
- **`icons/`** holds files downloaded from LaMetric's icon repo (for
  "educational use" per that repo's own terms) — already gitignored, do not
  remove that entry or commit its contents.
- **`.upload_state.json`** is local upload-tracking state, already gitignored.
