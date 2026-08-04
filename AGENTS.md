# AGENTS.md

## Structure

- Keep each service implementation in `<service>/`.
- Put generated deployment artifacts in `<target>/<service>/`.
- Keep repository tooling generic; adding a service must not require changing shared workflow logic.
- Treat generated target directories and `.doco-cd.<target>.yml` as pipeline output.

## Secrets

- Keep 1Password access in GitHub Actions; never give doco-cd a 1Password credential.
- Use `*.secret.tmpl` only for outputs that must be injected and SOPS-encrypted.
- Never write injected plaintext secrets to disk, logs, artifacts, or commits.
- Keep one age recipient per deployment target.

## Style

- Keep Python helpers and constants sorted; keep `main()` and its execution guard last.
- Sort mise tools, tasks, workflow structure, Renovate rules, and Prek hooks consistently with the homelab repository.
- Prefer direct code and standard tools over repository-specific abstractions.

## Verification

- Run `mise run check` before handoff.
- Shadow-render to `.render/` before changing generated deployment artifacts.
