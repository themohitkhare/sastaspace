# vulture_whitelist.py — False positives for vulture dead code analysis.
# These are used by frameworks (Click, FastAPI, Pydantic) via decorators/introspection.

# Click CLI commands (registered via @main.command decorator)
redesign_cmd  # noqa
list_cmd  # noqa
open_cmd  # noqa
remove_cmd  # noqa
serve_cmd  # noqa

# Pydantic settings / validators
model_config  # noqa
resolve_sites_dir  # noqa
parse_cors_origins  # noqa

# FastAPI route handlers (registered via @app.get/@app.post decorators)
redesign_endpoint  # noqa
job_stream_endpoint  # noqa
get_job_status  # noqa
list_jobs_endpoint  # noqa
list_sites_endpoint  # noqa
create_espocrm_lead  # noqa
crm_webhook  # noqa
admin_list_sites  # noqa
admin_sync  # noqa
serve_site  # noqa
serve_site_asset  # noqa

# Dataclass / model fields used via attribute access
favicon_url  # noqa
source_page  # noqa
pricing_model  # noqa
site_colors  # noqa
site_title  # noqa
checkpoint  # noqa
pages_crawled  # noqa
assets_count  # noqa
assets_total_size  # noqa
business_profile  # noqa

# Enum values used in comparisons
DISCOVERING  # noqa
DOWNLOADING  # noqa
ANALYZING  # noqa

# Functions called by other modules
extract_asset_urls  # noqa
sanitize_svg  # noqa
redesign_premium  # noqa

# Redis stream config
CONSUMER_PREFIX  # noqa
stream_name  # noqa
