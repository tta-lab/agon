"""Harbor installed agent adapter for Lenos.

Mount your host lenos config into the container:
  harbor run ... \
    -v ./agon_bench/lenos/config.json:/root/.config/lenos/config.json \
    -v ~/.local/share/lenos:/root/.local/share/lenos

`agon_bench/lenos/config.json` is Agon's minimal non-secret options config.
`~/.local/share/lenos/config.json` contains host provider secrets; do not read it.
"""

import os
import shlex

from harbor.agents.installed.base import (
    BaseInstalledAgent,
    CliFlag,
    with_prompt_template,
)
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


LENOS_VERSION = os.environ.get("LENOS_VERSION", "latest")
LENOS_RELEASE_BASE = "https://github.com/tta-lab/lenos/releases"
if LENOS_VERSION == "latest":
    LENOS_DOWNLOAD_URL = f"{LENOS_RELEASE_BASE}/latest/download"
else:
    LENOS_DOWNLOAD_URL = f"{LENOS_RELEASE_BASE}/download/{LENOS_VERSION}"

TEMENOS_CONFIG = """\
# temenos config for Harbor Lenos agent
allow_env = [
  "PATH", "HOME", "USER", "SHELL",
  "LENOS_*",
  "OPENAI_*", "ANTHROPIC_*", "DEEPSEEK_*", "GOOGLE_*",
]
allow_read = [
  "/usr/local/bin", "/usr/bin", "/bin",
  "/app", "/workspace",
  "/root/.config/lenos",
  "/root/.local/share/lenos",
  "/tmp",
]
allow_write = [
  "/app", "/workspace",
  "/tmp",
]
"""


class LenosAgent(BaseInstalledAgent):
    """Lenos — terminal-first AI agent with self-contained sandboxing.

    Lenos config comes from the host, mounted at:
      agon_bench/lenos/config.json → non-secret options config
      ~/.local/share/lenos         → provider secrets and registry cache

    Run with:
      harbor run -d "terminal-bench-2.0==head" \\
        --agent-import-path agon_bench.adapters.lenos:LenosAgent \\
        -m deepseek-v4-pro \\
        --task-id hello-world \\
        -v ./agon_bench/lenos/config.json:/root/.config/lenos/config.json \\
        -v ~/.local/share/lenos:/root/.local/share/lenos
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

    async def install(self, environment: BaseEnvironment) -> None:
        # Install system dependencies for sandboxing
        await self.exec_as_root(
            environment,
            command=(
                "if command -v apt-get &> /dev/null; then "
                "  apt-get update && apt-get install -y bubblewrap curl; "
                "elif command -v apk &> /dev/null; then "
                "  apk add --no-cache bubblewrap curl; "
                "elif command -v yum &> /dev/null; then "
                "  yum install -y bubblewrap curl; "
                "fi"
            ),
            env={"DEBIAN_FRONTEND": "noninteractive"},
        )

        # Detect architecture and download lenos binary
        download_cmd = (
            'ARCH=$(uname -m); '
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
        await self.exec_as_agent(environment, command=download_cmd)

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

        cli_flags = self.build_cli_flags()
        extra_flags = f" {cli_flags}" if cli_flags else ""

        await self.exec_as_agent(
            environment,
            command=(
                "export LENOS_DISABLE_PROVIDER_AUTO_UPDATE=1; "
                f"lenos run{model_flag}{extra_flags} "
                f"{escaped_instruction} "
                "2>&1 | tee /logs/agent/lenos.txt"
            ),
        )

    def populate_context_post_run(self, context: AgentContext) -> None:
        pass
