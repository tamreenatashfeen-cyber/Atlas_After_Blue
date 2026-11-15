# Atlas After Blue

Atlas After Blue (AAB) is a small web app that uses NISAR satellite radar to document how a landscape changed after a flash flood. It was built for the NASA Space Apps Challenge 2026, under the challenge "Dancing with the SARs".

Live site: https://atlasafterblue.earth/

## What this is

Mountain valleys are often missed by live coverage during a flood, and after the water recedes authorities may not know where damage occurred. AAB compares two NISAR radar scenes of the same area taken from the same angle before and after a flood. Pixels that darkened by at least 3 dB and now look like calm water are marked as possible flood. Permanent water and tiny speckle noise are removed, and brighter areas are kept separate as uncertain change.

The result is reported as possible flood, not confirmed flooding, because no ground check exists for the site.

Demonstrated on Kandia Gol, Upper Kohistan, Pakistan (July 2026 floods).

## The case study

The app is built around one reported event: a flash flood in Kandia Gol, Upper Kohistan, Khyber Pakhtunkhwa, Pakistan, on 22 July 2026.

Two NISAR scenes bracket the event. One was acquired on 14 July (before) and one on 26 July (after), both on Track 84, Frame 19, ascending. The after scene is four days past the reported peak, so most of the standing water had already receded by the time it was imaged.

| Metric | Value |
| --- | --- |
| Before / after scenes | 14 Jul 2026 / 26 Jul 2026 |
| Candidate flooded area | 0.0278 km² (2.78 ha) |
| Candidate pixels | 278 on a 10 m grid |
| Candidate patches | 55 |
| Permanent water excluded | 0.0838 km² |
| Uncertain surface change | 11.56 km² |
| Confidence | Low (unvalidated) |

The headline reading is honest: four days after the peak, L-band radar saw little standing water. Most of the signal is surface change rather than open water.

## What the app shows

The site has five pages:

- **Home** introduces the event and shows a before/after comparison.
- **Report** is the main result view, with three tabs: an interactive Leaflet map of candidate patches, permanent water and backscatter change, a before/after swipe, and a side-by-side compare.
- **Method** explains the detection pipeline and its limits.
- **Sources** lists the data and event references.
- **About** covers the team and the project.

A history strip shows three observations (2, 14 and 26 July) on one shared brightness scale. This is visual context for how the area looked before the event. It does not change the detection result or its confidence.
How the app works
The app is a static site with five pages, each doing one job:

Home introduces the flood event and shows a before/after comparison, so a first-time visitor sees the change immediately.

- Report is the main result view. It has three tabs: an interactive Leaflet map of candidate patches, permanent water and backscatter change; a before/after swipe; and a side-by-side compare.

- Method explains the detection pipeline and its limits, in plain language with a glossary.

- Sources lists the data and event references behind every claim.

- About covers the team and the project.

All result numbers are loaded from JSON files in aab/data/, so the same figures appear on every page without being retyped. A history strip on the Home page shows three observations (2, 14 and 26 July) on one shared brightness scale as visual context; it does not affect the detection result or its confidence.

How a visitor uses it: open the Report page, switch between the map, swipe and side-by-side views to see where the ground changed, then read Method for what the flags mean and Sources for where the data came from.

## How the detection works

The pipeline is a transparent physical threshold, not a machine-learning model.

Calm open water reflects the radar signal away from the sensor, so it appears dark in the image. A pixel is flagged as a candidate flooded pixel when its backscatter drops by 3 dB or more between the two scenes and the post-event value is at or below -14 dB. A rise of 3.5 dB or more is held separately as uncertain surface change, because brighter returns can come from debris, roughened ground or moisture and cannot be attributed to flooding from radar alone. Isolated speckle is removed with a 4-pixel minimum mapping unit.

The current method is version v1.0, a 16-stage NISAR GCOV pipeline. The output is a candidate change map, not a confirmed flood extent.

## Data

The radar data come from the NASA-ISRO Synthetic Aperture Radar (NISAR) mission, L-band, searched and obtained through ASF Vertex. The scenes are L2 GCOV provisional products. The flood event itself is referenced from the Provincial Disaster Management Authority (PDMA), Khyber Pakhtunkhwa, daily situation report.

## Repository layout

```
Atlas_After_Blue/
├── aab/                    # the website (Netlify publish directory)
│   ├── index.html          # Home
│   ├── report.html         # Report: map, swipe, side-by-side
│   ├── method.html         # Method
│   ├── sources.html        # Data sources
│   ├── about.html          # Team and project
│   ├── css/                # page styles
│   ├── js/                 # app, common and home scripts
│   ├── data/               # JSON and GeoJSON results and metadata
│   ├── img/                # radar PNGs, history images, team photos
│   ├── downloads/          # case study report PDF
│   └── History-Py/         # history export script
└── netlify.toml            # publish = "aab"
```

The result numbers shown in the app are read from the JSON files in `aab/data/`, so the figures stay consistent across pages.

## Running locally

This is a static site with no build step. Serve the `aab` folder with any static server, for example:

```bash
cd aab
python -m http.server 8000
```

Then open http://localhost:8000. Opening `index.html` directly from disk will not work, because the pages load their JSON data with `fetch` and need a server.

Deployment is configured for Netlify in `netlify.toml`, with the publish directory set to `aab`.

## Tech

- HTML, CSS and JavaScript
- Leaflet 1.9.4 for the interactive Report map
- Search_Data Api
- GeoJSON and JSON data rendered client-side
- Netlify static hosting

## Limitations

These are stated in the app and are worth repeating here:

- The after scene is four days past the reported peak. Flash-flood water recedes quickly, so little standing water remained to image. No satellite covered the area between 19 and 24 July, so the peak was never observed.
- Radar cannot separate debris-laden floodwater from other kinds of surface change.
- Roughly 14% of the study area is masked by radar shadow and layover in the steep terrain.
- Narrow tributary channels can fall below the 10 m grid and the 400 m² minimum mapping unit.
- The data are provisional, and the result has not been checked against independent optical imagery or field observations. The event is corroborated only qualitatively by the PDMA KP situation report.

## Team - dnov_1

- Tamreena Tashfeen: Project Lead & Director
- Syed Saim Ali: SAR Pipeline & Geospatial Processing Engineer
- Mamuna Ahmad: Research & Product Validation Lead
- Muhammad Ayan Toqeer: Coordination & Operations Lead
- Sharmeen Shahid: Shahid	Scientific Reporting Specialist


## Data sources and acknowledgement

- NISAR (NASA-ISRO SAR mission): https://nisar.jpl.nasa.gov/
- ASF Vertex (scene search and download): https://search.asf.alaska.edu/
- NASA Earthdata: https://www.earthdata.nasa.gov/
- PDMA Khyber Pakhtunkhwa (event reference): https://www.pdma.gov.pk/

> Contains modified data from the NASA-ISRO Synthetic Aperture Radar (NISAR) mission, provided by the ASF DAAC. Imagery for this study was searched and obtained from ASF Vertex. Flood event details referenced from the Provincial Disaster Management Authority, Khyber Pakhtunkhwa.

