# Authentication and integrations (optional)

Nexora remains a loopback-only, single-user application. It continues to work with Ollama, Knowledge, and existing local projects without Google, GitHub, SMTP, or a login account. Authentication is optional; enabling it creates one owner for this local installation. It does **not** make the existing database multi-user or provide per-user data isolation. Do not expose this single-user app to an untrusted network.

## First run and local account

1. Start Nexora and open `http://127.0.0.1:8501`.
2. Open **Settings → Account & Integrations** (or `http://127.0.0.1:8501/setup`).
3. You can continue using the local app without an account. To enable sign-in, use **Set up or sign in to the local account** and create the one local owner with a password of at least 12 characters.
4. Passwords are stored as Argon2id hashes. Session cookies are opaque, server-side, HttpOnly, SameSite=Strict, and expire after 12 hours. Unsafe requests require a matching CSRF token and same-origin request.

The installation is single-user: all existing SQLite settings, chats, Knowledge collections, indexed documents, GitHub projects, and conversation records remain global to this one local app. The optional owner sign-in is a local access gate, not a tenant boundary. No existing records are assigned to a newly invented user id, and no multi-user account linking is offered.

Local account email is an identifier only; registration does not claim email verification and sends no email. Password reset is unavailable until you configure and test your own SMTP server. If SMTP is unavailable, a local operator can run `python scripts/reset_local_auth.py` from the project folder and set a new password at the console; this requires local filesystem access and does not send email.

## Google sign-in (optional)

1. In Google Cloud Console, configure the OAuth consent screen and create an OAuth client of type **Web application**.
2. In **Account & Integrations → Google**, copy the displayed authorized origin and callback exactly. Default values:
   - Authorized origin: `http://127.0.0.1:8501`
   - Authorized redirect URI: `http://127.0.0.1:8501/api/auth/google/callback`
3. Paste the Google OAuth Client ID and Client Secret in the wizard and save. The secret is stored only in the operating system credential manager; it is never returned by the API or written into the ZIP.
4. If you change the origin, set `STUDIO_PUBLIC_ORIGIN` to the exact loopback origin (for example `http://127.0.0.1:8501`) before starting the server, then register the corresponding callback in Google.

The browser is sent to Google's authorization endpoint using authorization code + PKCE, state and nonce. The backend exchanges the code and verifies the Google ID token signature, issuer, audience, expiry, verified email, and nonce. If Google is not configured, its sign-in button is not shown.

Official Google guide: https://developers.google.com/identity/protocols/oauth2/web-server

## GitHub App connection (optional)

1. In GitHub Developer settings, create a GitHub App and enable user authorization. Enable expiring user access tokens/refresh tokens as supported by GitHub.
2. In **Account & Integrations → GitHub App**, use the callback shown in the wizard. Default: `http://127.0.0.1:8501/api/github/callback`.
3. Grant only repository **Metadata: read-only** and **Contents: read-only** permissions needed to list repositories and import code. Do not grant write, issues, pull requests, or administration permissions.
4. Paste the GitHub App Client ID and Client Secret and save. These remain in the OS credential manager. Then click **Connect GitHub**, approve on GitHub, and return to choose a repository, branch, and paths.

OAuth state is stored hashed, bound to a short-lived browser cookie and the current local session, and consumed once. Disconnect revokes/removes the user token but keeps the administrator's App configuration so **Reconnect** does not require re-entering the App secret. Removing the App setup is a separate action. Existing repository indexing, read-only import, incremental synchronization, cancellation, source citations, and local Ollama chat remain intact.

Official GitHub App guide: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app

## SMTP password recovery (optional)

The app has no built-in mail service. Supply an SMTP host/port, STARTTLS or implicit SSL, optional credentials, and a sender email in the wizard. **Test connection and save** must succeed before password reset is advertised. SMTP credentials are stored in the OS credential manager. Reset tokens are single-use, stored hashed, and expire after one hour; reset requests use a generic response to avoid account enumeration.

The app uses the configured loopback origin in reset links. Do not configure an email provider or use password recovery until its SMTP credentials and sender authorization are ready.

## Secrets, backups, and ZIP contents

Google, GitHub App and SMTP secrets plus GitHub user tokens are held in the OS credential manager. Do not copy them into frontend code or source control. The generated Task 4 ZIP intentionally excludes `.env` files, databases, local `files/` and `data/` directories, caches, tokens, and credentials. Existing local SQLite content is preserved by additive schema migrations; the project does not package a user's database.

The application remains bound to `127.0.0.1`. `STUDIO_PUBLIC_ORIGIN` accepts only loopback HTTP/HTTPS origins. A reverse proxy or public deployment requires a separate security review and is not supported by this local setup wizard.
