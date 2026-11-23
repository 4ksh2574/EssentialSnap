# EssentialSnap

Minimal frontend for an optional self-hosted backend. This frontend is published with GitHub Pages.

## Pages deployment
Settings → Pages → Source: GitHub Actions.

## Backend configuration
The UI expects a backend URL stored in localStorage under `essentialsnap_backend`. In the browser console on the deployed site, set:
```js
localStorage.setItem('essentialsnap_backend','https://YOUR-BACKEND'); location.reload();
```

The API expected is POST `/api/info` with JSON `{url}` returning `{title,platform,duration,formats:[{id,label}]}`, and POST `/api/download` with JSON `{url,format_id}` returning a media file. Download only content you own or have permission to save; no private-account or DRM circumvention.