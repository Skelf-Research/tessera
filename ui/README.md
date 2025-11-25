# CallDNS Node UI

A Vue 3 + TailwindCSS web interface for CallDNS nodes with dual-mode support:
- **Regular Node**: Status-oriented dashboard for monitoring
- **Organization Node**: Full management features for organizations

## Features

### Regular Node Mode
- Node health and status monitoring
- WebSocket connection status
- Recent proof verifications
- Commitment management
- Stats overview

### Organization Node Mode
- Customer management
- Device registration and management
- Commitment tracking per customer
- Quick actions dashboard
- Organization configuration

## Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

```bash
cd ui
npm install
```

### Development

```bash
npm run dev
```

The UI will be available at `http://localhost:3000`.

By default, it proxies API requests to `http://localhost:8000` (the CallDNS service).

### Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Configuration

### API Endpoint

Configure the API endpoint in the Settings page or via environment:

The UI uses `/api` as the base URL which is proxied to the CallDNS service in development.

### Mode Switching

Switch between Regular and Organization modes:
1. Via the toggle in the header
2. Via the Settings page

Mode selection persists in local storage.

## Project Structure

```
ui/
├── src/
│   ├── components/
│   │   ├── common/      # Shared components (Card, Modal, StatusBadge, etc.)
│   │   ├── regular/     # Regular node components (NodeStatus, StatsOverview)
│   │   └── org/         # Organization components (CustomerList, DeviceManager)
│   ├── composables/     # Vue composables (useApi, useWebSocket, useTime)
│   ├── stores/          # Pinia stores (app, node, customers, proofs, commitments)
│   ├── views/           # Page views (Dashboard, Customers, Settings, etc.)
│   ├── router/          # Vue Router configuration
│   └── assets/          # CSS and static assets
├── public/              # Static files
└── index.html           # Entry HTML
```

## API Integration

The UI integrates with the CallDNS service API:

- `GET /health` - Node health status
- `GET /stats` - Service statistics
- `POST /proofs/verify` - Verify a proof
- `POST /proofs/broadcast` - Broadcast a proof
- `POST /commitments/register` - Register commitment
- `GET /commitments/lookup/:id` - Lookup commitment
- `POST /customers/register` - Register customer (org mode)
- `GET /customers/:id/devices` - Get customer devices
- `POST /customers/:id/devices` - Register device
- `DELETE /customers/:id/devices/:deviceId` - Remove device
- `GET /customers/:id/commitments` - Get customer commitments

## Theming

Supports light, dark, and system themes. Toggle via:
- Header theme button
- Settings page

Theme preference persists in local storage.
