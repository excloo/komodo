# Homelab Docker

Docker Compose service implementations and deployment templates live in this
repository. The homelab config supplies non-secret deployment instances and
programmatic 1Password references.

GitHub Actions renders target-specific OCI packages and SOPS-encrypts every
deployment file with the target's age recipient. Doco-cd pulls, decrypts, and
deploys them locally without a 1Password credential or remote Docker access.

Service source lives under `templates/services/`. Generated output exists only
in the pipeline and places each service directly at its OCI artefact root.

The renderer accepts Docker config v2. Service-wide generated settings are
provided on each deployment under `custom.<service>`.

## Licence

AGPL-3.0 - see [LICENSE](LICENSE).
