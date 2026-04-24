# Session store configuration.
#
# Key: _sastaspace_session — shared across all path-routed apps on sastaspace.com
# so that a user signed in at sastaspace.com/sign-in stays signed in at
# sastaspace.com/almirah without any extra cookie dance.
#
# No `domain:` attribute — same-origin path routing means we never need it.
# httponly: true — always. The JS layer has no business reading the session.
# same_site: :lax — CSRF protection without breaking top-level navigation.

Rails.application.config.session_store :cookie_store,
  key: "_sastaspace_session",
  httponly: true,
  same_site: :lax,
  secure: Rails.env.production?
