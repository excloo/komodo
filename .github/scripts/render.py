import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

IDENTITY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def check_deployments(config):
    targets = {target["key"]: target for target in config["targets"]}
    with TemporaryDirectory() as directory:
        output_root = Path(directory)
        for deployment in sorted(config["deployments"], key=lambda item: item["key"]):
            target = targets[deployment["target"]]
            render_deployment(
                config,
                deployment,
                target,
                output_root,
                encrypt_files=False,
            )
            destination_root = output_root / target["key"] / deployment["service"]
            command = ["docker", "compose"]
            if (destination_root / ".env").is_file():
                command.extend(["--env-file", ".env"])
            command.extend(["-f", "compose.yaml", "config", "--quiet"])
            subprocess.run(command, check=True, cwd=destination_root)


def content_type(path):
    if path.name == ".env":
        return "dotenv"
    return {".json": "json", ".yaml": "yaml"}.get(path.suffix, "binary")


def encrypt(content, recipient, output_type):
    if b"{{ op://" in content:
        content = subprocess.run(
            ["op", "inject"],
            check=True,
            input=content,
            stdout=subprocess.PIPE,
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
    ).stdout


def render_deployment(config, deployment, target, output_root, encrypt_files=True):
    service_path = Path(deployment["service"])
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
            )
        else:
            content = source.read_bytes()

        destination = destination_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.name == ".doco-cd.yaml":
            destination.write_bytes(content)
        elif encrypt_files:
            destination.write_bytes(
                encrypt(content, target["age_public_key"], content_type(destination))
            )
        else:
            destination.write_bytes(content)


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
    if config.get("repository") != "docker":
        raise ValueError("Expected Docker config")

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
    deployment_target_keys = {deployment["target"] for deployment in deployments}
    if target_keys - deployment_target_keys:
        raise ValueError("Target has no deployments")

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    config = json.loads(os.environ["CONFIG"])
    validate(config)
    if args.check:
        check_deployments(config)
        return

    output_root = Path(".render")
    target_key = os.environ["TARGET"]
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
