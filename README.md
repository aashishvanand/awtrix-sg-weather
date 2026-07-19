# Ulanzi SG Weather — Live Weather for AWTRIX (Singapore)

Replaces the native `Temperature`/`Humidity` apps on a Ulanzi Pixel Clock
(AWTRIX 3 firmware) with live outdoor readings, since the onboard sensor sits
indoors next to a wall wart and isn't a great proxy for outdoor conditions.
This is a **standalone n8n workflow** that pulls live readings from
[data.gov.sg](https://data.gov.sg)'s NEA real-time weather API (no API key
strictly required) and pushes them to the clock as a custom app, so the
numbers on screen are always current.

```
Schedule Trigger (n8n, every 5min)
  -> data.gov.sg (air temperature, relative humidity, 2hr forecast)
  -> nearest station/area to home coords + forecast icon
  -> POST to AWTRIX custom app API
```

data.gov.sg's air-temperature and relative-humidity endpoints report from a
network of ~16 physical weather stations, and the 2-hour forecast endpoint
reports per named area (Ang Mo Kio, Bedok, ...) — none of these are a single
point forecast, so the workflow haversine-sorts each and uses whichever
station/area is physically closest to `HOME_LAT`/`HOME_LON`. This only makes
sense for Singapore locations — if you're elsewhere, swap the three `Fetch`
HTTP nodes for whatever weather API covers your region.

## Hardware / firmware

1. Flash **AWTRIX 3** onto the clock using the official web flasher (Chrome/Edge/Opera):
   https://blueforcer.github.io/awtrix3/#/flasher
   - Connect via USB-C, click **Connect**, select the serial port, check **Erase Device**,
     click **Install AWTRIX 3**.
2. On first boot the clock broadcasts a `AWTRIX_xxxxx` WiFi hotspot
   (password `12345678`). Connect to it and hand it your home WiFi credentials.
3. Give it a static IP on your router/UniFi controller (this project uses `YOUR_CLOCK_IP` as a placeholder throughout).
4. Once it's on your network and confirmed working, block it from reaching the
   internet at your firewall/UniFi controller — it never needs WAN access, everything
   here runs over the LAN.

The clock's web UI lives at `http://<CLOCK_IP>` — icons, apps, and settings all
live there.

## Forecast icons

The 2-hour forecast returns one of 23 fixed condition strings (`Fair`,
`Heavy Thundery Showers with Gusty Winds`, etc). `generate_weather_icons.py`
draws 15 hand-plotted 8x8 pixel-art icons covering all of them — there's no
source photo to convert, so these are drawn directly:

```
generate_weather_icons.py -> icons/wx_<key>.gif, e.g. icons/wx_thunder_wind.gif
```

```bash
python3 -m venv venv && venv/bin/pip install pillow numpy
venv/bin/python generate_weather_icons.py
./upload_icons.sh
```

The `Build Weather Payload` code node in the workflow maps each of the 23
forecast strings to one of the 15 icon keys (several share an icon, e.g.
`Light Rain` / `Passing Showers` / `Light Showers` all use `wx_light_rain`)
and sets it as the custom app's `icon`, so temperature, humidity, and a
forecast icon all show on one page:
`{ "text": "28C 82%", "icon": "wx_partly_cloudy_night", ... }`.

### `upload_icons.sh`

Bulk-uploads everything in `icons/` to the clock over its built-in LittleFS
file editor (`http://<CLOCK_IP>/edit`), skipping any icon whose hash hasn't
changed since the last run (tracked in `.upload_state.json`, gitignored).

```bash
./upload_icons.sh
```

Set `CLOCK_IP` at the top of the script to your clock's static IP.

**Note on the upload API:** the AWTRIX file editor is ESPAsyncWebServer's
`SPIFFSEditor`. The destination path has to be embedded in the multipart
`filename` field itself (`filename=/ICONS/wx_thunder.gif`) — a separate
`?path=` query parameter is silently ignored and the file lands in the root
directory instead. `upload_icons.sh` already does this correctly.

## One-time setup — disable the native sensor apps

```bash
curl --location 'http://<CLOCK_IP>/api/settings' \
  --header 'Content-Type: application/json' \
  --data '{ "HUM": false, "TEMP": false }'
curl --location 'http://<CLOCK_IP>/api/reboot' --request POST
```

Both settings require a reboot to take effect.

## n8n workflow

`n8n_weather_workflow.json` is an importable n8n workflow. Import it via
n8n's **Import from File** and fill in the placeholders in its own **Config**
node:

| Field | What it is |
|---|---|
| `HOME_LAT` / `HOME_LON` | Your coordinates — used to find the nearest station/area |
| `CLOCK_IP` | The AWTRIX device's static IP |
| `DATA_GOV_SG_API_KEY` | From [data.gov.sg](https://guide.data.gov.sg/developer-guide/api-keys) — the endpoints work without one, but a key raises your rate limit and is more reliable long-term |

**Flow:**

```
Every 5min -> Config
  -> Fetch Air Temperature (data.gov.sg)
  -> Fetch Relative Humidity (data.gov.sg)
  -> Fetch 2hr Forecast (data.gov.sg)
  -> Build Weather Payload (nearest station/area to home coords + forecast icon)
  -> POST /api/custom?name=weather
```

Weather doesn't need 30s polling like a flight tracker does, so it runs on
its own 5-minute trigger. Remember to flip it to **Active** in n8n after
import.

## Repo layout

```
.
├── README.md
├── generate_weather_icons.py  # hand-plotted pixel art -> icons/wx_*.gif (forecast icons)
├── upload_icons.sh            # bulk-upload icons/ to the clock
├── n8n_weather_workflow.json  # importable n8n workflow (secrets scrubbed)
└── icons/                     # generated 8x8 forecast icons — original pixel art, safe to publish
```

## Before you publish this repo

- **`.env`** holds your `data.gov.sg` API key — already gitignored, do not
  remove that entry.
- **`n8n_weather_workflow.json`** — its `Config` node's `DATA_GOV_SG_API_KEY`
  should be a placeholder before publishing. Paste your real key back in
  locally after importing to n8n.
- **`icons/wx_*.gif`** are original pixel art generated by this repo's own
  script, not third-party assets — safe to publish.
- **`.upload_state.json`** is local upload-tracking state, already gitignored.
