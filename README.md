# fal.ai Image Generation

A [Claude Code skill](https://code.claude.com/docs/en/skills) for generating and editing images with [fal.ai](https://fal.ai). Claude uses it to produce web, UI, game, icon, sprite, texture, mockup, and transparent PNG assets through the bundled CLI.

Image only — no video, audio, or 3D.

## What Claude can do with this skill

- **Generate** images from text (`nano-banana-2`, `nano-banana-pro`, and related models)
- **Edit** existing images with prompt-guided changes
- **Remove backgrounds** with `rembg`
- **Create transparent PNGs** via generate-on-flat-background → rembg
- **Download outputs** into your project asset folder

Claude loads the skill automatically when your request matches the description in `SKILL.md`, or you can invoke it directly with `/fal-ai-image-gen`.

## Install

Clone this repository, then install the skill directory where Claude Code looks for skills. The folder name must match the skill name: `fal-ai-image-gen`.

| Scope | Path |
|-------|------|
| Personal (all projects) | `~/.claude/skills/fal-ai-image-gen/` |
| Project (shared via git) | `.claude/skills/fal-ai-image-gen/` |

Example — personal install:

```bash
git clone https://github.com/procommerz/skill-falai-image.git ~/.claude/skills/fal-ai-image-gen
```

Or symlink a local checkout:

```bash
ln -s /path/to/fal-ai-image-gen ~/.claude/skills/fal-ai-image-gen
```

Claude Code watches these directories and picks up edits to `SKILL.md` during the session. Start a new session if you create the skills folder for the first time.

## Requirements

- **Claude Code** with skills enabled
- **Python 3.11+** — the CLI uses only the standard library
- **fal.ai API key** — set `FAL_KEY` in the environment or in a `.env` file in your working directory or in `.claude/settings.json`.

Get a key at [fal.ai/dashboard/keys](https://fal.ai/dashboard/keys).

## Use in Claude Code

Start Claude Code in a project where you want assets:

```bash
claude
```

Then either invoke the skill directly:

```text
/fal-ai-image-gen Create a transparent health potion sprite for a mobile fantasy game
```

Or ask naturally — Claude should load the skill when you mention fal.ai image generation, sprites, icons, mockups, background removal, and similar tasks:

```text
Generate a 16:9 SaaS hero image with fal.ai and save it to ./assets/generated
```

Claude runs `scripts/fal_image.py` from the skill directory, waits for each generation to finish, and returns Markdown image previews plus local file paths.

## CLI reference

The bundled script talks to fal's queue REST API. You can run it yourself to test the skill outside Claude Code:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/fal_image.py --help
```

When testing from the skill directory directly:

```bash
python3 scripts/fal_image.py --help
```

### Examples

Generate a hero image:

```bash
python3 scripts/fal_image.py generate \
  --prompt "A polished SaaS dashboard hero image, crisp glass monitor reflections, bright studio lighting" \
  --model nano-banana-2 \
  --aspect-ratio 16:9 \
  --resolution 2K \
  --download-dir ./assets/generated
```

Edit an existing image:

```bash
python3 scripts/fal_image.py edit \
  --image-file ./assets/source.png \
  --prompt "Keep the layout, change the style to premium clay-rendered game UI art" \
  --model nano-banana-pro \
  --download-dir ./assets/generated
```

Create a transparent game asset:

```bash
python3 scripts/fal_image.py transparent \
  --prompt "A cute low-poly health potion pickup, centered, clean silhouette, readable at 64px" \
  --background "flat solid white background" \
  --aspect-ratio 1:1 \
  --download-dir ./assets/generated
```

Remove a background:

```bash
python3 scripts/fal_image.py rembg \
  --image-file ./assets/item-on-white.png \
  --download-dir ./assets/generated
```

### Commands

| Command | Description |
|---------|-------------|
| `generate` | Text-to-image generation |
| `edit` | Prompt-based image editing (local file or URL) |
| `transparent` | Generate on a flat background, then run rembg |
| `rembg` | Background removal only |
| `upload` | Upload a local file to fal CDN |
| `status` | Poll a queued request by ID |
| `result` | Fetch a completed queued request |

Common flags: `--model`, `--aspect-ratio`, `--resolution` (`1K` / `2K` / `4K`), `--output-format` (`png` / `jpeg` / `webp`), `--download-dir`, `--num-images`, `--seed`.

Model aliases: `nano-banana-2`, `nano-banana-pro`, `nano-banana-edit`, `rem-bg`, `rembg`. Full fal endpoint IDs also work.

## Models

| Model | Best for |
|-------|----------|
| `fal-ai/nano-banana-2` | Default workhorse — fast iteration for images and edits |
| `fal-ai/nano-banana-pro` | Higher quality, typography, polished web/game assets, finals |
| `fal-ai/nano-banana/edit` | Faster, simpler edits |
| `fal-ai/imageutils/rembg` | Background removal |

## Transparent PNG workflow

Image models cannot emit true transparency. For sprites, icons, stickers, and cutouts:

1. Generate the subject on a **flat solid background** (usually white).
2. Avoid shadows, gradients, and subjects that touch the frame edges.
3. Run the result through `rembg` (the `transparent` command does both steps).
4. Use PNG output.

If white appears in the subject, switch to a contrasting flat color (e.g. cyan or magenta).

## Repository layout

```
fal-ai-image-gen/
├── SKILL.md              # Claude Code skill instructions
├── README.md             # This file
├── agents/
│   └── openai.yaml       # Optional metadata for other agent platforms
└── scripts/
    └── fal_image.py      # fal.ai queue API CLI
```

`SKILL.md` is the source of truth for Claude: model selection, prompt patterns, aspect-ratio defaults, and output handoff. Read it if you want to customize behavior or fork the skill.

## Author

**procommerz** — skill version `0.0.2`
