# Render deployment and GitHub collaboration

This repository contains the complete application. `render.yaml` proposes one
paid 2 CPU / 4 GB service in Singapore with a 10 GB persistent disk. Confirm the
current quote in Render before creating it. This is an initial demo configuration,
not a measured camera-capacity guarantee. Begin with one stream and monitor memory
and frame throughput. The local RTX 3050 remains the faster analytics environment;
this configuration does not connect Render to your laptop GPU.

## First deployment

1. In Render, choose **New > Blueprint** and connect this GitHub repository.
2. Review `render.yaml`, the service and disk charges; approve only within your budget.
3. Render builds the React frontend, Python backend, CPU PyTorch and model weights.
   The first build downloads the pinned plate model and vehicle/OCR baselines.
4. In the service's Environment page, retrieve the generated `CCTV_ADMIN_PASSWORD`
   and `CCTV_VIEWER_PASSWORD`. Sign in with username `admin` or `viewer` respectively.
   Share the viewer password privately with reviewers. Do not commit credentials.
5. Add `SENTINEL_EMAIL` and `SENTINEL_PASSWORD` privately in Render if using authorized
   organizer feeds. The public repo intentionally contains no working credentials.
6. Open `https://<your-service>.onrender.com/dashboard/`, sign in, then import the
   authorized catalogue from Registry. Camera sources and local records are not
   copied to the public repository or silently transferred to hosting.
7. Connect one permitted source. Verify the video, AI readiness, actual detections,
   plate evidence, and watchlist alerts before giving evaluators the URL.

Render supplies its hostname and port. The launcher allows that hostname, permits
its HTTPS origin and sets Secure/HttpOnly session cookies without blindly trusting
forwarded headers. For a custom domain, set `SENTINEL_ALLOWED_HOSTS` to the custom
and Render hostnames plus `localhost,127.0.0.1`, and add the custom HTTPS origin to
`CORS_ORIGINS`. Sessions expire after eight hours and restart clears login sessions.
The reverse proxy currently shares a login failure bucket; ten failed attempts can
pause all logins for five minutes. Use correct credentials during evaluator demos.

## Data, recordings and updates

The disk mounts at `/var/lib/sentinel`; SQLite, evidence and uploaded media stay
there across deployments. Models are built into the image. Recorded files must be
transferred privately to `/var/lib/sentinel/media` using Render's documented SSH/SCP
access; onboard a relative filename. Do not publish government footage in GitHub.
Local file paths from your Windows computer will not work on Render.

Add your friend in GitHub **Settings > Collaborators**. Use feature branches and
pull requests. Merge only passing changes into `main`; Render's `checksPass`
automatic deployment runs after CI succeeds. A disk-backed service briefly stops
while updating, and camera connections resume only for previously connected
network sources. One process/instance is required for SQLite and camera ownership.

Before schema or data changes, back up SQLite with Python's `sqlite3.Connection.backup`
and copy its evidence directory while ingestion is stopped. Keep backups private.
Revert a Git commit and redeploy to roll back code. A code rollback does not undo
database changes; restore a compatible application backup if a migration requires it.

## Verification and submission limits

CI runs backend regressions, builds the frontend and builds/smoke-tests the CPU
container. The first GitHub Linux container build/startup passed on 12 September 2026.
The local Docker daemon is unavailable; container testing runs in GitHub Actions.
A real Render deployment still needs a live smoke test and stream benchmark.

The small public CarPark diagnostic rerun produced two correct confirmed plates,
zero false confirmed plates and two missed appearances (50% recall); it was not a
held-out accuracy benchmark. Government plate accuracy and multi-camera target
identification remain unproven. Hosting does not resolve those evaluation gaps.
Saved organizer requirements list the hosted platform/login as an optional extra;
the own-source video, government-feed video/report, presentation and HLD remain
required. Consult `SUBMISSION_READINESS.md` before submission.

## Alternative: your own GPU server

Copy `deploy/.env.example` to `deploy/.env`, set a real DNS domain and distinct
passwords, and run `docker compose --env-file deploy/.env -f compose.yaml -f
compose.gpu.yaml up -d --build` with Docker and the NVIDIA Container Toolkit.
Use one line for that command. CPU hosting can omit the GPU override. Caddy handles
HTTPS; only its ports are published. Never put the local `.env` file in Git.

Official references: [Blueprint fields](https://render.com/docs/blueprint-spec),
[persistent disk and deployment behavior](https://render.com/docs/disks),
[pricing](https://render.com/pricing).
