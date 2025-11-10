import argparse
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Final

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

    args: argparse.Namespace = parser.parse_args()

    root: Path = Path.cwd()
    excludes: set[str] = set(args.exclude or [])
    outfile: Path = root / args.output

    include_exts: set[str] = normalise_exts(args.include_ext)
    exclude_exts: set[str] = normalise_exts(args.exclude_ext) | set(DEFAULT_BINARY_EXTS)

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
                collected_files.append(e)

    tree_lines.append('.')
    walk(root)

    now: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with outfile.open('w', encoding='utf-8') as f:
        f.write(f"# Snapshot of {root.name}\n\n")
        f.write(f"Generated: {now}\n\n")

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
