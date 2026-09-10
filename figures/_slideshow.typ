#set page(width: 13.33in, height: 7.5in, margin: 1in, fill: rgb("#fafafa"))
#set text(font: "Helvetica Neue", size: 20pt)

#align(center + horizon)[
  #text(size: 40pt, weight: "bold")[Weekly Patterns — Figures]
]
#pagebreak()

#grid(
  rows: (auto, 1fr),
  row-gutter: 0.4in,
  align(center)[= Plot Pois By Dimension],
  align(center + horizon)[#image("plot_pois_by_dimension.png", height: 100%, width: 100%, fit: "contain")],
)
#pagebreak()

#grid(
  rows: (auto, 1fr),
  row-gutter: 0.4in,
  align(center)[= Plot Pois By Dimension Region 10],
  align(center + horizon)[#image("plot_pois_by_dimension_region_10.png", height: 100%, width: 100%, fit: "contain")],
)
#pagebreak()

#grid(
  rows: (auto, 1fr),
  row-gutter: 0.4in,
  align(center)[= Plot Pois By Dimension Top Category 10],
  align(center + horizon)[#image("plot_pois_by_dimension_top_category_10.png", height: 100%, width: 100%, fit: "contain")],
)
#pagebreak()

#grid(
  rows: (auto, 1fr),
  row-gutter: 0.4in,
  align(center)[= Plot Visits By Hour],
  align(center + horizon)[#image("plot_visits_by_hour.png", height: 100%, width: 100%, fit: "contain")],
)
#pagebreak()

#grid(
  rows: (auto, 1fr),
  row-gutter: 0.4in,
  align(center)[= Plot Visits By Hour Per Day],
  align(center + horizon)[#image("plot_visits_by_hour_per_day.png", height: 100%, width: 100%, fit: "contain")],
)
#pagebreak()
