# Tessera Node Management UI

The Tessera Node UI is a Vue 3 + TailwindCSS web application designed for managing Tessera nodes. It supports two operational modes and is built to handle millions of records efficiently.

## Overview

The UI serves two primary use cases:

1. **Regular Node Operators** - Monitor node health, view proof verifications, and manage commitments
2. **Organization Node Operators** - Full customer and device management capabilities

## Architecture

### Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | Vue 3 | Reactive UI with Composition API |
| State | Pinia | Centralized state management |
| Routing | Vue Router | Client-side navigation |
| Styling | TailwindCSS | Utility-first CSS framework |
| Icons | Heroicons | SVG icon library |
| Build | Vite | Fast development and production builds |

### Directory Structure

```
ui/
├── src/
│   ├── components/
│   │   ├── common/          # Reusable UI components
│   │   ├── regular/         # Regular node specific
│   │   └── org/             # Organization node specific
│   ├── composables/         # Shared logic (useApi, useWebSocket, useTime)
│   ├── stores/              # Pinia state stores
│   ├── views/               # Page components
│   ├── router/              # Route definitions
│   └── assets/              # CSS and static files
├── public/                  # Static assets
└── index.html               # Entry point
```

## Getting Started

### Prerequisites

- Node.js 18 or higher
- npm or yarn
- Running Tessera backend service

### Installation

```bash
cd ui
npm install
```

### Development Server

```bash
npm run dev
```

Access the UI at `http://localhost:3000`. API requests are proxied to `http://localhost:8000`.

### Production Build

```bash
npm run build
npm run preview  # Preview the build
```

### Using the Start Script

```bash
# Development
./scripts/start_ui.sh

# Production build
./scripts/start_ui.sh --build
```

## Modes

### Regular Node Mode

Focused on monitoring and basic operations:

- **Dashboard**: Node health, WebSocket status, recent activity
- **Proofs**: View and verify proofs with search/filter
- **Commitments**: Register and lookup commitments
- **Settings**: Configure API endpoint and theme

### Organization Node Mode

Full management capabilities:

- **Dashboard**: Extended with quick actions and org info
- **Customers**: Full CRUD with search and pagination
- **Devices**: Per-customer device management
- **Commitments**: Per-customer commitment tracking
- **Settings**: Organization ID and API key configuration

Switch modes via the header toggle or Settings page.

## Scalability Design

The UI is designed to handle millions of records efficiently:

### Server-Side Pagination

All list views use server-side pagination:

```javascript
// Store example
async function fetchCustomers(options = {}) {
  const params = new URLSearchParams({
    page: options.page || page.value,
    page_size: options.pageSize || pageSize.value,
    ...(searchQuery.value && { search: searchQuery.value })
  })

  const response = await fetch(`${apiUrl}/customers?${params}`)
  const data = await response.json()

  customers.value = data.items       // Current page only
  total.value = data.total           // For pagination display
}
```

Expected API response format:
```json
{
  "items": [...],
  "total": 1500000,
  "page": 1,
  "page_size": 50
}
```

### Debounced Search

Search inputs use debouncing to prevent excessive API calls:

```vue
<SearchInput
  v-model="query"
  instant
  :debounce="300"
  @search="onSearch"
/>
```

### Live Counters

Statistics use polling with compact number formatting:

```vue
<LiveCounter
  :value="1234567"
  format="compact"    <!-- Displays "1.2M" -->
  show-delta          <!-- Shows changes: +5K -->
/>
```

### Virtual Scrolling

For very large in-memory lists, use the VirtualList component:

```vue
<VirtualList
  :items="largeArray"
  :item-height="64"
  container-height="400px"
  @load-more="loadNextPage"
>
  <template #default="{ item }">
    <CustomerRow :customer="item" />
  </template>
</VirtualList>
```

## Components

### Common Components

| Component | Description |
|-----------|-------------|
| `Card` | Base card container with optional header/actions |
| `Modal` | Dialog overlay with header, body, footer slots |
| `Pagination` | Full pagination controls with page size selector |
| `SearchInput` | Debounced search with loading state |
| `VirtualList` | Virtualized list for large datasets |
| `LiveCounter` | Animated counter with compact formatting |
| `StatCard` | Statistics display card with icon |
| `StatusBadge` | Colored status indicators |
| `EmptyState` | Placeholder for empty lists |
| `Sidebar` | Navigation sidebar (collapsible) |
| `Header` | Top bar with mode toggle and controls |

### Regular Node Components

| Component | Description |
|-----------|-------------|
| `NodeStatus` | Health status and connection info |
| `StatsOverview` | Grid of stat cards |
| `RecentActivity` | Recent proof verifications |

### Organization Components

| Component | Description |
|-----------|-------------|
| `CustomerList` | Paginated customer list with search |
| `DeviceManager` | Device CRUD for selected customer |
| `CommitmentTracker` | Commitment list with expiry status |

## State Management

### Stores

| Store | Purpose | Key State |
|-------|---------|-----------|
| `app` | Global config | mode, theme, apiUrl, orgId, apiKey |
| `node` | Node status | health, stats, wsConnected |
| `customers` | Customer data | customers[], page, total, selected |
| `proofs` | Proof data | proofs[], page, total, liveStats |
| `commitments` | Commitments | commitments[], lookupCache |

### Pagination Pattern

All paginated stores follow this pattern:

```javascript
export const useCustomersStore = defineStore('customers', () => {
  // Data
  const customers = ref([])      // Current page only
  const loading = ref(false)

  // Pagination state
  const page = ref(1)
  const pageSize = ref(50)
  const total = ref(0)
  const searchQuery = ref('')

  // Actions
  async function fetchCustomers(options = {}) { ... }
  async function searchCustomers(query) { ... }
  async function setPage(newPage) { ... }
  async function setPageSize(newSize) { ... }

  return { customers, loading, page, pageSize, total, ... }
})
```

## API Integration

### Authentication

Organization mode requires authentication:

```javascript
function getHeaders() {
  const headers = { 'Content-Type': 'application/json' }
  if (appStore.apiKey) {
    headers['Authorization'] = `Bearer ${appStore.apiKey}`
  }
  return headers
}
```

### Endpoints Used

#### Public Endpoints
- `GET /health` - Node health check
- `GET /stats` - Service statistics
- `POST /proofs/verify` - Verify a proof
- `POST /proofs/broadcast` - Broadcast a proof
- `GET /proofs/recent` - List recent proofs (paginated)
- `POST /commitments/register` - Register commitment
- `GET /commitments/lookup/:id` - Lookup commitment

#### Organization Endpoints (Authenticated)
- `GET /customers` - List customers (paginated)
- `POST /customers/register` - Register customer
- `GET /customers/:id/devices` - Get devices (paginated)
- `POST /customers/:id/devices` - Register device
- `DELETE /customers/:id/devices/:deviceId` - Remove device
- `GET /customers/:id/commitments` - Get commitments (paginated)

### WebSocket

Real-time updates via WebSocket:

```javascript
const { connect, on, send } = useWebSocket('subscriber-id')

on('proof_received', (data) => {
  // Handle new proof
})

connect()
```

## Theming

### Theme Options

- **Light**: Default light theme
- **Dark**: Dark mode with adjusted colors
- **System**: Follows OS preference

### Customization

Colors are defined in `tailwind.config.js`:

```javascript
colors: {
  primary: { 50: '...', 500: '...', 600: '...' },
  success: { ... },
  warning: { ... },
  danger: { ... }
}
```

### CSS Classes

Common utility classes in `src/assets/main.css`:

```css
.btn { @apply inline-flex items-center ... }
.btn-primary { @apply bg-primary-600 ... }
.btn-secondary { @apply bg-gray-200 ... }
.card { @apply bg-white dark:bg-gray-800 ... }
.input { @apply w-full px-3 py-2 ... }
```

## Performance Tuning

### Backend Requirements

For handling millions of records:

1. **Database Indexes**
   - Index `customer_id`, `proof_id`, `created_at`
   - Consider composite indexes for common queries

2. **Efficient Counting**
   - Cache total counts or use approximate counts
   - Avoid `COUNT(*)` on large tables

3. **Search Optimization**
   - Use database full-text search or Elasticsearch
   - Implement search result caching

4. **Rate Limiting**
   - Limit search queries per client
   - Implement request throttling

### Frontend Optimizations

1. **Route-based Code Splitting**
   - Each view is lazy-loaded
   - Reduces initial bundle size

2. **Component Chunking**
   - Large components are split into separate chunks
   - Vite handles automatic chunking

3. **Memory Management**
   - Only current page data in stores
   - Clear selections when navigating away

## Deployment

### Static Hosting

Build and serve the `dist` directory:

```bash
npm run build
# Serve dist/ with nginx, Apache, or CDN
```

### Docker

```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### Environment Configuration

Configure API endpoint via Settings page or pre-configure in localStorage:

```javascript
localStorage.setItem('tessera-api-url', 'https://api.example.com')
localStorage.setItem('tessera-mode', 'organization')
```

## Troubleshooting

### Common Issues

**API Connection Failed**
- Check if backend is running on configured port
- Verify CORS is enabled on backend
- Check browser console for errors

**WebSocket Not Connecting**
- Ensure WebSocket endpoint is accessible
- Check for proxy/firewall blocking WebSocket

**Slow Performance**
- Enable server-side pagination on backend
- Check network latency
- Reduce page size in Settings

**Theme Not Applying**
- Clear localStorage and refresh
- Check for CSS conflicts

### Debug Mode

Enable logging in Settings or via console:

```javascript
localStorage.setItem('tessera-debug', 'true')
```

## Contributing

### Development Workflow

1. Create feature branch
2. Make changes following code style
3. Test with mock data and real backend
4. Submit PR with description

### Code Style

- Vue Composition API with `<script setup>`
- TailwindCSS for all styling
- Pinia stores with setup syntax
- TypeScript-like JSDoc comments for complex logic
