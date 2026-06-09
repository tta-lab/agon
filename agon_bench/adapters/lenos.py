"""Harbor installed agent adapter for Lenos.

Mount your host lenos config into the container:
  harbor run ... \
    --mounts "[{\"type\":\"bind\",\"source\":\"${PWD}/agon_bench/lenos/config.json\",\"target\":\"/root/.config/lenos/config.json\",\"read_only\":true},{\"type\":\"bind\",\"source\":\"${HOME}/.local/share/lenos\",\"target\":\"/root/.local/share/lenos\",\"read_only\":true}]"

`agon_bench/lenos/config.json` is Agon's minimal non-secret options config.
`~/.local/share/lenos/config.json` contains host provider secrets; do not read it.
"""

import json
import os
import shlex
import base64

from harbor.agents.installed.base import (
    BaseInstalledAgent,
    CliFlag,
    with_prompt_template,
)
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


DEFAULT_LENOS_VERSION = "latest"
DEFAULT_ORGANON_VERSION = "latest"
DEFAULT_EINAI_VERSION = "v0.1.0"
DEEPSEEK_REASONING_EFFORT = "xhigh"
LENOS_REASONING_EFFORT = os.environ.get("LENOS_REASONING_EFFORT")
LENOS_NO_SANDBOX = os.environ.get("LENOS_NO_SANDBOX", "")

LENOS_VERSION = os.environ.get("LENOS_VERSION", DEFAULT_LENOS_VERSION)
LENOS_RELEASE_BASE = os.environ.get(
    "LENOS_RELEASE_BASE", "https://github.com/tta-lab/lenos/releases"
)
ORGANON_VERSION = os.environ.get("ORGANON_VERSION", DEFAULT_ORGANON_VERSION)
ORGANON_RELEASE_BASE = os.environ.get(
    "ORGANON_RELEASE_BASE", "https://github.com/tta-lab/organon/releases"
)
EINAI_VERSION = os.environ.get("EINAI_VERSION", DEFAULT_EINAI_VERSION)
EINAI_RELEASE_BASE = os.environ.get(
    "EINAI_RELEASE_BASE", "https://github.com/tta-lab/einai/releases"
)
EINAI_MODEL = os.environ.get("EINAI_MODEL", "deepseek/deepseek-v4-flash")
if LENOS_VERSION == "latest":
    LENOS_DOWNLOAD_URL = f"{LENOS_RELEASE_BASE}/latest/download"
else:
    LENOS_DOWNLOAD_URL = f"{LENOS_RELEASE_BASE}/download/{LENOS_VERSION}"
if ORGANON_VERSION == "latest":
    ORGANON_DOWNLOAD_URL = f"{ORGANON_RELEASE_BASE}/latest/download"
else:
    ORGANON_DOWNLOAD_URL = f"{ORGANON_RELEASE_BASE}/download/{ORGANON_VERSION}"
if EINAI_VERSION == "latest":
    raise ValueError(
        "EINAI_VERSION=latest is not supported because einai release asset names "
        "include the concrete version. Set EINAI_VERSION=v0.1.0 or another tag."
    )
EINAI_DOWNLOAD_URL = f"{EINAI_RELEASE_BASE}/download/{EINAI_VERSION}"
EINAI_ARCHIVE_VERSION = EINAI_VERSION.removeprefix("v")

TEMENOS_CONFIG = """\
# temenos config for Harbor Lenos agent
allow_env = [
  "PATH", "HOME", "USER", "SHELL",
  "LENOS_*",
]
allow_read = [
  "/usr/local/bin", "/usr/bin", "/bin",
  "/app", "/workspace",
  "/root/.config/lenos", "/root/.config/einai",
  "/root/.einai",
  "/tmp",
]
allow_write = [
  "/app", "/workspace",
  "/root/.einai",
  "/tmp",
]
"""

USAGE_SUMMARY_PATH = "/logs/agent/usage-summary.json"
TASK_CONTEXT_PATH = "/tmp/agon-task.md"
TASK_TRIGGER = "Start."


def _env_enabled(value: str | None) -> bool:
    return bool(value) and value.lower() not in {"0", "false", "no", "off"}


class LenosAgent(BaseInstalledAgent):
    """Lenos — terminal-first AI agent with self-contained sandboxing.

    Lenos config comes from the host, mounted at:
      agon_bench/lenos/config.json → non-secret options config
      ~/.local/share/lenos         → provider secrets and registry cache

    Run with:
      harbor run -d "terminal-bench@2.0" \\
        --agent-import-path agon_bench.adapters.lenos:LenosAgent \\
        -m deepseek-v4-flash \\
        -t terminal-bench/hello-world \\
        --mounts "[{\\"type\\":\\"bind\\",\\"source\\":\\"${PWD}/agon_bench/lenos/config.json\\",\\"target\\":\\"/root/.config/lenos/config.json\\",\\"read_only\\":true},{\\"type\\":\\"bind\\",\\"source\\":\\"${HOME}/.local/share/lenos\\",\\"target\\":\\"/root/.local/share/lenos\\",\\"read_only\\":true}]" \\
        -y
    """

    CLI_FLAGS = [
        CliFlag("model", cli="-m", type="str"),
    ]

    @staticmethod
    def name() -> str:
        return "lenos"

    def get_version_command(self) -> str | None:
        return "lenos --version"

    def parse_version(self, stdout: str) -> str:
        text = stdout.strip()
        for line in text.splitlines():
            line = line.strip()
            if line:
                return line.removeprefix("lenos ").split()[0]
        return text

    @staticmethod
    def _reasoning_flag_for_model(model_name: str | None) -> str:
        if LENOS_REASONING_EFFORT:
            return f" --reasoning-effort {shlex.quote(LENOS_REASONING_EFFORT)}"
        if not model_name:
            return ""
        if not model_name.split("/", 1)[-1].startswith("deepseek"):
            return ""
        return f" --reasoning-effort {shlex.quote(DEEPSEEK_REASONING_EFFORT)}"

    @staticmethod
    def _sandbox_flag() -> str:
        if _env_enabled(LENOS_NO_SANDBOX):
            return " --no-sandbox"
        return ""

    async def install(self, environment: BaseEnvironment) -> None:
        # Install system dependencies for sandboxing
        await self.exec_as_root(
            environment,
            command=(
                "if command -v apt-get &> /dev/null; then "
                "  apt-get update && apt-get install -y bubblewrap curl python3; "
                "elif command -v apk &> /dev/null; then "
                "  apk add --no-cache bubblewrap curl python3; "
                "elif command -v yum &> /dev/null; then "
                "  yum install -y bubblewrap curl python3; "
                "fi"
            ),
            env={"DEBIAN_FRONTEND": "noninteractive"},
        )

        # Detect architecture and download lenos binary.
        download_cmd = (
            "ARCH=$(uname -m); "
            'case "$ARCH" in '
            '  x86_64|amd64) GOARCH="x86_64" ;; '
            '  arm64|aarch64) GOARCH="arm64" ;; '
            "  *) echo 'ERROR: unsupported arch' >&2; exit 1 ;; "
            "esac; "
            f'ARCHIVE="lenos_Linux_${{GOARCH}}.tar.gz"; '
            f'curl -fsSL "{LENOS_DOWNLOAD_URL}/${{ARCHIVE}}" '
            f'  -o "/tmp/${{ARCHIVE}}" && '
            'tar -xzf "/tmp/${ARCHIVE}" -C /tmp && '
            "mv /tmp/lenos /usr/local/bin/lenos && "
            "chmod +x /usr/local/bin/lenos && "
            'rm "/tmp/${ARCHIVE}" && '
            "lenos --version"
        )
        await self.exec_as_root(environment, command=download_cmd)

        organon_cmd = (
            "ARCH=$(uname -m); "
            'case "$ARCH" in '
            '  x86_64|amd64) GOARCH="x86_64" ;; '
            '  arm64|aarch64) GOARCH="arm64" ;; '
            "  *) echo 'ERROR: unsupported arch' >&2; exit 1 ;; "
            "esac; "
            f'ARCHIVE="organon_Linux_${{GOARCH}}.tar.gz"; '
            f'curl -fsSL "{ORGANON_DOWNLOAD_URL}/${{ARCHIVE}}" '
            f'  -o "/tmp/${{ARCHIVE}}" && '
            'tar -xzf "/tmp/${ARCHIVE}" -C /tmp && '
            "for bin in src web skill; do "
            '  test -f "/tmp/${bin}" || '
            '    { echo "ERROR: ${bin} missing from organon archive" >&2; exit 1; }; '
            '  mv "/tmp/${bin}" "/usr/local/bin/${bin}"; '
            '  chmod +x "/usr/local/bin/${bin}"; '
            "done && "
            'rm "/tmp/${ARCHIVE}" && '
            "command -v src web skill"
        )
        await self.exec_as_root(environment, command=organon_cmd)

        einai_cmd = (
            "ARCH=$(uname -m); "
            'case "$ARCH" in '
            '  x86_64|amd64) GOARCH="amd64" ;; '
            '  arm64|aarch64) GOARCH="arm64" ;; '
            "  *) echo 'ERROR: unsupported arch' >&2; exit 1 ;; "
            "esac; "
            f'VERSION="{EINAI_ARCHIVE_VERSION}"; '
            'if [ -n "$VERSION" ]; then '
            '  ARCHIVE="ei_${VERSION}_linux_${GOARCH}.tar.gz"; '
            "else "
            '  ARCHIVE="ei_linux_${GOARCH}.tar.gz"; '
            "fi; "
            f'curl -fsSL "{EINAI_DOWNLOAD_URL}/${{ARCHIVE}}" '
            f'  -o "/tmp/${{ARCHIVE}}" && '
            'tar -xzf "/tmp/${ARCHIVE}" -C /tmp && '
            "mv /tmp/ei /usr/local/bin/ei && "
            "chmod +x /usr/local/bin/ei && "
            'rm "/tmp/${ARCHIVE}" && '
            "ei version"
        )
        await self.exec_as_root(environment, command=einai_cmd)

        # Write temenos config (lenos loads this at first sandbox use)
        await self.exec_as_agent(
            environment,
            command=(
                "mkdir -p ~/.config/temenos && "
                "cat > ~/.config/temenos/config.toml << 'TEOF'\n"
                f"{TEMENOS_CONFIG}"
                "TEOF"
            ),
        )

        # Ensure lenos config dirs exist (host mount covers the content)
        await self.exec_as_agent(
            environment,
            command="mkdir -p ~/.config/lenos ~/.local/share/lenos",
        )

        await self.exec_as_agent(
            environment,
            command=(
                "mkdir -p ~/.config/einai ~/.einai && "
                "cat > ~/.config/einai/config.toml << 'EOF'\n"
                'default_runtime = "lenos"\n'
                f'model = "{EINAI_MODEL}"\n'
                'references_path = "~/.einai/references"\n'
                "EOF"
            ),
        )

        await self.exec_as_agent(
            environment,
            command=(
                "if ! ei daemon status >/dev/null 2>&1; then "
                "  rm -f ~/.einai/daemon.sock; "
                "  nohup ei daemon run > ~/.einai/daemon.log 2>&1 & "
                "fi; "
                "for i in $(seq 1 50); do "
                "  if ei daemon status >/dev/null 2>&1; then "
                "    ei daemon status; exit 0; "
                "  fi; "
                "  sleep 0.1; "
                "done; "
                "cat ~/.einai/daemon.log >&2; "
                "exit 1"
            ),
        )

        await self.exec_as_agent(
            environment,
            command="command -v lenos src web skill ei",
        )

    @with_prompt_template
    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        model_flag = ""
        if self.model_name:
            model_flag = f" -m {shlex.quote(self.model_name)}"
        reasoning_flag = self._reasoning_flag_for_model(self.model_name)
        sandbox_flag = self._sandbox_flag()

        cli_flags = self.build_cli_flags()
        extra_flags = f" {cli_flags}" if cli_flags else ""
        task_context = self._task_context(instruction)

        await self.exec_as_agent(
            environment,
            command=self._write_task_context_command(task_context),
        )

        run_cmd = (
            "set -o pipefail; "
            "export LENOS_DISABLE_PROVIDER_AUTO_UPDATE=1; "
            f"lenos run{model_flag}{reasoning_flag}{sandbox_flag}{extra_flags} "
            f"--context-file {shlex.quote(TASK_CONTEXT_PATH)} "
            f"--usage-json {shlex.quote(USAGE_SUMMARY_PATH)} "
            f"{shlex.quote(TASK_TRIGGER)} "
            "2>&1 | tee /logs/agent/lenos.txt"
        )
        await self.exec_as_agent(
            environment,
            command=f"bash -lc {shlex.quote(run_cmd)}",
        )

        result = await self.exec_as_agent(
            environment,
            command=f"cat {shlex.quote(USAGE_SUMMARY_PATH)}",
        )
        self._populate_usage_context(context, result.stdout)

    @staticmethod
    def _task_context(instruction: str) -> str:
        return instruction.strip() + "\n"

    @staticmethod
    def _write_task_context_command(task_context: str) -> str:
        encoded = base64.b64encode(task_context.encode("utf-8")).decode("ascii")
        script = (
            "import base64\n"
            "from pathlib import Path\n"
            f"Path({TASK_CONTEXT_PATH!r}).write_bytes(base64.b64decode({encoded!r}))\n"
        )
        return f"python3 - <<'PY'\n{script}PY"

    def _populate_usage_context(self, context: AgentContext, stdout: str) -> None:
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if not lines:
            return

        try:
            summary = json.loads("\n".join(lines))
        except json.JSONDecodeError:
            try:
                summary = json.loads(lines[-1])
            except json.JSONDecodeError:
                return

        self._apply_usage_summary(context, summary)

    def _apply_usage_summary(self, context: AgentContext, summary: dict) -> None:
        context.n_input_tokens = summary["input_tokens"]
        context.n_cache_tokens = summary["input_cache_hit_tokens"]
        context.n_output_tokens = summary["output_tokens"]
        context.cost_usd = summary.get("cost_usd")
        context.metadata = {
            **(context.metadata or {}),
            "lenos_usage": summary,
            "lenos_cost_usd": summary.get("cost_usd"),
        }

    def populate_context_post_run(self, context: AgentContext) -> None:
        path = self.logs_dir / "usage-summary.json"
        if not path.exists():
            return

        try:
            summary = json.loads(path.read_text(encoding="utf-8"))
            self._apply_usage_summary(context, summary)
        except (OSError, KeyError, json.JSONDecodeError):
            self.logger.exception("Failed to parse Lenos usage summary")
