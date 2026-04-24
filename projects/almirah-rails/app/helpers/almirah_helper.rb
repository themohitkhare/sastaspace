# frozen_string_literal: true

module AlmirahHelper
  # Render a garment silhouette SVG by kind.
  # All path data ported from item-shapes.tsx.
  def item_silhouette_svg(kind, size: 80, color: "currentColor", **attrs)
    paths = SILHOUETTE_PATHS.fetch(kind.to_s, SILHOUETTE_PATHS["shirt"])
    html_attrs = attrs.merge(
      viewBox: "0 0 100 100",
      width: size,
      height: size,
      style: "color: #{color};",
      "aria-hidden": "true"
    )
    content_tag(:svg, html_attrs) do
      raw(paths)
    end
  end

  # Render an item card div (tonal background + silhouette + label).
  # Mirrors <ItemCard> from item-card.tsx.
  def item_card_html(item_or_gap, size: :md, note: nil, faded: false, selected: false, name_override: nil)
    is_item = item_or_gap.respond_to?(:tone_bg)
    tone_bg = is_item ? item_or_gap.tone_bg : Item::TONE_BG.fetch(item_or_gap[:tone] || item_or_gap["tone"] || "warm", "#f5f1e8")
    kind    = is_item ? item_or_gap.kind : (item_or_gap[:kind] || item_or_gap["kind"] || "shirt")
    label   = name_override || (is_item ? item_or_gap.name.split.first(2).join(" ") : (item_or_gap[:name] || item_or_gap["name"]))

    pad         = { sm: "8px", md: "12px", lg: "18px" }.fetch(size, "12px")
    name_fs     = { sm: 9, md: 10, lg: 10 }.fetch(size, 10)
    sil_maxh    = { sm: 80, md: 130, lg: 180 }.fetch(size, 130)
    card_class  = "item-card"
    card_class += " item-card--sm" if size == :sm
    card_class += " item-card--lg" if size == :lg
    card_class += " item-card--selected" if selected
    card_class += " item-card--faded"    if faded

    content_tag(:div, class: card_class,
                      style: "background: #{tone_bg}; border: #{selected ? '1.5px solid var(--brand-sasta)' : '1px solid var(--brand-dust-40)'}; padding: #{pad};") do
      safe_join([
        content_tag(:div, class: "item-card__silhouette") do
          content_tag(:svg, viewBox: "0 0 100 100", width: "100%", height: "100%",
                            preserveAspectRatio: "xMidYMid meet",
                            style: "max-height: #{sil_maxh}px;", "aria-hidden": "true") do
            raw(SILHOUETTE_PATHS.fetch(kind.to_s, SILHOUETTE_PATHS["shirt"]))
          end
        end,
        (label.present? ? content_tag(:div, label, class: "item-card__name #{"item-card__name--sm" if size == :sm}") : "".html_safe),
        (note.present? ? content_tag(:div, note, class: "item-card__note") : "".html_safe),
      ])
    end
  end

  SILHOUETTE_PATHS = {
    "kurta" => <<~SVG,
      <g stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M50 8 V14"/>
        <path d="M35 18 Q50 12 65 18"/>
        <path d="M35 18 L22 28 L28 36 L36 30 V86 H64 V30 L72 36 L78 28 L65 18"/>
        <path d="M50 18 V86"/>
      </g>
    SVG
    "saree" => <<~SVG,
      <g stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M50 8 V14"/>
        <path d="M32 20 Q50 14 68 20"/>
        <path d="M32 20 L28 90 H72 L68 20"/>
        <path d="M56 22 Q72 34 66 62 Q60 80 58 90" stroke-dasharray="2 3"/>
        <path d="M34 38 H66 M34 58 H66 M34 78 H66" stroke-dasharray="1 4"/>
      </g>
    SVG
    "blouse" => <<~SVG,
      <g stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M50 8 V14"/>
        <path d="M36 18 Q50 12 64 18"/>
        <path d="M36 18 L26 30 L32 38 L38 32 V58 H62 V32 L68 38 L74 30 L64 18"/>
      </g>
    SVG
    "dupatta" => <<~SVG,
      <g stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M50 8 V14"/>
        <path d="M30 18 Q50 14 70 18"/>
        <path d="M30 18 Q24 60 32 90 H68 Q76 60 70 18"/>
        <path d="M34 82 l2 6 M42 86 l2 6 M50 84 l2 8 M58 86 l2 6 M66 82 l2 6"/>
      </g>
    SVG
    "sherwani" => <<~SVG,
      <g stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M50 8 V14"/>
        <path d="M35 18 Q50 12 65 18"/>
        <path d="M35 18 L24 30 V86 H76 V30 L65 18"/>
        <path d="M50 18 V86"/>
        <path d="M48 30 L52 30 M48 42 L52 42 M48 54 L52 54 M48 66 L52 66"/>
      </g>
    SVG
    "shirt" => <<~SVG,
      <g stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M50 8 V14"/>
        <path d="M36 18 Q50 12 64 18"/>
        <path d="M36 18 L24 28 L30 36 L38 30 V72 H62 V30 L70 36 L76 28 L64 18"/>
        <path d="M44 18 L50 26 L56 18"/>
      </g>
    SVG
    "jeans" => <<~SVG,
      <g stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M50 8 V14"/>
        <path d="M36 18 H64"/>
        <path d="M36 18 L32 90 H46 L50 40 L54 90 H68 L64 18"/>
        <path d="M36 28 H64"/>
      </g>
    SVG
    "lehenga" => <<~SVG,
      <g stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M50 8 V14"/>
        <path d="M38 18 Q50 14 62 18"/>
        <path d="M38 18 L36 34 H64 L62 18"/>
        <path d="M36 34 L22 90 H78 L64 34"/>
        <path d="M30 60 H70 M26 76 H74"/>
      </g>
    SVG
    "juttis" => <<~SVG,
      <g stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 70 Q28 54 44 56 L44 68 L18 72 Z"/>
        <path d="M54 68 L54 56 Q70 54 80 70 L80 72 L54 68 Z"/>
        <path d="M32 60 l0 4 M64 60 l0 4"/>
      </g>
    SVG
    "jacket" => <<~SVG,
      <g stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M50 8 V14"/>
        <path d="M34 18 Q50 12 66 18"/>
        <path d="M34 18 L22 30 L30 42 L38 34 V78 H62 V34 L70 42 L78 30 L66 18"/>
        <path d="M42 18 L50 32 L58 18"/>
        <path d="M50 32 V78"/>
      </g>
    SVG
  }.freeze

  # Rack label → display name
  RACK_LABELS = {
    "ethnic"  => "Ethnic",
    "office"  => "Office",
    "weekend" => "Weekend",
  }.freeze

  # Tab bar links
  TABS = [
    { key: "rack",     label: "rack",    path_helper: :root_path,    icon: :rack    },
    { key: "today",    label: "today",   path_helper: :today_path,   icon: :star    },
    { key: "plan",     label: "plan",    path_helper: :plan_path,    icon: :plan    },
    { key: "discover", label: "find",    path_helper: :discover_path, icon: :shop   },
    { key: "me",       label: "me",      path_helper: :profile_path,  icon: :person },
  ].freeze

  def tab_icon_svg(key)
    case key.to_s
    when "rack"
      %(<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>)
    when "star"
      %(<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/></svg>)
    when "plan"
      %(<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>)
    when "shop"
      %(<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>)
    when "person"
      %(<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>)
    else
      %(<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"/>)
    end
  end
end
