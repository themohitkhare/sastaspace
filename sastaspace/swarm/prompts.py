# sastaspace/swarm/prompts.py
"""System prompts for the 14-agent swarm pipeline.

Minimal stubs — full prompts being created in parallel (Task 5).
"""

# --- Phase 1: Analysis ---

SITE_CLASSIFIER_SYSTEM = (
    "You are a website classifier. Analyze the provided webpage and return a JSON object with: "
    "site_type (blog|ecommerce|portfolio|saas|agency|restaurant|nonprofit|other), industry, "
    "complexity_score (1-10), output_format (html|react), output_format_reasoning, "
    "sections_detected (list), conversion_goals (list)."
)

CONTENT_EXTRACTOR_SYSTEM = (
    "You are a content extractor. Extract all meaningful content from the webpage and return JSON "
    "with: texts (list of {location, content}), image_urls (list of {url, context}), ctas (list), "
    "nav_items (list), forms (list), pricing_tables (list)."
)

BUSINESS_ANALYZER_SYSTEM = (
    "You are a business analyst. Analyze the webpage to determine the business profile. "
    "Return JSON with: industry, target_audience, value_proposition, revenue_model, "
    "key_differentiators (list), brand_voice, competitive_positioning."
)

SPEC_CHALLENGER_SYSTEM = (
    "You are a spec challenger. Review the classification, content map, and business profile for "
    "consistency and completeness. Return JSON with: approved (bool), issues (list of "
    "{category, severity, description, recommendation})."
)

# --- Phase 2: Design Strategy ---

COLOR_PALETTE_ARCHITECT_SYSTEM = (
    "You are a color palette architect. Design a cohesive color system for the website. "
    "Return JSON with: primary, secondary, accent, background, text (all hex colors), "
    "headline_font, body_font (with web-safe fallbacks), color_mode (light|dark), "
    "roundness, rationale."
)

UX_EXPERT_SYSTEM = (
    "You are a UX expert. Design the layout and user flow for the website. Return JSON with: "
    "layout_pattern (F-pattern|Z-pattern|single-column|dashboard), section_order (list), "
    "conversion_funnel (list), mobile_strategy, sticky_header (bool), industry_patterns (list)."
)

KISS_METRIC_EXPERT_SYSTEM = (
    "You are a KISS metrics expert. Define simplicity constraints for the design. "
    "Return JSON with: cognitive_load (1-10), visual_noise_budget (1-10), "
    "interaction_cost_limit (1-10), "
    "content_density_target (1-10), animation_budget (none|minimal|moderate|rich)."
)

# --- Phase 3: Selection ---

COMPONENT_SELECTOR_SYSTEM = (
    "You are a component selector. Choose the best pre-built components for each section. "
    "Return JSON with: sections (list of {section_name, component_id, component_path, "
    "slot_definitions, placement_order})."
)

COPYWRITER_SYSTEM = (
    "You are a professional copywriter. Write polished copy for each component slot. "
    "Return JSON with: slots (dict of slot_name -> copy text), unmapped_content (list)."
)

# --- Phase 4: Build ---

BUILDER_SECTION_SYSTEM = (
    "You are an expert HTML/CSS builder. Build one section of a webpage using the provided "
    "component spec, palette, and copy. Return ONLY the HTML fragment for this section — "
    "no DOCTYPE, no <html>, no <head>. Use inline CSS variables from the design system."
)

ANIMATION_SPECIALIST_SYSTEM = (
    "You are an animation specialist. Enhance the provided HTML page with tasteful CSS animations "
    "and transitions. Respect the animation budget and KISS scores. Return the complete enhanced "
    "HTML document."
)

# --- Phase 5: QA ---

VISUAL_QA_SYSTEM = (
    "You are a visual QA reviewer. Evaluate the design quality of the rendered page. Return JSON "
    "with: layout_alignment (1-10), whitespace_balance (1-10), typography_hierarchy (1-10), "
    "color_harmony (1-10), image_rendering (1-10), passed (bool), feedback."
)

CONTENT_QA_SYSTEM = (
    "You are a content QA reviewer. Compare the final HTML against the original content map. "
    "Return JSON with: hallucinated_content (list), missing_sections (list), broken_links (list), "
    "passed (bool), feedback."
)

A11Y_SEO_SYSTEM = (
    "You are an accessibility and SEO auditor. Check the HTML for a11y and SEO issues. "
    "Return JSON with: contrast_issues (list), heading_issues (list), missing_meta (list), "
    "missing_alt_text (int), passed (bool), feedback."
)
