# Security

## Code-execution model
Blender runs Python with the full permissions of the user. This skill makes an AI agent write and
run such Python, so:

- **Headless mode** runs `blender -b --factory-startup` on a **copy** of the file inside a
  project folder. Generated scripts are linted (`api_lint.py`) for shell calls, `exec`/`eval`,
  overwriting saves, enabling auto-run, and add-on installs.
- **Live MCP mode** sends small scoped chunks to the user's open Blender. The host application
  must ask for approval before each execution; the skill tells agents never to switch that off.
  MCP servers should listen on localhost only.
- The skill never installs add-ons, extensions or packages, never enables auto-run of scripts in
  `.blend` files, and never handles API keys, without an explicit yes from the user.
- Untrusted `.blend` files can contain scripts (drivers, startup text blocks). Open them with
  auto-run disabled.

## Supported versions
| Version | Supported |
|---|---|
| 0.x (Blender 5.2) | yes |

## Reporting a vulnerability
Please open a private security advisory on the repository, or contact the maintainers listed in
the repository profile. Include the Blender version, the agent host, and steps to reproduce.
Do not include secrets or private files in reports.
