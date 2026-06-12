# fal.ai Image Generation

A [Cursor Agent Skill](https://cursor.com/docs/agent/skills) for generating and editing images with [fal.ai](https://fal.ai). It targets production assets for web design, product UI, games, icons, sprites, textures, mockups, and transparent PNG cutouts.

The skill teaches an agent how to pick models, write production prompts, and run the bundled CLI. Image only — no video, audio, or 3D.

## What it does

- **Generate** images from text prompts (`nano-banana-2`, `nano-banana-pro`, and related models)
- **Edit** existing images with prompt-guided changes
- **Remove backgrounds** with `rembg`
- **Create transparent PNGs** via a two-step generate-on-flat-background → rembg workflow
- **Download outputs** into your project asset folder

## Install

Clone or copy this repository into a Cursor skills directory:

| Scope | Path |
|-------|------|
| Personal (all projects) | `~/.cursor/skills/fal-ai-image-gen/` |
| Project (this repo only) | `.cursor/skills/fal-ai-image-gen/` |

The skill is loaded from `SKILL.md`. Invoke it in chat with `$fal-ai-image-gen` or ask the agent to use the fal.ai image generation skill.

## Requirements

- **Python 3.11+** — the CLI uses only the standard library
- **fal.ai API key** — set `FAL_KEY` in the environment or in a `.env` file in your working directory:

```bash
export FAL_KEY="your-fal-api-key"
```

Get a key at [fal.ai/dashboard/keys](https://fal.ai/dashboard/keys).

## Quick start

From the skill directory:

```bash
python3 scripts/fal_image.py --help
```

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

Create a transparent game asset (generate on white, then remove background):

```bash
python3 scripts/fal_image.py transparent \
  --prompt "A cute low-poly health potion pickup, centered, clean silhouette, readable at 64px" \
  --background "flat solid white background" \
  --aspect-ratio 1:1 \
  --download-dir ./assets/generated
```

Remove a background from an existing image:

```bash
python3 scripts/fal_image.py rembg \
  --image-file ./assets/item-on-white.png \
  --download-dir ./assets/generated
```

## CLI commands

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

Model aliases include `nano-banana-2`, `nano-banana-pro`, `nano-banana-edit`, `rem-bg`, and `rembg`. Full fal endpoint IDs also work.

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
├── SKILL.md              # Agent instructions (primary skill file)
├── README.md             # This file
├── agents/
│   └── openai.yaml       # ChatGPT agent interface metadata
└── scripts/
    └── fal_image.py      # fal.ai queue API CLI
```

## Agent usage notes

When an agent runs the CLI:

- Wait for each command to finish; do not redirect or detach output (streaming updates may break).
- Prefer parallel tool calls for multiple independent generations rather than one shell script with many runs.
- Return results with Markdown image tags, the fal URL, model used, and local download path.

See `SKILL.md` for prompt patterns, aspect-ratio defaults, and full workflow guidance.

## Author

**procommerz** — skill version `0.0.2`
