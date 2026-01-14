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

- **Files modified in the last 30 minutes**

  ```bash
  dir2md -m 30
  ```

- **Files created in the last hour**

  ```bash
  dir2md -c 60
  ```

- **Either modified OR created in the last 2 hours**

  ```bash
  dir2md -m 120 -c 120
  ```

- **Combine with other filters - recent TypeScript changes**
  ```bash
  dir2md --include-ext ts -m 60
  ```

Mix and match these options to tailor the Markdown output to your workflow.

## Example Output

[directory_snapshot.md](./directory_snapshot.md)

## License

Released under the [MIT License](./LICENSE).
