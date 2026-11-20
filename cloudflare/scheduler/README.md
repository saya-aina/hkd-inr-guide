# Cloudflare scheduler

A tiny Worker that triggers the GitHub workflows on time. See worker.js.

Setup (Cloudflare dashboard):
1. Workers & Pages, Create, Create Worker, name it `nriremit-scheduler`, Deploy, then Edit code and paste worker.js.
2. Settings, Variables and Secrets: add secret `GITHUB_TOKEN` (fine-grained PAT, only repo saya-aina/hkd-inr-guide, permission Actions: Read and write).
3. Settings, Triggers, Cron Triggers: add `30 1 * * *` and `0 * * * *`.
4. Test: Triggers page, or run once by hand and check the Actions tab.
