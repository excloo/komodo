# Homelab Docker

This repository owns the Docker Compose implementations deployed by the
[homelab](https://github.com/maxexcloo/homelab) configuration. Each service
lives in a root-level directory containing its Compose templates and supporting
files.

Deployments are published as target-specific OCI packages. They contain
SOPS-encrypted configuration that doco-cd can pull, decrypt, and reconcile
locally without remote Docker access or a 1Password credential.

## Deployment Flow

1. The homelab repository publishes non-secret Docker config v2 through the
   `CONFIG` repository variable.
2. GitHub Actions renders each configured target, resolves its `op://`
   references, and encrypts every deployment file with the target's age
   recipient. Doco-cd discovery metadata remains readable.
3. The workflow publishes one OCI package per target to GHCR, tagged with both
   the commit revision and `main`.
4. Doco-cd pulls the package and reconciles the services on that target.

## Repository Layout

- `<service>/` — Compose templates and service-owned files.
- `.github/scripts/render.py` — validates Docker config and renders encrypted
  target packages.
- `.github/workflows/render.yaml` — checks, renders, and publishes packages.
- `.render/` — ephemeral rendered output; never committed.

Files ending in `.tmpl` are rendered with gomplate. The deployment context is
available through `DEPLOYMENT`, with service-wide generated settings under
`custom.<service>`.

## Development

```bash
mise run setup    # Install Git hooks
mise run check    # Run all repository checks
mise run fmt      # Format supported files
mise run cleanup  # Remove generated output and caches
```

To add a service, create its root directory, add the required templates, and
configure its deployment in the homelab repository. Shared rendering and
workflow code should not require service-specific changes.

## Licence

AGPL-3.0 - see [LICENSE](LICENSE).
