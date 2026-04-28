# Frontend (React + Vite)

Frontend control panel for the Face Attendance project.

## Run Locally

1. Install dependencies.
2. Configure environment.
3. Start Vite dev server.

```bash
npm install
npm run dev
```

Set environment variable in `.env`:

```bash
VITE_API_BASE=http://localhost:8000
```

## Main UI Sections

- Home
	- Add Student
	- Train Model
	- Mark Attendance
- Monthly Lookup
- Admin

## Feature Notes

### Add Student
- Captures up to 50 frames from camera.
- Backend filters valid/unique face frames before storing selected images.

### Train Model
- Uses backend `/training/start` and `/training/status`.
- Current training payload is aligned to backend constraints (`epochs=25`, `batch_size=8`).

### Mark Attendance
- Captures webcam frame every interval and calls `/attendance/recognize`.
- Uses cooldown-aware error toasts to avoid spam during repeated failures.

### Monthly Lookup
- Uses backend `/attendance/monthly-summary`.
- `month` parameter is interpreted as months count from current month backward.
- Example in April: `month=4` means April + March + February + January.

### Admin
- Refresh training status.
- Start training.
- Delete student by id or roll number.
- Reset semester.

## API Dependency

This frontend expects backend to be running at `VITE_API_BASE` with these endpoints available:
- `/students`
- `/training/start`
- `/training/status`
- `/attendance/recognize`
- `/attendance/monthly-summary`
- `/attendance/class-day`
- `/admin/reset-semester`
- `/admin/rebuild-embeddings`
