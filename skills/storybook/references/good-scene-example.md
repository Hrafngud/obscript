# Good scene example

Use this as a quality bar for completeness and internal agreement, not as a reusable layout, subject, asset set, or animation recipe. A good scene resolves all five pillars around one visible idea, then makes every production field describe that same idea.

In this example, the narration distinguishes making a database faster from avoiding repeated database work. The visual therefore shows two requests from the same starting point: the first takes the long route to the database and populates the cache; the second visibly terminates at the cache while the database remains inactive.

```json
{
  "id": "scene-001",
  "order": 1,
  "script_section_id": "cache-mechanism",
  "voiceover": {
    "text": "O cache não acelera o banco de dados; ele evita que a mesma consulta precise chegar até ele de novo.",
    "estimated_seconds": 8
  },
  "timing": {
    "estimated_start_seconds": 0,
    "estimated_end_seconds": 8
  },
  "narrative_beat": "Replace the speed myth with the reuse mechanism",
  "visual_goal": "See the second request stop before the database",
  "design_pillars": {
    "context": {
      "narration_claim": "A cache reduces repeated database work by answering a repeated query before it reaches the database.",
      "visible_evidence": "The first request reaches the database and fills the cache; the identical second request ends at the cache while the database stays inactive.",
      "accuracy_guardrail": "Show a relative route difference only; do not imply that the database itself becomes faster or invent a numeric latency improvement."
    },
    "assets": {
      "search_queries": [
        "cache database request",
        "server latency clock",
        "dark texture background"
      ],
      "candidates_considered": [
        "/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/ilustrations/cache.svg",
        "/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/ilustrations/database.png",
        "/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/ilustrations/SERVER.png",
        "/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/background1/black_mamba.png"
      ],
      "selected_assets": [
        {
          "path": "/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/ilustrations/cache.svg",
          "usage": "foreground",
          "semantic_role": "The decision point that stores the first result and intercepts the repeated request."
        },
        {
          "path": "/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/ilustrations/database.png",
          "usage": "foreground",
          "semantic_role": "The expensive downstream destination reached only by the first request."
        },
        {
          "path": "/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/background1/black_mamba.png",
          "usage": "background",
          "semantic_role": "A low-contrast tiled ground that gives the request paths and state changes a stable visual field."
        }
      ],
      "exception_reason": ""
    },
    "animation": {
      "explanatory_change": "A first request misses the empty cache, returns from the database, and leaves a stored copy; an identical second request then resolves at the cache without activating the database.",
      "attention_path": "Follow the first token from left to cache to database and back, then reset to the same left origin and follow the second token only as far as the now-active cache."
    },
    "visual_abstraction": {
      "primitive": "Two-pass pipeline with persistent request tokens and a stateful cache node",
      "semantic_mapping": "Blue circles are identical query requests; the cache glow means that query is stored; the long branch leads to the database; the short terminating branch represents a cache hit; route length communicates relative work, not measured time."
    },
    "directness": {
      "attention_anchor": "The second blue request stops and resolves inside the glowing cache while the database remains visibly dormant.",
      "mute_read": "The first request must visit the database, but the repeated request is answered earlier by the cache."
    }
  },
  "composition": {
    "layout": "Use one left-to-right depth path: request origin at 12% width, cache large at 46%, and database smaller and deeper at 82%. Curve the return path above the outbound path so the stored result remains legible without a split screen.",
    "focal_element": "The cache changing from empty outline to active stored state, then stopping the second request",
    "supporting_elements": [
      "Two identical blue request tokens launched from the same origin",
      "Long database branch that dims after the first pass",
      "Short return arc carrying one result copy into the cache"
    ]
  },
  "visual_elements": [
    {
      "type": "foreground illustration",
      "content": "/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/ilustrations/cache.svg",
      "role": "Stateful cache node; animate its internal fill and outline glow when the first result is stored."
    },
    {
      "type": "foreground illustration",
      "content": "/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/ilustrations/database.png",
      "role": "Downstream database; activate once for the miss and remain inactive for the hit."
    },
    {
      "type": "raster background",
      "content": "/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/background1/black_mamba.png",
      "role": "Subtle full-frame tiled texture behind the route."
    },
    {
      "type": "data tokens and paths",
      "content": "Two identical blue circles, one amber result square, and directed route strokes",
      "role": "Make the two-pass request behavior visible without explanatory prose."
    }
  ],
  "onscreen_text": [
    {
      "text": "MISS",
      "purpose": "Identify the first cache state at the moment the request continues downstream."
    },
    {
      "text": "HIT",
      "purpose": "Identify the changed cache state when the repeated request terminates early."
    }
  ],
  "animation": {
    "entrance": "At 0.0 seconds, reveal the empty cache and dormant database by drawing the single route from left to right; introduce no title card.",
    "continuous": "From 0.6 to 3.8 seconds, move the first blue request into the cache, flash MISS, continue it to the database, then return one amber result square along the upper arc and lock a copy inside the cache. From 4.4 to 6.7 seconds, launch an identical second blue request from the same origin and stop it inside the cache.",
    "emphasis": "At 6.0 seconds, change MISS to HIT, brighten the stored square and cache outline, dim the database and its branch, and pulse the short completed route once.",
    "exit": "From 7.2 to 8.0 seconds, hold the resolved request inside the cache and let the unused database branch recede without removing the spatial relationship.",
    "camera": "Track the first token on the long route, ease back to the shared origin for the second pass, then settle in a tighter frame containing the active cache and dormant database together."
  },
  "transition_out": "None",
  "asset_requirements": [
    {
      "type": "foreground cache illustration",
      "description": "/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/ilustrations/cache.svg; inline or layer it so the outline and stored-state fill can animate independently."
    },
    {
      "type": "foreground database illustration",
      "description": "/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/ilustrations/database.png; preserve its aspect ratio and use brightness to distinguish active from dormant state."
    },
    {
      "type": "raster background",
      "description": "/home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/background1/black_mamba.png; tile beyond the full frame at its natural pattern scale and darken it for foreground contrast."
    }
  ],
  "render_brief": "Tile /home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/background1/black_mamba.png beyond the full frame at its natural 192 × 192 pattern scale and darken it so the route remains dominant. Place /home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/ilustrations/cache.svg large at 46% width and /home/zalmo/documents/obsidian/Videos/Videos/Globals/assets/ilustrations/database.png smaller and deeper at 82%, with one directed path entering the cache and continuing to the database. At 0.6 seconds, follow a blue request token into the empty cache; flash 'MISS', continue the same token to the database, and return an amber result square along a separate upper arc. At 3.4 seconds, lock a copy of that square inside the cache and brighten its outline. At 4.4 seconds, return the camera to the unchanged request origin and launch an identical blue token. Stop it inside the cache, replace 'MISS' with 'HIT', pulse the short completed route, and keep the database and its branch dormant. Hold both nodes in frame through 8.0 seconds so the viewer reads avoided database work rather than a faster database. End with no transition."
}
```

Why this works:

- **Context controls the design:** the accuracy guardrail prevents a visually tempting but false speed claim.
- **Assets are searched, verified, and active:** the cache and database are structural actors; the background supports contrast but does not count as the contextual foreground asset.
- **Motion carries the explanation:** the scene changes from miss to stored state to hit. Removing that sequence destroys the meaning.
- **The abstraction is explicit and stable:** tokens, paths, glow, and route length each have one declared meaning.
- **The anchor passes the mute test:** the repeated token stopping at the cache is understandable without turning the narration into text.

Do not copy the two-pass pipeline when the narration calls for a hierarchy, comparison, state machine, diagnostic inspection, quantitative chart, or another primitive. Copy the discipline: one claim, verified assets with semantic jobs, one evolving mechanism, one stable visual mapping, and one dominant visible takeaway.
