# NetMon Dashboard

A real-time network monitoring dashboard built with React, TypeScript, and Vite. Displays device status, latency metrics, and anomaly alerts for network infrastructure monitoring.

## Features

- **Real-time Device Monitoring**: View status of all network devices with auto-refresh (10s intervals)
- **Site Status Overview**: Health indicators showing devices up/down, active anomalies, and overall site status
- **Device Details**: Click any device to view detailed metrics including latency, packet loss, and jitter
- **Anomaly Alerts**: Live feed of network anomalies with resolution capabilities
- **JWT Authentication**: Secure login with automatic token refresh
- **Dark/Light Theme**: Toggle between themes with persistent preference
- **Responsive Design**: Works on desktop and tablet displays

## Tech Stack

- **React 19** with TypeScript
- **Vite** for development and build
- **TanStack Query** for server state management
- **Tailwind CSS 4** for styling
- **Recharts** for data visualization
- **Axios** for API communication
- **Lucide React** for icons

## Prerequisites

- Node.js 18+
- A running NetMon API backend

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your settings:
   ```
   VITE_API_URL=http://localhost:3000/api/v1
   VITE_SITE_ID=home
   ```

## Development

Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`. The dev server proxies API requests to avoid CORS issues.

## Building for Production

```bash
npm run build
```

Output will be in the `dist/` directory.

## Preview Production Build

```bash
npm run preview
```

## Project Structure

```
src/
├── api/           # API client and endpoint functions
│   ├── client.ts  # Axios instance with auth interceptors
│   ├── auth.ts    # Authentication endpoints
│   ├── sites.ts   # Site endpoints
│   ├── anomalies.ts
│   └── measurements.ts
├── components/
│   └── dashboard/ # Dashboard UI components
│       ├── Dashboard.tsx
│       ├── StatusOverview.tsx
│       ├── DeviceTable.tsx
│       ├── DeviceDetailPanel.tsx
│       ├── AnomaliesPanel.tsx
│       ├── LoginForm.tsx
│       └── ThemeToggle.tsx
├── hooks/         # React Query hooks
│   ├── useAnomalies.ts
│   ├── useMeasurements.ts
│   ├── useSites.ts
│   ├── useSiteStatus.ts
│   └── useTheme.tsx
├── lib/
│   └── utils.ts   # Utility functions (cn for classnames)
├── types/
│   └── api.ts     # TypeScript type definitions
├── App.tsx        # Root component
├── main.tsx       # Entry point
└── index.css      # Global styles and CSS variables
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `/api/v1` (uses proxy in dev) |
| `VITE_SITE_ID` | Site identifier to monitor | `home` |
| `VITE_SITE_NAME` | Alternative to SITE_ID | - |

## API Endpoints Used

- `POST /auth/token` - Login
- `POST /auth/refresh` - Refresh tokens
- `GET /sites` - List sites
- `GET /sites/:id/status` - Site status with device list
- `GET /anomalies` - List anomalies
- `PATCH /anomalies/:id/resolve` - Resolve an anomaly
- `GET /measurements` - Historical measurements
