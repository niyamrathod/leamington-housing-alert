/**
 * signup-worker.js
 *
 * Receives the email sign-up form submission from
 * niyamrathod.github.io/leamington-housing-alert.html and commits the
 * new address into recipients.json in the leamington-housing-alert repo,
 * using GitHub's Contents API. This is what makes sign-up fully
 * automatic - main.py reads recipients.json fresh on every scheduled
 * run, so a new address is picked up on the next alert check with no
 * manual step.
 *
 * Deploy: paste this whole file into a new Cloudflare Worker (Workers &
 * Pages > Create > Worker > paste into the editor), then set a Worker
 * secret named GITHUB_TOKEN holding a fine-grained GitHub PAT scoped to
 * ONLY this repo with "Contents: Read and write" permission - nothing
 * broader. The token never reaches the browser; it only lives here,
 * server-side.
 */

const OWNER = "niyamrathod";
const REPO = "leamington-housing-alert";
const FILE_PATH = "recipients.json";
const ALLOWED_ORIGIN = "https://niyamrathod.github.io";
const MAX_RECIPIENTS = 200; // hard cap so a burst of abuse can't grow this file without bound
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default {
  async fetch(request, env) {
    const corsHeaders = {
      "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }
    if (request.method !== "POST") {
      return jsonResponse({ error: "Method not allowed" }, 405, corsHeaders);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return jsonResponse({ error: "Invalid request." }, 400, corsHeaders);
    }

    // Honeypot field: real visitors never fill this in, so a non-empty
    // value almost always means a bot. Pretend success so bots don't
    // learn their submission was rejected and adjust their behaviour.
    if (body.website) {
      return jsonResponse({ ok: true }, 200, corsHeaders);
    }

    const email = String(body.email || "").trim().toLowerCase();
    if (!EMAIL_PATTERN.test(email)) {
      return jsonResponse({ error: "Enter a valid email address." }, 400, corsHeaders);
    }

    try {
      const result = await addRecipient(email, env);
      const message = result.alreadySignedUp
        ? "You're already signed up."
        : "You're signed up! Watch your inbox.";
      return jsonResponse({ ok: true, message }, 200, corsHeaders);
    } catch (error) {
      const status = error.message === "list-full" ? 429 : 502;
      const message = error.message === "list-full"
        ? "Sign-ups are temporarily full - contact Niyam directly."
        : "Could not save your sign-up. Please try again shortly.";
      return jsonResponse({ error: message }, status, corsHeaders);
    }
  },
};

/**
 * Reads recipients.json, appends `email` if it's not already there, and
 * commits the update via GitHub's Contents API. Retries once on a 409/422
 * conflict (another submission updated the file in between our read and
 * write) by re-reading and re-attempting with the fresh SHA.
 */
async function addRecipient(email, env) {
  const apiUrl = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${FILE_PATH}`;
  const githubHeaders = {
    "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
    "Accept": "application/vnd.github+json",
    "User-Agent": "leamington-housing-alert-signup-worker",
  };

  for (let attempt = 0; attempt < 2; attempt++) {
    const getResponse = await fetch(apiUrl, { headers: githubHeaders });
    if (!getResponse.ok) throw new Error("read-failed");
    const fileData = await getResponse.json();
    const currentRecipients = JSON.parse(atob(fileData.content));

    if (currentRecipients.map((e) => e.toLowerCase()).includes(email)) {
      return { alreadySignedUp: true };
    }
    if (currentRecipients.length >= MAX_RECIPIENTS) {
      throw new Error("list-full");
    }

    const updatedRecipients = [...currentRecipients, email];
    const putResponse = await fetch(apiUrl, {
      method: "PUT",
      headers: { ...githubHeaders, "Content-Type": "application/json" },
      body: JSON.stringify({
        message: `Add ${email} to alert recipients`,
        content: btoa(JSON.stringify(updatedRecipients, null, 2) + "\n"),
        sha: fileData.sha,
      }),
    });

    if (putResponse.ok) return { alreadySignedUp: false };
    if (putResponse.status !== 409 && putResponse.status !== 422) {
      throw new Error("write-failed");
    }
    // Someone else's submission changed the file between our GET and PUT -
    // loop and retry once with a freshly-read SHA.
  }
  throw new Error("write-failed");
}

function jsonResponse(data, status, corsHeaders) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}
