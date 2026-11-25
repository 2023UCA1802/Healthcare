# Healthcare Frontend (React + Vite)

```bash
npm install
cp .env.example .env     # defaults work with the backend on http://127.0.0.1:8000
npm run dev              # http://localhost:5173
```

Start the Django backend first (see its README).

## How it talks to the backend

- The browser only talks to `http://localhost:5173/api/...`; the **Vite dev proxy** forwards that to Django
  (`VITE_PROXY_TARGET`). Same-origin is what lets the HttpOnly `SameSite=Strict` refresh cookie work, so no CORS is involved in dev.
- **Access token:** kept in memory only (never `localStorage`). Reloading the page restores the session silently via the refresh cookie.
- **Refresh token:** an HttpOnly cookie set by the server; JavaScript can't read it. It rotates on every use, so concurrent refreshes share one request (`refreshSession` in `src/api.js`).
- **Log out** calls `/api/auth/logout/`, which revokes the refresh token server-side.
- **Register** doesn't auto-log-in: the server gives the same answer whether or not the email exists, so you log in afterwards.
- Lists are paginated (`Pager` component); dropdowns use `api.getAll()` to fetch every page.

## Production
Serve the built app (`npm run build`) and the API under the **same site** (e.g. one domain with a reverse proxy sending `/api` to Django), set `VITE_API_URL=/api`, and add your site's URL to the backend's `CORS_ALLOWED_ORIGINS`.
