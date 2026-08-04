import json
import os
import re
import shutil
import subprocess
from pathlib import Path

DEPLOYMENTS_PATH = Path("deployments")
IDENTITY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SERVICES_PATH = Path("services")


def encrypt(content, age_public_key, content_type):
    injected = subprocess.run(
        ["op", "inject"],
        check=True,
        input=content,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout
    return subprocess.run(
        [
            "sops",
            "--encrypt",
            "--age",
            age_public_key,
            "--config",
            "/dev/null",
            "--input-type",
            content_type,
            "--output-type",
            content_type,
            "/dev/stdin",
        ],
        check=True,
        input=injected,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout


def output_path(render_path, service_path, template):
    relative_path = template.relative_to(service_path)
    suffix = ".secret.tmpl" if template.name.endswith(".secret.tmpl") else ".tmpl"
    return render_path / str(relative_path)[: -len(suffix)]


def render_deployment(config, deployment, target, output_root, resolve_secrets):
    service_path = SERVICES_PATH / deployment["service"]
    if not service_path.is_dir():
        raise FileNotFoundError(f"Service not found: {deployment['service']}")

    render_path = output_root / DEPLOYMENTS_PATH / target["key"] / deployment["service"]
    shutil.copytree(
        service_path,
        render_path,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("*.tmpl"),
    )

    context = dict(deployment, target_config=target, vaults=config["vaults"])
    environment = dict(
        os.environ, DEPLOYMENT=json.dumps(context, separators=(",", ":"))
    )
    for template in sorted(service_path.rglob("*.tmpl")):
        rendered = subprocess.run(
            ["gomplate", "--file", template],
            check=True,
            env=environment,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout
        destination = output_path(render_path, service_path, template)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if template.name.endswith(".secret.tmpl"):
            if resolve_secrets:
                content_type = {
                    ".env": "dotenv",
                    ".yaml": "yaml",
                    ".yml": "yaml",
                }.get(destination.suffix, "binary")
                rendered = encrypt(rendered, target["age_public_key"], content_type)
        elif "op://" in rendered:
            raise ValueError(f"Secret reference in unencrypted output: {destination}")

        destination.write_text(rendered)


def render_metadata(targets, output_root):
    rules = "\n".join(
        f"  - age: {target['age_public_key']}\n"
        f"    path_regex: ^{DEPLOYMENTS_PATH}/{target['key']}/"
        for target in targets
    )
    (output_root / ".sops.yaml").write_text(f"creation_rules:\n{rules}\n")

    for path in output_root.glob(".doco-cd.*.yml"):
        path.unlink()
    for target in targets:
        (output_root / f".doco-cd.{target['key']}.yml").write_text(
            f"working_dir: {DEPLOYMENTS_PATH}/{target['key']}\n\n"
            "auto_discovery:\n"
            "  delete: true\n"
            "  depth: 1\n"
            "  enabled: true\n"
            "  remove_images: true\n"
            "  remove_volumes: false\n"
        )


def validate(config):
    if config.get("repository") != "docker" or config.get("version") != 1:
        raise ValueError("Expected Docker config version 1")

    deployments = config["deployments"]
    targets = config["targets"]
    for collection in [deployments, targets]:
        keys = [item["key"] for item in collection]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate config key")
        if not all(IDENTITY_PATTERN.fullmatch(key) for key in keys):
            raise ValueError("Invalid config key")

    target_keys = {target["key"] for target in targets}
    if any(deployment["target"] not in target_keys for deployment in deployments):
        raise ValueError("Deployment has no target")


def main():
    config = json.loads(os.environ["CONFIG"])
    output_root = Path(os.environ.get("OUTPUT_ROOT", "."))
    resolve_secrets = os.environ.get("RESOLVE_SECRETS", "true") == "true"
    validate(config)

    if not resolve_secrets and output_root == Path("."):
        raise ValueError("Unresolved secrets require a shadow output directory")

    output_root.mkdir(parents=True, exist_ok=True)
    targets = sorted(config["targets"], key=lambda target: target["key"])
    target_by_key = {target["key"]: target for target in targets}

    shutil.rmtree(output_root / DEPLOYMENTS_PATH, ignore_errors=True)

    render_metadata(targets, output_root)

    for deployment in sorted(config["deployments"], key=lambda item: item["key"]):
        render_deployment(
            config,
            deployment,
            target_by_key[deployment["target"]],
            output_root,
            resolve_secrets,
        )


if __name__ == "__main__":
    main()
