# Rental Radar — Presentation Guide & Speaker Notes

## Start here

Open `Rental_Radar_Stage_Ready.html` in Chrome or Edge. No installation is required for the saved example or the embedded model lab. Use the offline example during the timed presentation; live lookup is optional.

- Arrow keys / Space: navigate slides. F: fullscreen. O: overview. D: demo. N: speaker notes.
- Notes appear on the same screen as the presentation. Hide them before projecting; this is not a private presenter view.
- Use “Start 8:00” for rehearsal. Budget eight minutes for the presentation and two minutes for questions. The timings below are allocations, not a guarantee of reading duration: rehearse with the actual clicks.
- Suggested roles: Speaker A, slides 1–3; Speaker B, slides 4–5; Speaker C, slides 6–9. With two speakers, hand over after slide 5.

## 90-second pilot demo

1. **0–15 seconds:** On slide 4, select **Open pilot demo → Open example report**. Say: “This is a saved public-data snapshot for a real address, 3325 Neptune Avenue in Brooklyn. It is not a live inspection.”
2. **15–35 seconds:** Show the overview, then select **Heat & hot water**. Say: “We organize the records into issues a renter can understand and questions they can ask at a viewing.”
3. **35–60 seconds:** Select **See evidence** and expand a record. Say: “You can inspect the underlying evidence instead of trusting a summary alone. A complaint is not a verified violation, and a closed case does not prove a repair.”
4. **60–80 seconds:** Show the viewing checklist and select **Download viewing checklist**. Say: “The useful output is a practical checklist. Annual pest filings are tax-lot-level records, which may cover multiple buildings—not necessarily this apartment.”
5. **80–90 seconds:** Select **Back to slides**. Say: “The pilot helps renters ask better questions; it does not certify that a property is safe.”

Source links require internet access. The saved report, checklist and embedded model lab work offline. Do not depend on external pages during the timed demo.

## Slide-by-slide speaker notes

### Slide 1 — Introduction | 0:00–0:25

Today we are presenting Rental Radar. It helps renters understand public building records and prepare better questions before a viewing. We will show a working pilot, the models we have trained, the limitations, and our next steps.

### Slide 2 — User problem and scope | 0:25–1:05

The renter starts with an address. We bring together complaints, recorded violations and annual pest filings, then turn them into questions they can act on. A peer asked why we only cover New York City. It is a focused pilot with public datasets that share a tax-lot identifier. We must validate coverage separately before adding other cities.

### Slide 3 — Progress | 1:05–1:45

We have connected three data sources, created reproducible reports, and trained both XGBoost and a logistic baseline. The dataset has 125 tax lots and 2,750 monthly observations. Our stricter evaluation removes overlap between the 90-day label windows across splits and evaluates 625 held-out rows. We also have a usable report and checklist. Customer interviews and external LLM evaluation remain outstanding.

### Slide 4 — Pilot demo | 1:45–3:15

Follow the 90-second sequence above. Speak while demonstrating; do not read button instructions aloud. Emphasize the journey: address → understandable issue → inspectable evidence → useful viewing question.

### Slide 5 — Data and optional LLM | 3:15–4:10

Python collects and deduplicates records, calculates totals, and prepares historical model features. The optional LLM is designed to explain bounded evidence. It does not search the web or calculate counts. The prompt requires citations and forbids safety claims. We validate structure and citation IDs, but factual support still needs human review. The demo already works with rules, so we do not depend on an untested external model call. Actual LLM token usage and cost have not been measured.

### Slide 6 — Model evaluation | 4:10–5:15

Our ML task is narrow: predict a newly recorded Class C violation in the following 90 days. After removing target windows that cross split boundaries, the logistic baseline ranks cases better and has higher recall. XGBoost has higher precision and a lower Brier score. There is no universal winner. These results apply to a small cohort with HPD history, not every NYC rental. In Q&A, the model lab can run saved trees on actual held-out feature rows directly in the browser.

### Slide 7 — Customer discovery | 5:15–6:05

We have one recalled peer question: why NYC? We used it to explain the pilot scope. We are not presenting it as a completed interview study or a verified Plause record. The next sprint is five to eight short interviews. We will test whether renters understand evidence types and whether the checklist changes what they ask. We will record requested and rejected features, not just positive comments.

### Slide 8 — Risks | 6:05–6:55

The biggest risk is overinterpreting data. A tax lot can contain several buildings. Complaints are reports, annual filings are self-reported, and open or closed status may not reflect current conditions. Our report separates evidence types, shows dates and source links, and uses neutral questions. For the model, sampling bias and calibration still limit public use.

### Slide 9 — Next steps | 6:55–8:00

We will interview renters, improve building identity, broaden model evaluation and test a small pilot. We want feedback on whether this evidence report and viewing checklist is a useful MVP before investing in scoring or city expansion. Our immediate priority is usefulness and correct interpretation, not a universal safety score. We have reserved two minutes for questions.

## Optional live address lookup

Extract `Rental_Radar_App.zip`. Open a terminal in the extracted `Rental_Radar_App` folder containing `demo_server.py`. With Python 3.10 or later, run:

```text
python demo_server.py
```

Open `http://127.0.0.1:8766`, enter the demo and select **Look up another NYC address**. Enter a street number/name without an apartment number, select the borough and date range. Internet is required; an LLM API key is not required. The end date is exclusive; the supported window is at most 731 days. Exact address matching can miss aliases. No records does not mean no problems. If a source fails, return to the clearly labeled saved example.

The localhost address works only on the computer running the server. Teammates should open their own HTML copy or run their own extracted app; it is not a public deployment link.

## Optional model lab for Q&A

Choose a historical held-out case, select **Run the trained model**, then inspect its inputs and reveal the recorded outcome. This performs actual inference using the embedded XGBoost trees. It is not a current prediction for the demo address or an arbitrary newly entered address, and it is not a calibrated citywide safety score.

## Evidence and limits

The existing verification recorded 20 passing unit tests, 25 passing offline output/citation contract checks, and browser/Python agreement on 625 model cases (maximum probability difference about 2.49e-7). Contract checks are not external LLM quality evaluation. External LLM calls, measured LLM cost and formal renter interviews remain unfinished. Work is packaged locally; no GitHub push or PR has been made.
