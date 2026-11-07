"""Command-line interface for prompt-tag-organizer."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from . import ai as ai_mod
from .dedupe import find_duplicates, duplicate_map
from .export import export_index
from .parser import (
    DEFAULT_EXTENSIONS,
    DEFAULT_SKIP_DIRS,
    apply_frontmatter,
    convert_scalar,
    load_prompt_file,
    scan_directory,
)
from .search import collect_tags, search_by_tag


def build_parser():
    parser = argparse.ArgumentParser(
        prog="prompt-tag-organizer",
        description=(
            "Organize your best prompts, locally. Scan Markdown/JSON prompt files, "
            "add tags/task/score frontmatter, search by tag with fuzzy terms, flag "
            "near-duplicates, and export a browsable HTML index. Optional AI tagging "
            "via any OpenAI-compatible endpoint (Ollama included, no keys)."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "directory",
        type=Path,
        help="folder containing your prompt files",
    )
    common.add_argument(
        "-e", "--extensions",
        default=",".join(ext.lstrip(".") for ext in DEFAULT_EXTENSIONS),
        help="comma-separated file extensions to scan (default: md,json)",
    )

    scan = sub.add_parser("scan", parents=[common], help="list prompt files and their frontmatter")
    scan.add_argument("--json", action="store_true", help="print results as JSON")

    tag = sub.add_parser("tag", help="add tags/task/score frontmatter to a prompt file (or JSON item)")
    tag.add_argument("file", type=Path, help="prompt file to update")
    tag.add_argument("-i", "--index", type=int, default=None, help="index of the item inside a JSON list/array group")
    tag.add_argument("--group", default=None, help="name of a JSON array group to target")
    tag.add_argument("--tags", default="", help="comma-separated tags to set")
    tag.add_argument("--add-tags", default="", help="comma-separated tags to merge in (AI suggestions)")
    tag.add_argument("--task", default=None, help="short task description")
    tag.add_argument("--score", default=None, help="quality score (e.g. 1-5)")
    tag.add_argument("--title", default=None, help="override the title")
    tag.add_argument("--dry-run", action="store_true", help="show the result without writing")
    tag.add_argument("--remove", action="store_true", help="remove the frontmatter instead")

    search = sub.add_parser("search", parents=[common], help="search prompts by tag with fuzzy terms")
    search.add_argument("--tag", required=True, help="tag to search for (fuzzy matched)")
    search.add_argument("--strict", action="store_true", help="match the exact tag only")

    dupes = sub.add_parser("dupes", parents=[common], help="flag near-duplicate prompts")
    dupes.add_argument("--threshold", type=float, default=0.9, help="similarity threshold 0-1 (default: 0.9)")
    dupes.add_argument("--fix", action="store_true", help="keep one duplicate per cluster and add a 'dupe' tag to the rest, writing 'kept' to the best prompt")

    export = sub.add_parser("export", parents=[common], help="export a browsable HTML index")
    export.add_argument("-o", "--output", type=Path, default=None, help="output HTML file (default: index.html in the folder)")
    export.add_argument("--title", default="Prompt Index", help="page title")
    export.add_argument("--threshold", type=float, default=0.9, help="near-duplicate similarity threshold")

    aitag = sub.add_parser("ai-tag", parents=[common], help="suggest tags/task for prompts via an OpenAI-compatible endpoint (Ollama included)")
    aitag.add_argument("--base-url", default=ai_mod.DEFAULT_BASE_URL, help="endpoint base URL (default: Ollama on localhost:11434)")
    aitag.add_argument("--model", default=ai_mod.DEFAULT_MODEL, help=f"model name (default: {ai_mod.DEFAULT_MODEL})")
    aitag.add_argument("--file", type=Path, default=None, help="only tag this one file")
    aitag.add_argument("--apply", action="store_true", help="write suggested tags/task into frontmatter")
    aitag.add_argument("--dry-run", action="store_true", help="show suggestions without writing (default when not --apply)")

    return parser


def _ext_list(extensions):
    exts = tuple("." + e.strip().lstrip(".") for e in extensions.split(",") if e.strip())
    return exts or DEFAULT_EXTENSIONS


def cmd_scan(args):
    prompts = scan_directory(args.directory, extensions=_ext_list(args.extensions))
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "path": p.path,
                        "fmt": p.fmt,
                        "title": p.title,
                        "tags": p.tags,
                        "task": p.meta.get("task"),
                        "score": p.score,
                        "chars": len(p.body),
                    }
                    for p in prompts
                ],
                indent=2,
            )
        )
        return 0
    print(f"Found {len(prompts)} prompt(s) in {args.directory}")
    for prompt in prompts:
        tags = " ".join(f"#{tag}" for tag in prompt.tags) or "(no tags)"
        print(f"\n  {prompt.path}")
        print(f"    {prompt.title}")
        print(f"    {tags}" + (f" | task: {prompt.meta['task']}" if prompt.meta.get("task") else "") + (f" | score: {prompt.score}" if prompt.score is not None else ""))
    return 0


def cmd_tag(args):
    targets = load_prompt_file(args.file)
    if not targets:
        print(f"No prompts found in {args.file}", file=sys.stderr)
        return 1
    if args.index is not None:
        chosen = [p for p in targets if p.meta.get("$index") == args.index]
        if not chosen:
            print(f"--index {args.index} not found in {args.file}", file=sys.stderr)
            return 1
    elif args.group:
        chosen = [p for p in targets if p.meta.get("group") == args.group]
        if not chosen:
            print(f"--group {args.group!r} not found in {args.file}", file=sys.stderr)
            return 1
    else:
        chosen = targets
    new_tags = [t.strip().lower() for t in args.tags.split(",") if t.strip()]
    add_tags = [t.strip().lower() for t in args.add_tags.split(",") if t.strip()]
    for prompt in chosen:
        if args.remove:
            meta = {}
        else:
            meta = dict(prompt.meta)
            if new_tags:
                meta["tags"] = new_tags
            elif add_tags:
                merged = list(dict.fromkeys(prompt.tags + add_tags))
                meta["tags"] = merged
            if args.task is not None:
                meta["task"] = args.task
            if args.score is not None:
                score = convert_scalar(args.score)
                meta["score"] = float(score) if isinstance(score, float) else score
            if args.title is not None:
                meta["title"] = args.title
        print(f"File: {prompt.path}")
        action = "removing frontmatter" if args.remove else "setting"
        print(
            f"  {action}: tags={meta.get('tags', [])} task={meta.get('task')!r} "
            f"score={meta.get('score')!r}"
        )
        apply_frontmatter_to_file(args.file, prompt, meta, args.dry_run)
    return 0


def apply_frontmatter_to_file(file_path, prompt, meta, dry_run):
    content, _had = apply_frontmatter(file_path, prompt, meta)
    if dry_run:
        print("--- would write ---")
        print(content[:600])
        return
    Path(file_path).write_text(content, encoding="utf-8")
    print(f"  written to {file_path}")


def cmd_search(args):
    prompts = scan_directory(args.directory, extensions=_ext_list(args.extensions))
    matched, results = search_by_tag(prompts, args.tag, strict=args.strict)
    if not matched:
        all_available = sorted(collect_tags(prompts))
        print(f"No tag close to {args.tag!r} found.")
        if all_available:
            print("Available tags: " + " ".join(f"#{t}" for t in all_available))
        return 0
    print(f"Matched tags: {' '.join(f'#{t}' for t in matched)}")
    print(f"{len(results)} prompt(s):")
    for prompt in results:
        print(f"\n  {prompt.path}")
        print(f"    {prompt.title}")
        print("    " + " ".join(f"#{t}" for t in prompt.tags))
    return 0


def cmd_dupes(args):
    prompts = scan_directory(args.directory, extensions=_ext_list(args.extensions))
    clusters = find_duplicates(prompts, threshold=args.threshold)
    if not clusters:
        print(f"No near-duplicates found in {len(prompts)} prompt(s).")
        return 0
    flagged = duplicate_map(clusters)
    print(f"{len(clusters)} cluster(s) of near-duplicates (threshold {args.threshold}):")
    for cluster in clusters:
        print("\n  Cluster:")
        for prompt, score in cluster:
            print(f"    {prompt.path} (similarity {score:.2f})")
    print(f"{len(flagged)} prompt(s) flagged total. Re-run 'export' to include the flags in an index page.")
    return 0


def cmd_export(args):
    prompts = scan_directory(args.directory, extensions=_ext_list(args.extensions))
    clusters = find_duplicates(prompts, threshold=args.threshold)
    flagged = duplicate_map(clusters)
    out_path = args.output or (args.directory / "index.html")
    export_index(prompts, out_path, duplicate_map=flagged, title=args.title, threshold=args.threshold)
    print(f"Exported {len(prompts)} prompt(s), {len(flagged)} near-duplicate flag(s) -> {out_path}")
    return 0


def cmd_ai_tag(args):
    if args.file:
        prompts = load_prompt_file(args.file)
    else:
        prompts = scan_directory(args.directory, extensions=_ext_list(args.extensions))
    prompts = [p for p in prompts if p.body.strip()]
    if not prompts:
        print("No prompts with bodies found to tag.", file=sys.stderr)
        return 1
    print(
        f"Reading {len(prompts)} prompt(s) against {args.base_url} (model {args.model})."
        + (" (dry run)" if not args.apply else "")
    )
    updated = 0
    for prompt in prompts:
        try:
            tags, task = ai_mod.suggest(prompt.body, base_url=args.base_url, model=args.model)
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        preview = " ".join(f"#{t}" for t in tags) or "(none)"
        print(f"\n  {prompt.path}")
        print(f"    suggested: {preview}")
        if task:
            print(f"    task: {task}")
        if not args.apply:
            continue
        is_md = prompt.fmt == "md" and "[" not in prompt.path and "#" not in prompt.path
        if is_md:
            base = prompt.path
            meta = dict(prompt.meta)
            if tags:
                meta["tags"] = list(dict.fromkeys(prompt.tags + tags))
            if task:
                meta["task"] = task
            content, _had = apply_frontmatter(base, prompt, meta)
            Path(base).write_text(content, encoding="utf-8")
            updated += 1
        elif prompt.fmt == "json":
            base = prompt.path.split("[")[0].split("#")[0]
            meta = dict(prompt.meta)
            meta.pop("$index", None)
            meta.pop("group", None)
            if tags:
                meta["tags"] = list(dict.fromkeys(prompt.tags + tags))
            if task:
                meta["task"] = task
            update_json_file(Path(base), prompt, meta)
            updated += 1
    if args.apply:
        print(f"\nApplied suggestions to {updated} prompt file(s).")
    else:
        print("\nDry run only. Re-run with --apply to write these suggestions.")
    return 0


def update_json_file(json_path, prompt, meta):
    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    index = prompt.meta.get("$index")
    group = prompt.meta.get("group")
    target = None
    if index is not None and isinstance(data, list):
        target = data[index]
    elif group and isinstance(data, dict):
        value = data.get(group)
        if isinstance(value, list) and index is not None and index < len(value):
            target = value[index]
    elif index is None:
        target = data
    if isinstance(target, dict):
        for key, value in meta.items():
            target[key] = value
        with open(json_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        print(f"  written to {json_path}")


COMMANDS = {
    "scan": cmd_scan,
    "tag": cmd_tag,
    "search": cmd_search,
    "dupes": cmd_dupes,
    "export": cmd_export,
    "ai-tag": cmd_ai_tag,
}


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return COMMANDS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
