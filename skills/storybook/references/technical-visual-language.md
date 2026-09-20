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

## Animate comprehension

Construct complex diagrams in the order the viewer needs them. Start with the relevant node, path, state, or layer; add context only when it becomes explanatory. For a large tree or graph, reveal the active neighborhood, dim unrelated branches, and let the camera follow the current traversal. Avoid presenting a complete hairball and then trying to rescue it with labels.

Make invisible behavior visible through consequences. A blocked packet can rebound at a firewall; a cache hit can take a short illuminated route; backpressure can compress a queue upstream; a recursive call can unfold and fold a tree; two threads can converge on one contested lock; a failed service can darken dependent nodes in sequence. These moments may be playful, but every reaction must correspond to the real mechanism.

Keep one visual ontology across a coherent explanation. If circles are services and bright dots are requests, retain those identities across adjacent scenes. Morph an established object into a new representation only when the narration changes abstraction level, and make the transformation legible.

## Prevent misleading diagrams

- Do not imply direction, causality, relative magnitude, timing, or simultaneity that the source does not support.
- Do not use faster motion merely for excitement when speed carries semantic meaning.
- Do not use a tree for a many-to-many graph, a linear pipeline for a cyclic process, or proportional sizing for unquantified importance.
- Do not mix data flow, control flow, and dependency edges without distinguishing them.
- Do not animate every edge at once. Direct attention to the path or change discussed by the narration.
- Do not replace a real interface demonstration with an abstract diagram when the observable user action is the explanation; combine them only when seeing both surface action and hidden mechanism adds clarity.

In `render_brief`, name what the abstraction represents, define any non-obvious encoding, and specify the explanatory sequence: initial state, trigger, path or transformation, consequence, focus change, and resolved state. The visible action—not a paragraph of labels—must carry the explanation.
