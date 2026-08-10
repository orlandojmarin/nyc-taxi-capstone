# Capstone Presentation Outline

**Template:** The Hartford PowerPoint Template
**Duration:** 20 minutes + 5 minutes Q&A
**Presenters:** Orlando Marin, Ariana Lopez, Maryam Choudhury

---

## Slide 1: Title Slide
- **Layout:** Title Slide
- **Title:** [Team Name / Project Title]
- **Subtitle:** Orlando Marin, Ariana Lopez, Maryam Choudhury

---

## Slide 2: The Headline (Open with the Finding)
- **Layout:** One Column Content
- **Purpose:** State the year-over-year finding in the first 30 seconds
- **Content:**
  - One-sentence headline result (e.g., "Airport zone trips grew X% year over year while outer-borough demand declined")
  - Supporting number prominently displayed
  - Brief "so what" for the business audience
- **Speaker:** [Owner of opening and closing]

---

## Slide 3: Agenda
- **Layout:** Two Column Content (numbered items)
- **Content:**
  1. Our Question and Why It Matters
  2. Data and Architecture
  3. Data Quality
  4. Findings (Year-over-Year)
  5. Technical Deep Dive
  6. Future State and Recommendation

---

## Slide 4: The Question (2-3 min)
- **Layout:** One Column Content
- **Content:**
  - The analytical question in one sentence
  - Why a business person should care
  - How we will know we have answered it
  - Scope: Yellow + Green, Jan-May 2025 vs Jan-May 2026, 30M+ rows
- **Speaker:** [Presenter 1]

---

## Slide 5: The Data (part of 3-4 min block)
- **Layout:** Content and Picture or One Column Content
- **Content:**
  - What we were given: 20 Parquet files, 2 taxi types, 30M+ rows
  - Shape: schema differences between Yellow/Green, the 2025 schema change
  - Key stats: row counts, file sizes, date ranges
  - Zone lookup: 265 zones mapped to boroughs

---

## Slide 6: Architecture Diagram (part of 3-4 min block)
- **Layout:** Title Only (full-slide diagram)
- **Content:**
  - Architecture diagram (what we actually built)
  - Show: storage locations, processing steps, tools, data flow direction, orchestration entry point
  - Enough time for the audience to actually read it
- **Speaker:** [Presenter 2]

---

## Slide 7: Data Quality (2-3 min)
- **Layout:** One Column Content
- **Content:**
  - Summary: X rows in source, Y rows loaded, Z rows dropped, percentage
  - Top defects found (with counts):
    - Cash tip trap (acknowledged explicitly)
    - Timestamps outside file's month
    - Negative fares / zero-distance trips
    - [Additional defect not in catalog]
  - Decision for each: drop/correct/quarantine/keep with caveat
  - How remaining defects limit our conclusions
- **Speaker:** [Presenter 3]

---

## Slide 8: Findings - Year-over-Year (5-6 min)
- **Layout:** One Column Content with key metrics
- **Content:**
  - The defended YoY claim: "X changed by Y between 2025 and 2026"
  - Supporting evidence (chart/number)
  - Why the comparison is fair (same months, same filters, same vehicle types)
  - Confirmed it is not a data quality artifact
  - The "so what" for the business

---

## Slide 9: Dashboard (part of Findings block)
- **Layout:** Title Only (screenshot or live demo)
- **Content:**
  - Tableau/Looker dashboard connected to Snowflake gold models
  - Built for a business reader (point is clear without narration)
  - Labeled axes, clear chart titles that state the point
  - Backup: screenshots captured in case live demo fails

---

## Slide 10: Supporting Analysis (part of Findings block)
- **Layout:** One Column Content or Two Column Content
- **Content:**
  - Additional charts/findings that support the headline
  - Zone-level breakdown, time-of-day patterns, payment type shifts
  - Each chart title states the insight, not the mechanic

---

## Slide 11: Technical Deep Dive (3-4 min)
- **Layout:** One Column Content
- **Content:**
  - Pattern choice and why (Pattern A vs B, trade-offs)
  - dbt model layering: staging (views) vs marts (tables) and reasoning
  - Key SQL/transformation decisions
  - Warehouse sizing and auto-suspend settings
- **Speaker:** [Presenter 2 or technical owner]

---

## Slide 12: Cost and Performance (part of Deep Dive)
- **Layout:** One Column Content or Two Column Content
- **Content:**
  - Table types used (transient vs permanent) and why
  - Warehouse size choice and auto-suspend
  - File sizing and format handling on load
  - Materialization choices per model layer
  - What we would change at 10x volume

---

## Slide 13: Future State (1-2 min)
- **Layout:** One Column Content with 3 pillars
- **Content:**
  - Future state architecture diagram
  - What we would build next (e.g., incremental ingestion, orchestration, additional data sources)
  - Rough effort estimate
  - What it would cost

---

## Slide 14: Recommendation (1 min)
- **Layout:** One Column Content
- **Content:**
  - One clear recommendation for the client
  - Tied back to the finding
  - Actionable next step
- **Speaker:** [Owner of opening and closing]

---

## Slide 15: Thank You / Questions
- **Layout:** Title Slide
- **Title:** Thank You
- **Subtitle:** Questions?

---

## Presentation Assignments

| Section | Presenter | Target Minutes |
| :--- | :--- | :--- |
| Opening + Headline | | 0.5 |
| Question and why it matters | | 2-3 |
| Data and architecture | | 3-4 |
| Data quality | | 2-3 |
| Findings + dashboard | | 5-6 |
| Technical deep dive + cost | | 3-4 |
| Future state | | 1-2 |
| Recommendation + close | | 1 |

**Total target:** 18-20 minutes (leaves buffer)

---

## Prepared Answers for Expected Questions

- **"How do you know that number is right?"** (Have reconciliation evidence ready)
- **"What would you do differently?"** (Real answer, not modest deflection)
- **"Why did you choose Pattern A/B over the other?"** (Reference decision log)
- **"What is the cost of running this?"** (Cost rationale covers it)
- **"Could a data quality issue explain that finding?"** (Show the check)

---

## Rehearsal Schedule

- [ ] First full rehearsal (out loud, timed): Friday August 14
- [ ] Second rehearsal: Saturday/Sunday August 16-17
- [ ] Third rehearsal: Monday/Tuesday August 18
- [ ] Dashboard screenshots captured: before Friday freeze
- [ ] Handoff transitions practiced specifically
