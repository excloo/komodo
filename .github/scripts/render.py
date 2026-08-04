import json
import os
import re
import shutil
import subprocess
from pathlib import Path

IDENTITY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SERVICES_PATH = Path("templates/services")


def content_type(path):
    if path.name == ".env":
        return "dotenv"
    return {".json": "json", ".yaml": "yaml"}.get(path.suffix, "binary")


def encrypt(content, recipient, output_type):
    if "{{ op://" in content:
        content = subprocess.run(
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
            recipient,
            "--config",
            "/dev/null",
            "--input-type",
            output_type,
            "--output-type",
            output_type,
            "/dev/stdin",
        ],
        check=True,
        input=content,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout


def render_deployment(config, deployment, target, output_root):
    service_path = SERVICES_PATH / deployment["service"]
    if not service_path.is_dir():
        raise FileNotFoundError(f"Service not found: {deployment['service']}")

    destination_root = output_root / target["key"] / deployment["service"]
    context = dict(deployment, target_config=target, vaults=config["vaults"])
    environment = os.environ | {
        "DEPLOYMENT": json.dumps(context, separators=(",", ":"))
    }

    for source in sorted(service_path.rglob("*")):
        if not source.is_file():
            continue

        relative_path = source.relative_to(service_path)
        if source.suffix == ".tmpl":
            relative_path = relative_path.with_suffix("")
            content = subprocess.check_output(
                ["gomplate", "--file", source],
                env=environment,
                text=True,
            )
        else:
            content = source.read_text()

        destination = destination_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.name == ".doco-cd.yaml":
            destination.write_text(content)
        else:
            destination.write_text(
                encrypt(content, target["age_public_key"], content_type(destination))
            )


def render_metadata(target, output_root):
    (output_root / target["key"] / ".doco-cd.yaml").write_text(
        "version: doco.v1\n"
        "working_dir: .\n\n"
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
    for collection in (deployments, targets):
        keys = [item["key"] for item in collection]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate config key")
        if not all(IDENTITY_PATTERN.fullmatch(key) for key in keys):
            raise ValueError("Invalid config key")

    target_keys = {target["key"] for target in targets}
    if any(deployment["target"] not in target_keys for deployment in deployments):
        raise ValueError("Deployment has no target")

    service_paths = [
        f"{deployment['target']}/{deployment['service']}" for deployment in deployments
    ]
    if len(service_paths) != len(set(service_paths)):
        raise ValueError("Duplicate service on target")
    if not all(
        IDENTITY_PATTERN.fullmatch(deployment["service"]) for deployment in deployments
    ):
        raise ValueError("Invalid service identity")


def main():
    config = json.loads(os.environ["CONFIG"])
    output_root = Path(".render")
    target_key = os.environ["TARGET"]
    validate(config)

    targets = {target["key"]: target for target in config["targets"]}
    if target_key not in targets:
        raise ValueError(f"Target not found: {target_key}")
    target = targets[target_key]

    shutil.rmtree(output_root / target_key, ignore_errors=True)
    (output_root / target_key).mkdir(parents=True)
    render_metadata(target, output_root)

    for deployment in sorted(config["deployments"], key=lambda item: item["key"]):
        if deployment["target"] == target_key:
            render_deployment(config, deployment, target, output_root)


if __name__ == "__main__":
    main()
