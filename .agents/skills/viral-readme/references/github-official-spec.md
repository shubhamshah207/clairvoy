# Reference: GitHub Official Specification for Repository READMEs

**Source**: [GitHub Docs: About the repository README file](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)  
**Retrieved**: 2026-09-13

---

## 1. Overview & Purpose
You can add a README file to your repository to communicate important information about your project. A README, along with a repository license, citation file, contribution guidelines, and a code of conduct, communicates expectations for your project and helps you manage contributions.

A README is often the first item a visitor will see when visiting your repository. README files typically include information on:
- **What the project does**
- **Why the project is useful**
- **How users can get started with the project**
- **Where users can get help with your project**
- **Who maintains and contributes to the project**

---

## 2. Discovery & Precedence
If you put your README file in your repository's hidden `.github`, root, or `docs` directory, GitHub will recognize and automatically surface your README to repository visitors.

If a repository contains more than one README file, then the file shown is chosen from locations in the following order:
1. `.github/` directory
2. Repository's root directory (`/`)
3. `docs/` directory

### Size Limit
When your README is viewed on GitHub, **any content beyond 500 KiB will be truncated**.

### Profile README
If you add a README file to the root of a public repository with the same name as your username, that README will automatically appear on your GitHub profile page.

---

## 3. Automated Navigation & Anchors

### Auto-Generated Table of Contents
For the rendered view of any Markdown file in a repository, GitHub automatically generates a table of contents based on section headings (`H2`, `H3`, etc.). Visitors can open the table of contents via the "Outline" menu icon in the top corner.

### Section Links (Heading Anchors)
GitHub automatically generates anchor links for all markdown headings. Clicking the link icon displays the direct URL anchor (e.g. `#quick-start`).

---

## 4. Relative Links & Image Assets

### Branch-Resilient Relative Links
You can define relative links and image paths in your rendered files to help readers navigate to other files in your repository.

GitHub automatically transforms relative links or image paths based on whatever branch the user is currently viewing, so that the link or path always works.
- Relative links (e.g., `docs/CONTRIBUTING.md` or `docs/assets/screenshot.png`) are relative to the current file.
- Links starting with `/` will be relative to the repository root.
- Operands such as `./` and `../` are fully supported.

### Critical Formatting Rule
Link text MUST be on a single line. Multi-line link anchors break rendering on GitHub:
```markdown
<!-- CORRECT: -->
[Contribution guidelines](docs/CONTRIBUTING.md)

<!-- INCORRECT (Will break): -->
[Contribution
guidelines](docs/CONTRIBUTING.md)
```

### Why Relative Links are Mandatory
Relative links are easier for users who clone your repository. Absolute links or raw CDN URLs (`raw.githubusercontent.com/...`) break in private repositories, offline environments, forks, and branch switches.

---

## 5. Scope & Separation of Concerns
A README should only contain information necessary for developers to get started using and contributing to your project. Longer, encyclopedic documentation is best suited for wikis, dedicated docs directories (`docs/`), or documentation websites (e.g. MkDocs, Docusaurus).
