# Worklane Journal — how to publish a blog post

All blog pages share one stylesheet (`blog/blog.css`), so every post automatically
has the same design. The Journal listing page (`blog/index.html`) builds itself
from `blog/posts.json` — with search and category filters included.

## Publish a new post (2 steps)

1. **Copy the template.**
   Duplicate `blog/post-template.html` → `blog/posts/<your-slug>.html`
   (slug = lowercase-words-with-hyphens, e.g. `audit-readiness-checklist`).
   Replace every `{{PLACEHOLDER}}` and write your content inside
   `<div class="article-body">`. The instructions are at the top of the template.

2. **Register it in the manifest.**
   Add one entry at the TOP of the `posts` array in `blog/posts.json`:

   ```json
   {
     "slug": "audit-readiness-checklist",
     "title": "Audit Readiness Checklist",
     "excerpt": "One or two sentences shown on the Journal page.",
     "category": "Accounting",
     "date": "2026-08-01",
     "dateDisplay": "Aug 1, 2026",
     "author": "Worklane Financial Advisory",
     "readTime": "5 min read",
     "tags": ["audit", "checklist"]
   }
   ```

   `slug` must exactly match the filename (without `.html`).

That's it. The post appears on the Journal page, is searchable by title,
category and tags, and is Google-indexable (static HTML with meta description,
canonical URL, Open Graph tags and JSON-LD BlogPosting schema baked in).

## Notes

- Categories in the filter chips are generated automatically from posts.json.
- To add a hero image: put it in `uploads/` and un-comment the `<figure>` block
  in the post.
- Update the `canonical` URL domain in the template if the site's final domain
  differs from `worklane.com.np`.
- For best Google indexing after deploying, submit a sitemap or the new URL in
  Google Search Console.
