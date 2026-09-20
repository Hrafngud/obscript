# Technical Visual Language

Use this vocabulary to turn technical narration into an observable model. First identify the entities, relationships, changing state, and important variable; then choose the smallest visual grammar that explains them. Do not combine several diagram types merely for variety.

## Match the abstraction to the concept

| Concept to explain | Useful abstraction | Meaningful animation |
| --- | --- | --- |
| Data, requests, messages, events | Directed paths with bright traveling tokens, dots, packets, or pulses | Follow one token; fork, merge, transform, reject, retry, queue, or arrive |
| Ordered processing | Pipeline, conveyor, or linked stages | Carry one persistent object through stages and visibly change it at each step |
| Hierarchy, recursion, inheritance, filesystem | Rooted tree | Grow the relevant branch, traverse a path, expand children, or collapse detail |
| Dependencies, networks, services, relationships | Node-link graph or topology map | Build connections progressively, highlight the active route, reroute, isolate, or propagate failure |
| State and control logic | State machine, decision tree, gates, switches, or branching track | Move a persistent marker between states and show the exact trigger for each transition |
| Concurrency and scheduling | Parallel lanes, threads, swimlanes, or a shared-resource track | Run events concurrently, synchronize at a barrier, race, block, or contend for a resource |
| Waiting and backpressure | Queue, buffer, stack, reservoir, or narrowing channel | Accumulate items, slow their exit, overflow, drain, or expose a bottleneck |
| Layers and encapsulation | Nested shells, stacked planes, cutaway, or zoom through boundaries | Peel layers, descend through abstraction levels, cross a boundary, or reveal hidden internals |
| Transformation or compilation | Morphing object, staged assembly, parsing tree, or before/after state | Preserve visual identity while structure or representation changes step by step |
| Propagation and reach | Wave, ripple, branching pulse, diffusion field, or expanding frontier | Show origin, travel time, attenuation, amplification, and affected regions |
| Quantity, distribution, or change over time | Proportional bars, line chart, histogram, scatterplot, matrix, or heatmap | Build from the data, highlight the meaningful comparison, and animate only the changing variable |
| Scale, latency, capacity, or throughput | Meter, timeline, calibrated distance, channel width, token spacing, or rate counter | Change one encoded dimension while holding unrelated dimensions stable |
| Participant interactions, APIs, or protocols | Sequence diagram with labeled lifelines | Follow messages in causal order; reveal requests, responses, callbacks, retries, and timeouts |
| Distributed request latency | Trace waterfall with nested spans | Expand one request into its spans, align them to a shared time axis, and isolate the slow or failed branch |
| Runtime memory and references | Stack-and-heap map, object-reference graph, or allocation arena | Push and pop frames, allocate objects, follow references, and reclaim unreachable objects |
| Function execution and exceptions | Call-stack view | Add and remove frames in order, preserve the active frame, and stop where an exception originates |
| Code, configuration, schema, or state changes | Focused diff, overlay comparison, or staged replacement | Hold unchanged structure stable while changed fragments appear, move, or replace their predecessors |
| Async events, incidents, or deployments | Causal event timeline with linked milestones | Advance through events, connect supported causes to delayed consequences, and distinguish correlation from causation |
| Signals, clocks, polling, or debounce behavior | Timing diagram or waveform | Draw signals against one shared time axis and emphasize the edge, delay, or interval that changes the outcome |
| Performance hotspots | Flame graph, profile stack, or cost breakdown | Build nested work, zoom into the expensive branch, and keep measured width or area proportional to cost |
| Data provenance and transformation history | Data-lineage map | Follow one field or record from sources through transformations to its consumers |
| Version ancestry and merging | Commit or branch graph | Grow branches, mark commits, merge histories, and expose divergence or conflict |
| Recorded state and recovery | Event log with snapshots or replay strip | Apply events in order, restore a checkpoint, and replay later changes without confusing events with snapshots |
| Search, planning, or optimization | Search-space tree, explored frontier, candidate field, or path map | Expand candidates, distinguish queued, explored, rejected, and selected states, then reveal the winning path |
| Rules and feasible solutions | Constraint field, boundary map, or elimination funnel | Add constraints one at a time and visibly remove invalid regions or candidates |
| Resource contention | Lock, pool, quota, or shared-resource view | Converge actors on the scarce resource and show acquisition, waiting, release, timeout, or starvation accurately |
| Coordinate transforms | Aligned local, world, camera, and screen spaces | Keep one object identifiable as axes and coordinates transform between spaces |
| Data quality and schema drift | Record inspection lane, validation gates, or field-level comparison | Isolate missing, malformed, duplicated, anomalous, or newly shaped values at the exact check that detects them |
| Alternative outcomes | Counterfactual branch from a shared initial state | Hold the starting conditions constant, split factual and hypothetical paths, and mark the hypothetical path clearly |
| Uncertainty, estimates, or forecasts | Interval band, error bars, fan chart, ensemble dots, or probability distribution | Reveal the estimate and its range together; animate changes without implying unsupported precision |

## Choose the quantitative view by the question

Charts and graphs are first-class explanatory visuals, not dashboard filler. Use the simplest chart that makes the requested comparison observable, show axes or denominators when they matter, and direct attention to the relevant mark rather than animating every value. Build the chart from its data or transform an established object into it so it remains part of the visual argument.

| Question | Useful chart or graph | Use and animation guidance |
| --- | --- | --- |
| How does a value change over continuous time? | Line chart or smooth curve | Draw along the time axis, reveal meaningful bends or crossings, and avoid smoothing that invents intermediate values |
| How does a value change at discrete events? | Step chart, event plot, or timeline | Advance only at real event boundaries; label the trigger rather than implying continuous change |
| How do several series evolve? | Multiple lines, small multiples, slopegraph, or bump chart | Prefer direct labels and a stable scale; spotlight crossings, rank changes, or divergence instead of creating a tangled bundle |
| How much or how many? | Bar chart, dot plot, lollipop chart, or proportional symbols | Start quantitative axes at an honest baseline where appropriate and keep lengths or areas proportional |
| What makes up a whole? | Pie chart, donut chart, stacked bar, 100% stacked bar, treemap, or sunburst | Use pie or donut charts only for a small number of distinct parts of one complete whole; reveal slices from the same baseline and state the denominator |
| How does composition change over time? | Stacked area chart, streamgraph, or repeated 100% stacked bars | Keep category order and colors stable; choose normalized or absolute values explicitly |
| What is the distribution? | Histogram, dot/strip plot, box plot, violin plot, or density curve | Reveal range, clusters, outliers, and sample size; do not animate bins or smoothing in ways that alter the underlying distribution |
| Are two variables related? | Scatterplot, bubble plot, connected scatterplot, or fitted curve | Introduce points before a trend; distinguish measured observations from fitted or inferred relationships |
| Where is a value concentrated? | Heatmap, matrix, calendar heatmap, choropleth, or proportional-symbol map | Include an interpretable scale and avoid treating geographic area as magnitude unless area is the measurement |
| How does volume split or merge? | Sankey or alluvial diagram | Keep band width proportional to supported quantities and preserve category identity across splits and merges |
| What is the range or confidence? | Error bars, interval plot, confidence band, fan chart, or ensemble dots | Show central value and uncertainty together; explain the interval semantics when they are not obvious |
| How do controlled cases differ? | Small multiples or repeated frames | Hold scale, framing, baseline, and encodings constant while changing one meaningful variable per view |

Never use a 3D pie chart, tilted bars, perspective-distorted axes, or decorative extrusion when depth changes perceived quantities. If precise comparison matters, settle the chart front-facing before the viewer reads its values.

Arrows must state a real direction: data movement, control flow, dependency, causality, or navigation. Distinguish different relationship types through consistent line treatment, color, or arrowheads when the distinction matters. Do not surround every object with arrows.

Traveling bright dots or tokens represent discrete things such as packets, requests, events, records, tasks, or signals. Pulses or waves represent propagation or activation. Use them when something truly travels or spreads, not as ambient decoration. Keep a token visually persistent when the viewer must understand where it went or how it changed.

Use visual variables deliberately and consistently within the section:

- position and connection encode structure or relationship;
- direction encodes flow or influence;
- token spacing or arrival rate can encode throughput;
- motion duration can encode latency;
- line or channel width can encode capacity or volume;
- size can encode magnitude only when proportional comparison is intended;
- color can encode category, ownership, state, success, warning, or failure;
- brightness, pulse, or saturation can encode current activity or focus;
- opacity can suppress context while preserving orientation.

When an encoding is not immediately obvious, establish it with one short label, compact legend, or an introductory action. Preserve that mapping in later scenes rather than reassigning colors or shapes.

Do not make color carry a required distinction alone. Pair it with position, shape, line style, pattern, an icon, or a brief label. Keep labels and quantitative marks readable against the chosen background and after any camera move or perspective treatment.

## Use diagnostic and inspection views

Technical explanations often become engaging when the viewer investigates the system rather than merely observes it. Use a moving magnifying lens, synchronized detail inset, diagnostic probe, X-ray overlay, or semantic zoom to connect a visible surface action with its hidden mechanism. The inspected detail must correspond to the exact region or event under examination.

Use exploded views when component order, containment, or assembly matters. Separate components along a consistent axis while retaining their relationships, then reassemble them or activate the relevant part. A living blueprint may draw architecture first and then turn its lines and symbols into the functioning system; keep operational meaning more prominent than the blueprint style.

For failure explanations, show both the initiating fault and its consequences. A failure-propagation map can darken or isolate dependent components in supported causal order, then reverse or reroute them during recovery. Distinguish a confirmed failure path from a possible blast radius.

## Use depth, perspective, and 3D tilt purposefully

HyperFrames supports perspective, 3D transforms, tilted planes, parallax, and camera movement. Consider them when depth clarifies structure or makes a technical scene more tactile: layered architectures, stacked planes, exploded assemblies, isometric infrastructure, memory regions, spatial networks, coordinate systems, tilted interface surfaces, and transitions between overview and detail.

- Establish a readable front, top, or isometric relationship before moving the camera. Keep important objects anchored so the viewer retains orientation.
- Use 3D tilt to expose layers, hierarchy, containment, or a route through space; animate the camera or object around the explanatory action rather than leaving a decorative permanent skew.
- Use restrained parallax and occlusion to communicate depth. Preserve sufficient separation and contrast between planes.
- Bring dense text, code, axes, legends, and exact values toward a front-facing readable state before they must be read.
- Use depth-aware transitions: rotate a plane into the next interface, travel between stacked layers, pull an object out of a diagram, or match an isometric edge across scenes.
- Do not apply the same tilt to every scene, add depth that implies a nonexistent hierarchy, or use perspective that distorts quantitative comparisons.

## Animate comprehension

Construct complex diagrams in the order the viewer needs them. Start with the relevant node, path, state, or layer; add context only when it becomes explanatory. For a large tree or graph, reveal the active neighborhood, dim unrelated branches, and let the camera follow the current traversal. Avoid presenting a complete hairball and then trying to rescue it with labels.

Make invisible behavior visible through consequences. A blocked packet can rebound at a firewall; a cache hit can take a short illuminated route; backpressure can compress a queue upstream; a recursive call can unfold and fold a tree; two threads can converge on one contested lock; a failed service can darken dependent nodes in sequence. These moments may be playful, but every reaction must correspond to the real mechanism.

Keep one visual ontology across a coherent explanation. If circles are services and bright dots are requests, retain those identities across adjacent scenes. Morph an established object into a new representation only when the narration changes abstraction level, and make the transformation legible.

Create visual rhythm across the section by alternating useful viewpoints such as overview, operation, inspection, consequence, comparison, and synthesis. The alternation must follow the explanation; do not switch view types merely to create variety. Reuse the same entities and encodings across those viewpoints so the viewer does not have to relearn the system.

For comparisons, keep scale, framing, baseline, and visual encodings constant unless changing one of them is the point being explained. For uncertain quantities, show the uncertainty with the estimate rather than adding it later as a disclaimer. If a diagram requires many labels, a large legend, or several unrelated encodings to become intelligible, divide it into progressive states or multiple scenes.

## Prevent misleading diagrams

- Do not imply direction, causality, relative magnitude, timing, or simultaneity that the source does not support.
- Do not use faster motion merely for excitement when speed carries semantic meaning.
- Do not use a tree for a many-to-many graph, a linear pipeline for a cyclic process, or proportional sizing for unquantified importance.
- Do not mix data flow, control flow, and dependency edges without distinguishing them.
- Do not animate every edge at once. Direct attention to the path or change discussed by the narration.
- Do not replace a real interface demonstration with an abstract diagram when the observable user action is the explanation; combine them only when seeing both surface action and hidden mechanism adds clarity.

In `render_brief`, name what the abstraction represents, define any non-obvious encoding, and specify the explanatory sequence: initial state, trigger, path or transformation, consequence, focus change, and resolved state. The visible action—not a paragraph of labels—must carry the explanation.
