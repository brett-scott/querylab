# QueryLab design concepts

Three desktop workspace concepts created collaboratively by the UI Designer and UX Researcher, rendered with the built-in image_gen tool on 17 October 2026. They show the same challenge and exploratory SQL/result state so the layout differences are comparable.

| Concept | Image | Main priority |
| --- | --- | --- |
| 1. Midnight Workbench | [PNG](querylab-01-midnight-workbench.png) | Dark editor-focused workspace with persistent brief and schema |
| 2. Field Notes | [PNG](querylab-02-field-notes.png) | Warm scenario-led workspace with business rules beside code |
| 3. Data Atlas | [PNG](querylab-03-data-atlas.png) | Light schema-led workspace with visible relationships |
| 4. Focused Midnight Workbench (selected revision) | [PNG](querylab-04-focused-workbench.png) | Short challenge overview and wide editor; rules/schema/results disclosed on demand |

Supporting artifacts: [design directions](querylab-concept-directions.md), [UX hypotheses and validation plan](querylab-ux-concept-notes.md), [exact generation prompts](querylab-image-prompts.md).

The user selected concept 4 and authorized implementation, with [UI Designer review and interaction contract](../docs/ui-simplification-review.md) and [generation prompt](querylab-04-focused-workbench.md). This keeps the Midnight identity while superseding its expanded three-pane default. Helper browser permission testing, distribution trials and the remaining nine challenges stay on the delivery backlog. Implementation evidence belongs in the [focused UI QA report](../docs/focused-ui-qa.md).

These are visual directions, not implemented screens, final database contracts or usability-tested interfaces. All three show practice results explicitly marked not graded. Generated schema columns, keys and relationship details vary between images and must be reconciled with the authored dataset before implementation; image 2's refund linkage especially is illustrative. Generated text, iconography and styling are subject to implementation review. Accessibility, responsive behavior, focus handling, result truncation, reset confirmation and running/cancel/error/expiry states require interactive validation.

Original selection: **Midnight Workbench**, confirmed on 17 October 2026. Its dark charcoal/mint identity is retained in the subsequently selected **Focused Midnight Workbench**. The revision makes supporting panels optional and supersedes the permanent expanded schema/results layout. Field Notes and Data Atlas remain alternative explorations.
