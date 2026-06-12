---
name: fal-ai-image-gen
description: Generate and edit images with fal.ai for web design, product UI, game development, sprites, icons, concept art, textures, mockups, and transparent-background assets. Use when a user asks to create, iterate, edit, upscale-style, remove backgrounds from, or prepare AI-generated images using fal.ai models such as nano-banana, nano-banana-pro, or rem-bg.
metadata:
  author: procommerz
  version: "0.0.2"
---

# fal.ai Image Generation

Use fal.ai for image generation and image editing tasks, especially when assets will be used in websites, UI mockups, landing pages, games, sprites, icons, textures, or design prototypes. This skill intentionally focuses on images only, not video, audio, or 3D.

## Core workflow

1. Decide the asset role: hero image, UI illustration, product mockup, game sprite, tileable texture, icon, item pickup, character sheet, background, or edit of an existing image.
2. Choose the model:
   - `fal-ai/nano-banana-2`: default workhorse model, fast iteration and images or edits.
   - `fal-ai/nano-banana-pro`: slightly high quality for photos and text, more layout control, typography, polished web/game assets, and important final outputs.
   - `fal-ai/nano-banana-edit`: faster iteration and simpler images or edits.
   - `fal-ai/imageutils/rembg`: background removal. The user may call this "rem-bg" or "rembg".
3. Generate or edit with a concrete production prompt: include medium, subject, camera/view, composition, palette, lighting, aspect ratio, and what must stay isolated or readable.
4. For transparent assets, never ask the image model to produce transparency directly. Generate the subject on a flat solid background first, then run background removal.
5. Show final images with Markdown image tags and include the URL and any downloaded local path.

## Transparent-background rule

For sprites, icons, stickers, product cutouts, item pickups, and other transparent PNG needs:

1. Generate the desired content on a flat solid background, usually `flat solid white background`.
2. Avoid cast shadows, gradients, busy texture, outlines that blend into the background, and edge-touching subjects.
3. Run the generated image through `fal-ai/imageutils/rembg`.
4. Use PNG output.

If white is part of the subject, choose another flat color with strong contrast, such as `flat solid cyan background` or `flat solid magenta background`.

## Script

Use the bundled script from this skill directory with a python3.11+ interpreter:

```bash
python3 scripts/fal_image.py --help
```

Set `FAL_KEY` in the environment, or place it in a `.env` file in the working directory:

```bash
export FAL_KEY="your-fal-api-key"
```

The script normally will wait for the generation to complete and output streaming updates. When you need multiple images **prefer parallel tool calling per generation**, rathern than creating a custom shell script with multiple generations in one place – such scripts may not work due to streaming output. DO NOT call the script with detached output or with output redirection. Wait for the output to finish.

### Generate an image

```bash
python3 scripts/fal_image.py generate \
  --prompt "A polished SaaS dashboard hero image showing collaborative analytics, crisp glass monitor reflections, realistic product UI, bright studio lighting" \
  --model nano-banana-2 \
  --aspect-ratio 16:9 \
  --resolution 2K \
  --download-dir ./assets/generated
```

### Edit an image

```bash
python3 scripts/fal_image.py edit \
  --image-file ./assets/source.png \
  --prompt "Keep the layout and product shape, change the visual style to premium clay-rendered game UI art with clean soft lighting" \
  --model nano-banana-pro \
  --download-dir ./assets/generated
```

### Create a transparent PNG

```bash
python3 scripts/fal_image.py transparent \
  --prompt "A cute low-poly health potion pickup for a mobile fantasy game, centered, clean silhouette, readable at 64 pixels" \
  --background "flat solid white background" \
  --aspect-ratio 1:1 \
  --download-dir ./assets/generated
```

### Remove a background from an existing image

```bash
python3 scripts/fal_image.py rembg \
  --image-file ./assets/item-on-white.png \
  --download-dir ./assets/generated
```

## Prompt patterns

For web design:

```text
Create a production-ready image for [page/component]. Subject: [literal subject]. Use [style/medium], [lighting], [palette], [composition]. Leave negative space for [headline/UI]. Avoid fake unreadable UI text unless explicitly requested.
```

For game assets:

```text
Create a [sprite/icon/prop/character/background/texture] for a [genre] game. Subject: [literal subject]. View: [front/side/isometric/top-down]. Style: [pixel art/low-poly/painted/3D render]. Requirements: readable at [size], clean silhouette, consistent palette, no cropped edges.
```

For editing:

```text
Preserve [identity/layout/pose/material/logo/important object]. Change only [target change]. Match [style/lighting/perspective]. Do not alter [protected elements].
```

## Practical defaults

- Use `--output-format png` for UI, games, transparency, and assets that may be composited.
- Use `16:9` or `21:9` for hero images, `4:3` or `3:2` for editorial/product images, `1:1` for icons, pickups, stickers, and sprites, and `9:16` for mobile-first scenes.
- Use `1K` for rough iterations, `2K` for most final web/game assets, and `4K` only when the asset needs large display detail.
- Download outputs into the project asset folder when they will be used by code, not left as only remote URLs.
- fal queue subpaths are submit-only. For endpoints such as `fal-ai/imageutils/rembg` and `fal-ai/nano-banana-pro/edit`, submit to the full endpoint, but poll status and fetch results from the base queue resource (`fal-ai/imageutils` or `fal-ai/nano-banana-pro`). The bundled script handles this.
- For unusual model parameters, fetch the current fal model schema or open the fal model API page before guessing.
- DO NOT call the generator script with detached output or with output redirection. Wait for the output to finish.

## Output handoff

When returning results to the user, include:

```markdown
![Generated asset](https://v3.fal.media/files/...)

Model: fal-ai/nano-banana-pro
Use: transparent game pickup
Local file: /absolute/path/to/project/assets/generated/output.png
```

Keep iteration notes short: mention what was generated, which model was used, and where the asset is available.
