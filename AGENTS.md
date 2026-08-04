# AGENTS.md

## Structure

- Keep each service implementation in `templates/services/<service>/`.
- Put each rendered service at `/<service>/` in its target-specific OCI package.
- Keep repository tooling generic; adding a service must not require changing shared workflow logic.
- Treat `.render/` and OCI packages as pipeline output.

## Secrets

- Keep 1Password access in GitHub Actions; never give doco-cd a 1Password credential.
- SOPS-encrypt every rendered deployment file except `.doco-cd.yaml` discovery metadata.
- Never write injected plaintext secrets to disk, logs, packages, or commits.
- Keep one age recipient per deployment target.

## Style

- Keep Python helpers and constants sorted; keep `main()` and its execution guard last.
- Sort mise tools, tasks, workflow structure, Renovate rules, and Prek hooks consistently with the homelab repository.
- Use `.yaml`, never `.yml`.
- Prefer direct code and standard tools over repository-specific abstractions.

## Verification

- Run `mise run check` before handoff.
- Inspect every OCI layer before changing package visibility.
