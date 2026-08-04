# Homelab Docker

Docker Compose service implementations and deployment templates live in this
repository. The homelab config supplies non-secret deployment instances and
programmatic 1Password references.

GitHub Actions renders deployments and SOPS-encrypts only secret files with each
target's age recipient. Doco-cd decrypts and deploys them locally without a
1Password credential or remote Docker access.
