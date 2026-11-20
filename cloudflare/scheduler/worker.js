// Cloudflare Worker: triggers GitHub workflows on time (GitHub's own cron can run hours late).
// Secrets/vars (set in the Worker settings, never in this file):
//   GITHUB_TOKEN  fine-grained PAT, repo saya-aina/hkd-inr-guide only, permission "Actions: Read and write"
// Cron triggers (UTC): "30 1 * * *"  -> daily alert (07:00 IST)
//                      "0 * * * *"   -> hourly rates refresh
const REPO = "saya-aina/hkd-inr-guide";

async function dispatch(env, workflow, inputs) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "nriremit-scheduler",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({ ref: "main", inputs }),
  });
  if (r.status !== 204) throw new Error(`${workflow} dispatch failed: ${r.status} ${await r.text()}`);
}

export default {
  async scheduled(event, env, ctx) {
    if (event.cron === "30 1 * * *") ctx.waitUntil(dispatch(env, "send-alerts.yml", { dry_run: "0" }));
    else if (event.cron === "0 * * * *") ctx.waitUntil(dispatch(env, "update-rates.yml", {}));
  },
};
