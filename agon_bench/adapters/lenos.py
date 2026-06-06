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

from harbor.agents.installed.base import (
    BaseInstalledAgent,
    CliFlag,
    with_prompt_template,
)
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


DEFAULT_LENOS_VERSION = "v1.4.3+0.74.1"
DEFAULT_ORGANON_VERSION = "latest"
DEEPSEEK_REASONING_EFFORT = "xhigh"
LENOS_REASONING_EFFORT = os.environ.get("LENOS_REASONING_EFFORT")

LENOS_VERSION = os.environ.get("LENOS_VERSION", DEFAULT_LENOS_VERSION)
LENOS_RELEASE_BASE = os.environ.get(
    "LENOS_RELEASE_BASE", "https://github.com/tta-lab/lenos/releases"
)
ORGANON_VERSION = os.environ.get("ORGANON_VERSION", DEFAULT_ORGANON_VERSION)
ORGANON_RELEASE_BASE = os.environ.get(
    "ORGANON_RELEASE_BASE", "https://github.com/tta-lab/organon/releases"
)
if LENOS_VERSION == "latest":
    LENOS_DOWNLOAD_URL = f"{LENOS_RELEASE_BASE}/latest/download"
else:
    LENOS_DOWNLOAD_URL = f"{LENOS_RELEASE_BASE}/download/{LENOS_VERSION}"
if ORGANON_VERSION == "latest":
    ORGANON_DOWNLOAD_URL = f"{ORGANON_RELEASE_BASE}/latest/download"
else:
    ORGANON_DOWNLOAD_URL = f"{ORGANON_RELEASE_BASE}/download/{ORGANON_VERSION}"

TEMENOS_CONFIG = """\
# temenos config for Harbor Lenos agent
allow_env = [
  "PATH", "HOME", "USER", "SHELL",
  "LENOS_*",
]
allow_read = [
  "/usr/local/bin", "/usr/bin", "/bin",
  "/app", "/workspace",
  "/root/.config/lenos",
  "/tmp",
]
allow_write = [
  "/app", "/workspace",
  "/tmp",
]
"""

USAGE_SUMMARY_PATH = "/logs/agent/usage-summary.json"


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

    @with_prompt_template
    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        escaped_instruction = shlex.quote(instruction)
        model_flag = ""
        if self.model_name:
            model_flag = f" -m {shlex.quote(self.model_name)}"
        reasoning_flag = self._reasoning_flag_for_model(self.model_name)

        cli_flags = self.build_cli_flags()
        extra_flags = f" {cli_flags}" if cli_flags else ""

        run_cmd = (
            "set -o pipefail; "
            "export LENOS_DISABLE_PROVIDER_AUTO_UPDATE=1; "
            f"lenos run{model_flag}{reasoning_flag}{extra_flags} "
            f"--usage-json {shlex.quote(USAGE_SUMMARY_PATH)} "
            f"{escaped_instruction} "
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
