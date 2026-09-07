# Template Conventions

The project-level `templates/` directory contains shared layouts. App-specific
templates live below a directory named for the app, such as
`templates/core/smoke.html`. Static assets live in `static/` for project-wide
assets; Django also discovers an app's `static/` directory through the
`django.contrib.staticfiles` app.

`templates/base.html` is the shared full-page shell. A full-page response
extends it and supplies the `content` block. HTMX fragment templates are
partial markup files under the owning app's template directory. Fragments do
not extend `base.html` and contain only the element(s) that an HTMX request
should replace.

A view chooses the response shape from the request: ordinary requests render
the full-page template, while an HTMX request renders the corresponding
fragment. The foundation does not add state-changing HTMX actions; later
features should keep their full-page and fragment templates paired.

HTMX is loaded from the version-pinned jsDelivr URL in `base.html` with
Subresource Integrity (`integrity`) and anonymous cross-origin loading. Update
the URL and hash together when upgrading it.

The repository does not currently contain `_docs/design-system.md`; this
foundation therefore follows the existing Django architecture and keeps the
visual treatment limited to responsive, light CSS.
