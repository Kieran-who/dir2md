import argparse
from collections.abc import Iterable
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Final
import time

DEFAULT_EXCLUDES: Final[set[str]] = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'dist', 'build'}
DEFAULT_BINARY_EXTS: Final[set[str]] = {
    '.png','.jpg','.jpeg','.gif','.webp','.bmp','.tif','.tiff','.ico',
    '.pdf','.zip','.rar','.gz','.bz2','.xz','.7z','.tar','.tgz',
    '.jar','.war','.ear','.class','.exe','.dll','.so','.dylib','.o','.a',
    '.bin','.dat','.psd','.ai','.eps'
}

LANG_MAP: Final[dict[str, str]] = {
    '.py':'python', '.ts':'typescript', '.js':'javascript', '.tsx':'tsx', '.jsx':'jsx',
    '.json':'json', '.md':'markdown', '.yml':'yaml', '.yaml':'yaml',
    '.sh':'bash', '.bash':'bash', '.zsh':'bash', '.ps1':'powershell', '.bat':'bat',
    '.ini':'ini', '.toml':'toml', '.html':'html', '.htm':'html', '.css':'css',
    '.scss':'scss', '.less':'less', '.xml':'xml',
    '.c':'c', '.h':'c', '.cpp':'cpp', '.hpp':'cpp', '.cc':'cpp',
    '.java':'java', '.kt':'kotlin', '.rb':'ruby', '.go':'go', '.rs':'rust',
    '.php':'php', '.pl':'perl', '.swift':'swift', '.cs':'csharp', '.sql':'sql'
}

def detect_lang(path: Path) -> str:
    if path.name == 'Dockerfile':
        return 'dockerfile'
    if path.name == 'Makefile':
        return 'make'
    return LANG_MAP.get(path.suffix.lower(), '')

def normalise_exts(exts: Iterable[str] | None) -> set[str]:
    if not exts:
        return set()
    out: set[str] = set()
    for e in exts:
        e = e.strip()
        if not e:
            continue
        if not e.startswith('.'):
            e = '.' + e
        out.add(e.lower())
    return out

def looks_binary(p: Path) -> bool:
    try:
        with p.open('rb') as rf:
            chunk = rf.read(8192)
        return b'\0' in chunk
    except Exception:
        return True

def matches_any_pattern(rel_path: str, patterns: list[str]) -> bool:
    """Check if relative path matches any of the given glob patterns."""
    for pattern in patterns:
        if fnmatch(rel_path, pattern):
            return True
    return False

def file_passes_time_filter(p: Path, modified_cutoff: float | None, created_cutoff: float | None) -> bool:
    """Check if file passes the time-based filters."""
    if modified_cutoff is None and created_cutoff is None:
        return True
    
    stat = p.stat()
    
    if modified_cutoff is not None and stat.st_mtime >= modified_cutoff:
        return True
    
    if created_cutoff is not None:
        # st_birthtime is macOS-specific; fall back to st_ctime on other platforms
        ctime = getattr(stat, 'st_birthtime', stat.st_ctime)
        if ctime >= created_cutoff:
            return True
    
    # If either filter was specified but neither passed, exclude the file
    return False

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dump directory structure and text file contents to Markdown."
    )
    parser.add_argument('-o', '--output', default='directory_snapshot.md',
                        help='Output Markdown filename (default: directory_snapshot.md)')
    parser.add_argument('--exclude', nargs='*', default=list(DEFAULT_EXCLUDES),
                        help='Names to exclude anywhere in the path (dirs or files)')
    parser.add_argument('--max-size', type=int, default=None,
                        help='Max bytes per file to include; if omitted, include full file')
    parser.add_argument('--show-hidden', action='store_true',
                        help='Include dotfiles and hidden directories')
    
    parser.add_argument('--include-ext', nargs='*', default=None,
                        help='Only include files with these extensions (e.g. .py .ts .md or py ts md)')
    parser.add_argument('--exclude-ext', nargs='*', default=None,
                        help='Exclude files with these extensions (e.g. .log .md). Binaries are excluded by default.')
    parser.add_argument('-p', '--pattern', nargs='*', default=None,
                        help='Glob patterns to include files (e.g. "*/files.*.ts" "src/**/*.py")')
    parser.add_argument('-P', '--exclude-pattern', nargs='*', default=None,
                        help='Glob patterns to exclude files (e.g. "__tests__/*" "*.test.ts")')
    parser.add_argument('-m', '--modified-within', type=int, default=None, metavar='MINUTES',
                        help='Only include files modified within the last N minutes')
    parser.add_argument('-c', '--created-within', type=int, default=None, metavar='MINUTES',
                        help='Only include files created within the last N minutes')

    args: argparse.Namespace = parser.parse_args()

    root: Path = Path.cwd()
    excludes: set[str] = set(args.exclude or [])
    outfile: Path = root / args.output

    include_exts: set[str] = normalise_exts(args.include_ext)
    exclude_exts: set[str] = normalise_exts(args.exclude_ext) | set(DEFAULT_BINARY_EXTS)
    include_patterns: list[str] | None = args.pattern
    exclude_patterns: list[str] | None = args.exclude_pattern

    # Calculate time cutoffs
    now = time.time()
    modified_cutoff: float | None = None
    created_cutoff: float | None = None
    
    if args.modified_within is not None:
        modified_cutoff = now - (args.modified_within * 60)
    if args.created_within is not None:
        created_cutoff = now - (args.created_within * 60)

    def is_hidden(p: Path) -> bool:
        return p.name.startswith('.')

    def skip(e: Path) -> bool:
        if e.is_symlink():
            return True
        if e == outfile:
            return True
        for part in e.parts:
            if part in excludes:
                return True
        if not args.show_hidden and is_hidden(e) and e != root:
            return True
        return False

    def list_entries(dirp: Path) -> list[Path]:
        items: list[Path] = []
        for e in sorted(dirp.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if skip(e):
                continue
            items.append(e)
        return items

    tree_lines: list[str] = []
    collected_files: list[Path] = []

    def walk(dirp: Path, prefix: str = '') -> None:
        entries: list[Path] = list_entries(dirp)
        for i, e in enumerate(entries):
            is_last: bool = i == len(entries) - 1
            connector: str = '└── ' if is_last else '├── '
            if e.is_dir():
                tree_lines.append(prefix + connector + e.name + '/')
                walk(e, prefix + ('    ' if is_last else '│   '))
            else:
                tree_lines.append(prefix + connector + e.name)
                ext: str = e.suffix.lower()
                if include_exts and ext not in include_exts:
                    continue
                if ext in exclude_exts:
                    continue
                if looks_binary(e):
                    continue
                rel_path: str = e.relative_to(root).as_posix()
                if include_patterns and not matches_any_pattern(rel_path, include_patterns):
                    continue
                if exclude_patterns and matches_any_pattern(rel_path, exclude_patterns):
                    continue
                if not file_passes_time_filter(e, modified_cutoff, created_cutoff):
                    continue
                collected_files.append(e)

    tree_lines.append('.')
    walk(root)

    now_str: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with outfile.open('w', encoding='utf-8') as f:
        f.write(f"# Snapshot of {root.name}\n\n")
        f.write(f"Generated: {now_str}\n\n")

        f.write("## Directory tree\n\n")
        f.write("```text\n")
        for line in tree_lines:
            f.write(line + "\n")
        f.write("```\n\n")

        f.write("## File contents\n\n")
        for p in collected_files:
            rel: str = p.relative_to(root).as_posix()

            size: int = p.stat().st_size
            truncated: bool = False

            max_size: int | None = args.max_size

            if max_size is not None and size > max_size:
                with p.open('rb') as rf:
                    data: bytes = rf.read(max_size)
                truncated = True
            else:
                with p.open('rb') as rf:
                    data = rf.read()
            
            try:
                text: str = data.decode('utf-8', errors='replace')
            except Exception:
                text = data.decode('latin-1', errors='replace')

            lang: str = detect_lang(p)

            f.write(f"### {rel}\n\n")
            f.write(f"```{lang}\n")
            f.write(text)
            if not text.endswith('\n'):
                f.write("\n")
            f.write("```\n\n")
            if truncated:
                f.write(f"> Note: truncated to {args.max_size} bytes from {size} bytes.\n\n")

    print(f"Wrote {outfile}")

if __name__ == '__main__':
    main()