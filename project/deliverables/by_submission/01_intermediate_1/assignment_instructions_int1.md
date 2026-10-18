# Intermediate 1 - assignment instructions (official)

Source: "CEE C181/C281 - Intermediate 1: Assignment Instructions" (course page, received 2026-10-18).
Wording below follows the original as closely as possible. Where this differs from the earlier guide-based
notes in this folder (`README.md`, `design_record_int1.md`), this file wins.

| Item | Detail |
|---|---|
| What | **Written proposal** for the continuing design project: explain the relevant concepts and how we will use them to investigate a focused traffic question, following the revised Design Project Guide |
| Deadline | **Oct 23, 2026, 23:59 Pacific Time (Friday)** |
| Code | **Not required** for this submission |
| Course weight | 10% of the course grade |
| Page budget | roughly **5 pages total, including references and the appendix** |

## Section 1 - Core concepts (45%)

Explain what the concepts are, how they work, and what assumptions they rely on. Establish the technical
foundation for the project. Include mathematical formulas where relevant, **define every symbol and unit**,
and connect the explanation to substantive sources.

- **Traffic mechanisms.** Explain the concepts needed for the question, such as car-following, headway and
  spacing, traffic flow and density, bottleneck capacity, queue formation, or the growth and decay of
  disturbances. Describe the **causal relationships** that motivate the expected traffic response.
- **Model formulation.** Present and explain the governing equations of a justified vehicle-motion model,
  such as the Intelligent Driver Model (IDM). Define its **states, inputs, parameters and units**; explain how
  **spacing, speed and relative speed** affect vehicle behavior. Support plausible parameter values or ranges
  with sources.

Scope rule: Section 1 explains the **established theory and mechanisms** only. The selected scenario,
implementation choices and proposed experiments go in Section 2.

## Section 2 - How you'll build upon them (40%)

Explain how we will apply, extend, connect or evaluate the concepts in our own project. **Link each important
design choice to a concept from Section 1** and describe the **evidence that would support or challenge** our
reasoning.

- **Focused question and prediction.** State **one** answerable operational or modeling question (example
  given: under what headway and demand conditions will a braking disturbance grow, decay or create a
  persistent queue?). **Predict the response before testing**, and explain why the selected model suggests it.
- **Minimum simulation design.** Describe a **bounded freeway segment** with **arrivals, exits, a bottleneck
  and a controlled ramp-entry queue**.
- **Feasibility and next steps.** Identify the next implementation tasks.

## References (7.5%)

Use a **consistent citation style**.

## Appendix (7.5%)

Keep this part short, roughly **half a page**. (Contents are not specified.)

## Also required (placement not specified)

- **For pairs:** name each student's component. Be responsible for what you submit.
- **AI-use disclosure:** in a few sentences, identify any AI tools used; if none were used, state that.

## Checklist

- [ ] About 5 pages total, including references and appendix
- [ ] Section 1, traffic mechanisms: concepts explained with their causal relationships
- [ ] Section 1, model formulation: governing equations; states, inputs, parameters and units; effect of spacing, speed and relative speed; sourced parameter values or ranges
- [ ] Section 1: every symbol and unit defined; substantive sources cited
- [ ] Section 1 contains no scenario, implementation choice or experiment
- [ ] Section 2: each important design choice linked to a Section 1 concept, with evidence that would support or challenge it
- [ ] Section 2: one focused question; prediction made before testing, with the model-based reason
- [ ] Section 2: bounded freeway segment with arrivals, exits, a bottleneck and a controlled ramp-entry queue
- [ ] Section 2: next implementation tasks
- [ ] References in one consistent citation style
- [ ] Appendix of about half a page
- [ ] Each student's component named
- [ ] AI-use disclosure
