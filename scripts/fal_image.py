#!/usr/bin/env python3
"""fal.ai image generation/editing helper for agent skills.

Uses only the Python standard library and fal's queue REST API.
"""

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


MODEL_ALIASES = {
    "nano-banana": "fal-ai/nano-banana",
    "nano-banana-2": "fal-ai/nano-banana-2",
    "nano-banana-edit": "fal-ai/nano-banana/edit",
    "nano-banan-pro": "fal-ai/nano-banana-pro",
    "nano-banana-pro": "fal-ai/nano-banana-pro",
    "nano-banana-pro-edit": "fal-ai/nano-banana-pro/edit",
    "rem-bg": "fal-ai/imageutils/rembg",
    "rembg": "fal-ai/imageutils/rembg",
}

QUEUE_RESOURCE_MODELS = {
    "fal-ai/imageutils/rembg": "fal-ai/imageutils",
    "fal-ai/imageutils/depth": "fal-ai/imageutils",
    "fal-ai/imageutils/marigold-depth": "fal-ai/imageutils",
    "fal-ai/nano-banana/edit": "fal-ai/nano-banana",
    "fal-ai/nano-banana-pro/edit": "fal-ai/nano-banana-pro",
}

TOKEN_ENDPOINT = "https://rest.alpha.fal.ai/storage/auth/token?storage_type=fal-cdn-v3"
QUEUE_BASE = "https://queue.fal.run"


def eprint(*parts: object) -> None:
    print(*parts, file=sys.stderr)


def load_dotenv() -> None:
    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"]
    for path in candidates:
        if not path.exists():
            continue
        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def fal_key() -> str:
    load_dotenv()
    key = os.environ.get("FAL_KEY", "").strip()
    if not key:
        raise SystemExit("Error: FAL_KEY is not set. Export it or add FAL_KEY=... to .env.")
    return key


def resolve_model(model: str) -> str:
    return MODEL_ALIASES.get(model, model)


def edit_endpoint(model: str) -> str:
    model_id = resolve_model(model)
    if model_id in {"fal-ai/nano-banana", "fal-ai/nano-banana-pro"}:
        return f"{model_id}/edit"
    return model_id


def request_json(
    method: str,
    url: str,
    *,
    key: Optional[str] = None,
    data: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    raw_body: Optional[bytes] = None,
    timeout: int = 120,
) -> Any:
    all_headers = dict(headers or {})
    body = raw_body
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        all_headers.setdefault("Content-Type", "application/json")
    if key:
        all_headers.setdefault("Authorization", f"Key {key}")

    request = urllib.request.Request(url, data=body, headers=all_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}\n{detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error for {url}: {exc}") from exc

    if not payload:
        return {}
    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        text = payload.decode("utf-8", errors="replace")
        raise SystemExit(f"Expected JSON from {url}, got:\n{text}") from exc


def upload_file(path: str, key: str) -> str:
    file_path = Path(path).expanduser().resolve()
    if not file_path.exists() or not file_path.is_file():
        raise SystemExit(f"File not found: {file_path}")
    size = file_path.stat().st_size
    if size > 100 * 1024 * 1024:
        raise SystemExit("File is over 100MB. Use fal's multipart upload tooling for this file.")

    eprint(f"Uploading {file_path.name}...")
    token = request_json("POST", TOKEN_ENDPOINT, key=key, data={})
    upload_token = token.get("token")
    token_type = token.get("token_type", "Bearer")
    base_url = token.get("base_url")
    if not upload_token or not base_url:
        raise SystemExit(f"Could not get fal CDN token:\n{json.dumps(token, indent=2)}")

    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    upload_url = f"{base_url}/files/upload"
    upload_headers = {
        "Authorization": f"{token_type} {upload_token}",
        "Content-Type": content_type,
        "X-Fal-File-Name": file_path.name,
    }
    response = request_json(
        "POST",
        upload_url,
        headers=upload_headers,
        raw_body=file_path.read_bytes(),
        timeout=300,
    )
    access_url = response.get("access_url")
    if not access_url:
        raise SystemExit(f"Upload did not return access_url:\n{json.dumps(response, indent=2)}")
    eprint(f"Uploaded: {access_url}")
    return access_url


def queue_url(model: str, suffix: str = "") -> str:
    return f"{QUEUE_BASE}/{model}{suffix}"


def queue_resource_model(model: str) -> str:
    return QUEUE_RESOURCE_MODELS.get(model, model)


def submit(
    model: str,
    payload: Dict[str, Any],
    args: argparse.Namespace,
    key: str,
) -> Any:
    headers = {}
    lifecycle = getattr(args, "lifecycle", None)
    if lifecycle:
        headers["X-Fal-Object-Lifecycle-Preference"] = str(lifecycle)

    submit_model = model
    resource_model = queue_resource_model(model)

    eprint(f"Submitting to {submit_model}...")
    submitted = request_json("POST", queue_url(submit_model), key=key, data=payload, headers=headers)
    if getattr(args, "async_mode", False):
        if resource_model != submit_model and isinstance(submitted, dict):
            submitted = dict(submitted)
            submitted["status_model"] = resource_model
            submitted["result_model"] = resource_model
        return submitted

    request_id = submitted.get("request_id")
    if not request_id:
        raise SystemExit(f"Submit response missing request_id:\n{json.dumps(submitted, indent=2)}")

    deadline = time.monotonic() + args.timeout
    seen_logs: Set[Tuple[str, str]] = set()
    while time.monotonic() < deadline:
        status = request_json(
            "GET",
            queue_url(resource_model, f"/requests/{request_id}/status?logs=1"),
            key=key,
        )
        state = status.get("status", "UNKNOWN")
        if state == "IN_QUEUE":
            position = status.get("queue_position")
            eprint(f"Status: IN_QUEUE position={position}")
        elif state == "IN_PROGRESS":
            eprint("Status: IN_PROGRESS")
        elif state == "COMPLETED":
            if status.get("error"):
                raise SystemExit(f"fal request failed: {status.get('error')}")
            eprint("Status: COMPLETED")
            return request_json(
                "GET",
                queue_url(resource_model, f"/requests/{request_id}"),
                key=key,
                timeout=300,
            )
        else:
            eprint(f"Status: {state}")

        if getattr(args, "logs", False):
            for log in status.get("logs", []) or []:
                key_tuple = (str(log.get("timestamp", "")), str(log.get("message", "")))
                if key_tuple not in seen_logs:
                    seen_logs.add(key_tuple)
                    eprint(f"> {log.get('message')}")
        time.sleep(args.poll_interval)

    raise SystemExit(f"Timed out after {args.timeout}s. Request ID: {request_id}")


def first_image_url(result: Any) -> str:
    if isinstance(result, dict):
        images = result.get("images")
        if isinstance(images, list) and images:
            url = images[0].get("url")
            if url:
                return str(url)
        image = result.get("image")
        if isinstance(image, dict) and image.get("url"):
            return str(image["url"])
    raise SystemExit(f"Could not find image URL in result:\n{json.dumps(result, indent=2)}")


def iter_media_files(node: Any) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    if isinstance(node, dict):
        url = node.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            content_type = str(node.get("content_type", ""))
            if content_type.startswith("image/") or not content_type:
                found.append(node)
        for value in node.values():
            found.extend(iter_media_files(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(iter_media_files(value))
    return found


def download_outputs(result: Any, directory: str) -> List[str]:
    output_dir = Path(directory).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    media_files = iter_media_files(result)

    for index, media in enumerate(media_files):
        url = str(media["url"])
        parsed = urllib.parse.urlparse(url)
        name = media.get("file_name") or Path(parsed.path).name or f"fal-output-{index}.png"
        target = output_dir / str(name)
        if target.exists():
            stem = target.stem
            suffix = target.suffix or ".png"
            target = output_dir / f"{stem}-{index}{suffix}"
        eprint(f"Downloading {url} -> {target}")
        try:
            with urllib.request.urlopen(url, timeout=300) as response:
                target.write_bytes(response.read())
        except urllib.error.URLError as exc:
            raise SystemExit(f"Download failed for {url}: {exc}") from exc
        written.append(str(target))
    return written


def enrich_with_downloads(result: Any, download_dir: Optional[str]) -> Any:
    if not download_dir:
        return result
    downloaded = download_outputs(result, download_dir)
    if isinstance(result, dict):
        result = dict(result)
        result["downloaded_files"] = downloaded
    return result


def collect_image_urls(args: argparse.Namespace, key: str) -> List[str]:
    urls = list(args.image_url or [])
    for image_file in args.image_file or []:
        urls.append(upload_file(image_file, key))
    if not urls:
        raise SystemExit("Provide --image-url or --image-file.")
    return urls


def build_image_payload(args: argparse.Namespace) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "prompt": args.prompt,
        "num_images": args.num_images,
        "aspect_ratio": args.aspect_ratio,
        "output_format": args.output_format,
        "safety_tolerance": str(args.safety_tolerance),
    }
    if args.seed is not None:
        payload["seed"] = args.seed
    if getattr(args, "resolution", None):
        payload["resolution"] = args.resolution
    if getattr(args, "enable_web_search", False):
        payload["enable_web_search"] = True
    if getattr(args, "limit_generations", False):
        payload["limit_generations"] = True
    return payload


def command_generate(args: argparse.Namespace) -> Any:
    key = fal_key()
    model = resolve_model(args.model)
    result = submit(model, build_image_payload(args), args, key)
    return enrich_with_downloads(result, args.download_dir)


def command_edit(args: argparse.Namespace) -> Any:
    key = fal_key()
    model = edit_endpoint(args.model)
    payload = build_image_payload(args)
    payload["image_urls"] = collect_image_urls(args, key)
    result = submit(model, payload, args, key)
    return enrich_with_downloads(result, args.download_dir)


def command_rembg(args: argparse.Namespace) -> Any:
    key = fal_key()
    image_url = collect_image_urls(args, key)[0]
    payload = {"image_url": image_url, "crop_to_bbox": args.crop_to_bbox}
    result = submit("fal-ai/imageutils/rembg", payload, args, key)
    return enrich_with_downloads(result, args.download_dir)


def command_transparent(args: argparse.Namespace) -> Any:
    if args.async_mode:
        raise SystemExit("The transparent command runs two dependent requests and cannot use --async.")
    key = fal_key()
    generation_prompt = (
        f"{args.prompt}. Isolated centered subject on a {args.background}. "
        "Clean silhouette, no cropped edges, no busy background, no transparent background yet."
    )
    gen_args = argparse.Namespace(**vars(args))
    gen_args.prompt = generation_prompt
    model = resolve_model(args.model)
    generated = submit(model, build_image_payload(gen_args), args, key)
    source_url = first_image_url(generated)
    removed = submit(
        "fal-ai/imageutils/rembg",
        {"image_url": source_url, "crop_to_bbox": args.crop_to_bbox},
        args,
        key,
    )
    result = {
        "transparent": removed,
        "generated_on_flat_background": generated,
        "background": args.background,
    }
    return enrich_with_downloads(result, args.download_dir)


def command_upload(args: argparse.Namespace) -> Any:
    key = fal_key()
    return {"url": upload_file(args.file, key)}


def command_status(args: argparse.Namespace) -> Any:
    key = fal_key()
    model = queue_resource_model(resolve_model(args.model))
    return request_json(
        "GET",
        queue_url(model, f"/requests/{args.request_id}/status?logs=1"),
        key=key,
    )


def command_result(args: argparse.Namespace) -> Any:
    key = fal_key()
    model = queue_resource_model(resolve_model(args.model))
    result = request_json("GET", queue_url(model, f"/requests/{args.request_id}"), key=key)
    return enrich_with_downloads(result, args.download_dir)


def add_queue_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--async", dest="async_mode", action="store_true", help="Submit and return request metadata without polling.")
    parser.add_argument("--timeout", type=int, default=600, help="Maximum seconds to wait while polling.")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Seconds between status checks.")
    parser.add_argument("--logs", action="store_true", help="Print fal runner logs while polling.")
    parser.add_argument("--lifecycle", type=int, help="Preferred output lifetime in seconds, if supported by fal.")


def add_generation_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prompt", required=True, help="Prompt for generation or editing.")
    parser.add_argument("--model", default="nano-banana-pro", help="Model alias or fal endpoint ID.")
    parser.add_argument("--aspect-ratio", default="1:1", help="Aspect ratio, such as 1:1, 16:9, 4:3, 9:16.")
    parser.add_argument("--num-images", type=int, default=1, help="Number of images to generate.")
    parser.add_argument("--output-format", default="png", choices=["png", "jpeg", "webp"], help="Image output format.")
    parser.add_argument("--resolution", choices=["1K", "2K", "4K"], help="Resolution for models that support it.")
    parser.add_argument("--safety-tolerance", default="4", choices=["1", "2", "3", "4", "5", "6"], help="fal safety tolerance.")
    parser.add_argument("--seed", type=int, help="Optional random seed.")
    parser.add_argument("--enable-web-search", action="store_true", help="Enable web search for models that support it.")
    parser.add_argument("--limit-generations", action="store_true", help="Ask supported models to limit generations per prompt.")
    parser.add_argument("--download-dir", help="Download returned image files into this directory.")
    add_queue_args(parser)


def add_image_input_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--image-url", action="append", help="Input image URL. Repeat for multiple references.")
    parser.add_argument("--image-file", action="append", help="Local input image to upload. Repeat for multiple references.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate, edit, and remove image backgrounds with fal.ai.")
    subparsers = parser.add_subparsers(dest="command")

    generate = subparsers.add_parser("generate", help="Generate image(s) from text.")
    add_generation_args(generate)
    generate.set_defaults(func=command_generate)

    edit = subparsers.add_parser("edit", help="Edit image(s) with a prompt.")
    add_generation_args(edit)
    add_image_input_args(edit)
    edit.set_defaults(func=command_edit)

    transparent = subparsers.add_parser("transparent", help="Generate on a flat background, then remove it.")
    add_generation_args(transparent)
    transparent.add_argument("--background", default="flat solid white background", help="Flat background to generate against before rembg.")
    transparent.add_argument("--crop-to-bbox", action="store_true", help="Crop rembg output to the subject bounding box.")
    transparent.set_defaults(func=command_transparent)

    rembg = subparsers.add_parser("rembg", help="Remove the background from an image.")
    add_image_input_args(rembg)
    rembg.add_argument("--download-dir", help="Download returned image files into this directory.")
    rembg.add_argument("--crop-to-bbox", action="store_true", help="Crop output to the subject bounding box.")
    add_queue_args(rembg)
    rembg.set_defaults(func=command_rembg)

    upload = subparsers.add_parser("upload", help="Upload a local file to fal CDN and print its URL.")
    upload.add_argument("--file", required=True, help="Local file path.")
    upload.set_defaults(func=command_upload)

    status = subparsers.add_parser("status", help="Check a queued request status.")
    status.add_argument("--model", required=True, help="Model alias or endpoint ID used for the request.")
    status.add_argument("--request-id", required=True, help="fal queue request_id.")
    status.set_defaults(func=command_status)

    result = subparsers.add_parser("result", help="Fetch a completed queued request result.")
    result.add_argument("--model", required=True, help="Model alias or endpoint ID used for the request.")
    result.add_argument("--request-id", required=True, help="fal queue request_id.")
    result.add_argument("--download-dir", help="Download returned image files into this directory.")
    result.set_defaults(func=command_result)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        raise SystemExit(2)
    result = args.func(args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
