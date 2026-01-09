# Snapshot of dir2md

Generated: 2026-01-09 18:20:56

## Directory tree

```text
.
├── src/
│   ├── dir2md/
│   │   ├── __init__.py
│   │   └── cli.py
│   └── dir2md.egg-info/
│       ├── dependency_links.txt
│       ├── entry_points.txt
│       ├── PKG-INFO
│       ├── SOURCES.txt
│       └── top_level.txt
├── LICENSE
├── pyproject.toml
└── README.md
```

## File contents

### src/dir2md/__init__.py

```python
__version__ = "0.1.1"
```

### src/dir2md/cli.py

```python
import argparse
from collections.abc import Iterable
from datetime import datetime
from fnmatch import fnmatch
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

def matches_any_pattern(rel_path: str, patterns: list[str]) -> bool:
    """Check if relative path matches any of the given glob patterns."""
    for pattern in patterns:
        if fnmatch(rel_path, pattern):
            return True
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

    args: argparse.Namespace = parser.parse_args()

    root: Path = Path.cwd()
    excludes: set[str] = set(args.exclude or [])
    outfile: Path = root / args.output

    include_exts: set[str] = normalise_exts(args.include_ext)
    exclude_exts: set[str] = normalise_exts(args.exclude_ext) | set(DEFAULT_BINARY_EXTS)
    include_patterns: list[str] | None = args.pattern
    exclude_patterns: list[str] | None = args.exclude_pattern

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
```

### src/dir2md.egg-info/dependency_links.txt

```

```

### src/dir2md.egg-info/entry_points.txt

```
[console_scripts]
dir2md = dir2md.cli:main
```

### src/dir2md.egg-info/PKG-INFO

```
Metadata-Version: 2.4
Name: dir2md
Version: 0.1.1
Summary: Dump directory tree and text contents to Markdown
Author: Kieran Lindsay
License: MIT
Requires-Python: >=3.8
Description-Content-Type: text/markdown
License-File: LICENSE
Dynamic: license-file

# dir2md

Dump directory structure and text contents into a single Markdown file for easy sharing and review (especially for LLMs). Includes some basic default filters to avoid dumping binary files and directories like `node_modules`.

## Installation

Clone the repository:

```bash
git clone https://github.com/kieranlindsay/dir2md.git
cd dir2md
```

Using [uv](https://uv.run/) to install directly from the repository:

```bash
uv tool install .
```

Using [pipx](https://pipxproject.github.io/pipx/) to install:

```bash
pipx install .
```

## Usage

Run `dir2md --help` to see every available flag. Common examples are below:

- **Basic dump:**
  ```bash
  dir2md
  ```
- **Custom output file:**
  ```bash
  dir2md -o my_dump.md
  ```
- **Include only certain file types:**
  ```bash
  dir2md --include-ext py ts js
  ```
- **Exclude specific extensions:**
  ```bash
  dir2md --exclude-ext log md
  ```
- **Exclude directories:**
  ```bash
  dir2md --exclude .git node_modules .next dist
  ```
- **Cap per-file size (recommended for large repos):**
  ```bash
  dir2md --max-size 262144
  ```
- **Include dotfiles:**
  ```bash
  dir2md --show-hidden
  ```
- **Filter by glob pattern:**
  ```bash
  dir2md -p "*/files.*.ts"
  ```
- **Multiple patterns:**
  ```bash
  dir2md -p "*/*.routes.ts" "*/*.controller.ts"
  ```
- **Recursive pattern matching:**
  ```bash
  dir2md -p "src/**/*.py"
  ```

Mix and match these options to tailor the Markdown output to your workflow.

## Example Output

[directory_snapshot.md](./directory_snapshot.md)

## License

Released under the [MIT License](./LICENSE).
```

### src/dir2md.egg-info/SOURCES.txt

```
LICENSE
README.md
pyproject.toml
src/dir2md/__init__.py
src/dir2md/cli.py
src/dir2md.egg-info/PKG-INFO
src/dir2md.egg-info/SOURCES.txt
src/dir2md.egg-info/dependency_links.txt
src/dir2md.egg-info/entry_points.txt
src/dir2md.egg-info/top_level.txt
```

### src/dir2md.egg-info/top_level.txt

```
dir2md
```

### LICENSE

```
MIT License

Copyright (c) 2025 Kieran Lindsay

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "dir2md"
version = "0.1.1"
description = "Dump directory tree and text contents to Markdown"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [{ name = "Kieran Lindsay" }]

[project.scripts]
dir2md = "dir2md.cli:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
```

### README.md

```markdown
# dir2md

Dump directory structure and text contents into a single Markdown file for easy sharing and review (especially for LLMs). Includes some basic default filters to avoid dumping binary files and directories like `node_modules`.

## Installation

Clone the repository:

```bash
git clone https://github.com/kieranlindsay/dir2md.git
cd dir2md
```

Using [uv](https://uv.run/) to install directly from the repository:

```bash
uv tool install .
```

Using [pipx](https://pipxproject.github.io/pipx/) to install:

```bash
pipx install .
```

## Usage

Run `dir2md --help` to see every available flag. Common examples are below:

- **Basic dump:**
  ```bash
  dir2md
  ```
- **Custom output file:**
  ```bash
  dir2md -o my_dump.md
  ```
- **Include only certain file types:**
  ```bash
  dir2md --include-ext py ts js
  ```
- **Exclude specific extensions:**
  ```bash
  dir2md --exclude-ext log md
  ```
- **Exclude directories:**
  ```bash
  dir2md --exclude .git node_modules .next dist
  ```
- **Cap per-file size (recommended for large repos):**
  ```bash
  dir2md --max-size 262144
  ```
- **Include dotfiles:**
  ```bash
  dir2md --show-hidden
  ```
- **Filter by glob pattern:**
  ```bash
  dir2md -p "*/files.*.ts"
  ```
- **Multiple patterns:**
  ```bash
  dir2md -p "*/*.routes.ts" "*/*.controller.ts"
  ```
- **Recursive pattern matching:**
  ```bash
  dir2md -p "src/**/*.py"
  ```
- **Exclude using pattern matching:**

  ```bash
  # E.g. exclude all files in __tests__ directories
  dir2md -P "__tests__/*"

  # Exclude test files at any depth
  dir2md -P "**/*.test.ts" "**/*.spec.ts"
  ```

- **Combine include and exclude patterns:**

  ```bash
  dir2md -p "src/**/*.ts" -P "**/*.test.ts" "__tests__/*"

  ```

Mix and match these options to tailor the Markdown output to your workflow.

## Example Output

[directory_snapshot.md](./directory_snapshot.md)

## License

Released under the [MIT License](./LICENSE).
```

