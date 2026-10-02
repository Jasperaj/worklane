# Worklane Static Website

A minimal, sophisticated multi-page static site concept for a financial advisory brand.

## Pages
- `index.html` — home
- `experience.html` — credentials and background
- `services.html` — advisory offerings
- `insights.html` — thought leadership
- `contact.html` — contact and intake details

## Run locally
```bash
cd worklane-site
python3 -m http.server 8080
```

## GitHub Pages deployment (already wired)
This repository now includes a GitHub Actions workflow at:
- `.github/workflows/deploy-worklane-pages.yml`

The workflow deploys **only** the `worklane-site/` folder to GitHub Pages, so you do not need to move files to repository root.

### One-time setup
1. Push this branch to GitHub.
2. In GitHub repo settings, open **Pages**.
3. Under **Build and deployment**, set **Source** to **GitHub Actions**.
4. Ensure your default branch is `main` (or update the workflow branch trigger).

### Deploy behavior
- Deploy runs automatically on pushes to `main` when files under `worklane-site/**` change.
- You can also trigger deployment manually from the **Actions** tab using **workflow_dispatch**.
