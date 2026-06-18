# Tessera Node UI

A Vue 3 + TailwindCSS web interface for Tessera nodes with dual-mode support:
- **Regular Node**: Status-oriented dashboard for monitoring
- **Organization Node**: Full management features for organizations

Built to handle **millions of customers and calls** with server-side pagination, virtual scrolling, and real-time counters.

## Features

### Regular Node Mode
- Node health and status monitoring
- WebSocket connection status with client count
- Recent proof verifications with search and filtering
- Commitment management and lookup
- Live stats overview with animated counters

### Organization Node Mode
- Customer management with search and pagination
- Device registration and management per customer
- Commitment tracking with expiry timers
- Quick actions dashboard
- Organization configuration with API key management

### Scalability Features
- **Server-side pagination** - Only loads current page (configurable: 25, 50, 100, 250 per page)
- **Real-time search** - Debounced instant search (300ms) with server-side filtering
- **Live counters** - Animated stats with delta indicators (+5K, -100)
- **Compact numbers** - Displays "1.2M", "450K" for large datasets
- **Virtual scrolling** - Efficiently renders large lists (VirtualList component)
- **Optimized stores** - Only keeps current page in memory

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

By default, it proxies API requests to `http://localhost:8000` (the Tessera service).

### Using the Start Script

```bash
# Start development server
./scripts/start_ui.sh

# Build for production
./scripts/start_ui.sh --build
```

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

Configure the API endpoint in the Settings page:
1. Navigate to Settings
2. Enter your API endpoint URL
3. For organization mode, add Organization ID and API Key
4. Click "Test Connection" to verify
5. Save configuration

The UI uses `/api` as the base URL which is proxied to the Tessera service in development.

### Mode Switching

Switch between Regular and Organization modes:
1. Via the toggle in the header
2. Via the Settings page (with detailed mode descriptions)

Mode selection persists in local storage.

### Theme

Supports three themes:
- **Light** - Clean light interface
- **Dark** - Dark mode for low-light environments
- **System** - Follows OS preference

## Project Structure

```
ui/
├── src/
│   ├── components/
│   │   ├── common/          # Shared UI components
│   │   │   ├── Card.vue           # Base card component
│   │   │   ├── Modal.vue          # Modal dialog
│   │   │   ├── Pagination.vue     # Server-side pagination controls
│   │   │   ├── SearchInput.vue    # Debounced search input
│   │   │   ├── VirtualList.vue    # Virtual scrolling for large lists
│   │   │   ├── LiveCounter.vue    # Animated number counters
│   │   │   ├── StatCard.vue       # Statistics display card
│   │   │   ├── StatusBadge.vue    # Status indicator badges
│   │   │   ├── EmptyState.vue     # Empty state placeholder
│   │   │   ├── Sidebar.vue        # Navigation sidebar
│   │   │   └── Header.vue         # Top header bar
│   │   ├── regular/         # Regular node components
│   │   │   ├── NodeStatus.vue     # Health and connection status
│   │   │   ├── StatsOverview.vue  # Stats cards grid
│   │   │   └── RecentActivity.vue # Recent proofs list
│   │   └── org/             # Organization components
│   │       ├── CustomerList.vue      # Paginated customer list
│   │       ├── DeviceManager.vue     # Device CRUD operations
│   │       └── CommitmentTracker.vue # Commitment monitoring
│   ├── composables/         # Vue composables
│   │   ├── useApi.js        # API request helper
│   │   ├── useWebSocket.js  # WebSocket connection manager
│   │   └── useTime.js       # Time formatting utilities
│   ├── stores/              # Pinia state stores
│   │   ├── app.js           # Mode, theme, config
│   │   ├── node.js          # Health, stats, WebSocket
│   │   ├── customers.js     # Customer management (paginated)
│   │   ├── proofs.js        # Proof verification (paginated)
│   │   └── commitments.js   # Commitment management
│   ├── views/               # Page views
│   │   ├── Dashboard.vue    # Main dashboard (mode-aware)
│   │   ├── Customers.vue    # Customer management (org mode)
│   │   ├── Commitments.vue  # Commitment management
│   │   ├── Proofs.vue       # Proof verification
│   │   └── Settings.vue     # Configuration
│   ├── router/              # Vue Router
│   └── assets/              # CSS and static assets
├── public/                  # Static files (favicon)
└── index.html               # Entry HTML
```

## API Integration

The UI integrates with the Tessera service API with full pagination support:

### Health & Stats
- `GET /health` - Node health status
- `GET /stats` - Service statistics (live polling every 5s)

### Proofs (Paginated)
- `GET /proofs/recent?page=1&limit=50&search=...&status=verified` - List proofs
- `POST /proofs/verify` - Verify a proof
- `POST /proofs/broadcast` - Broadcast a proof

### Commitments
- `POST /commitments/register` - Register commitment
- `GET /commitments/lookup/:id` - Lookup commitment

### Customers (Organization Mode, Paginated)
- `GET /customers?page=1&page_size=50&search=...` - List customers
- `POST /customers/register` - Register customer
- `GET /customers/:id/devices?page=1&page_size=50` - Get customer devices
- `POST /customers/:id/devices` - Register device
- `DELETE /customers/:id/devices/:deviceId` - Remove device
- `GET /customers/:id/commitments?page=1&page_size=50` - Get customer commitments

### Organizations (Organization Mode)
- `GET /organizations/:orgId/customers/:customerId/commitments` - Get commitments (with auth)

## Component Reference

### Pagination
```vue
<Pagination
  :current-page="store.page"
  :page-size="store.pageSize"
  :total="store.total"
  :page-sizes="[25, 50, 100, 250]"
  @update:current-page="store.setPage"
  @update:page-size="store.setPageSize"
/>
```

### SearchInput
```vue
<SearchInput
  v-model="searchQuery"
  placeholder="Search..."
  :loading="isLoading"
  instant
  :debounce="300"
  @search="onSearch"
/>
```

### LiveCounter
```vue
<LiveCounter
  :value="1234567"
  format="compact"      <!-- "1.2M" -->
  show-delta            <!-- Shows +/- changes -->
  class="text-2xl font-bold"
/>
```

### VirtualList
```vue
<VirtualList
  :items="largeArray"
  :item-height="64"
  container-height="400px"
  key-field="id"
  @load-more="loadNextPage"
>
  <template #default="{ item, index }">
    <div>{{ item.name }}</div>
  </template>
</VirtualList>
```

## Performance Considerations

### For Large Datasets (Millions of Records)

1. **Server-side pagination is required** - The UI expects paginated API responses:
   ```json
   {
     "items": [...],
     "total": 1500000,
     "page": 1,
     "page_size": 50
   }
   ```

2. **Search is server-side** - The UI sends search queries to the backend:
   ```
   GET /customers?search=john&page=1&page_size=50
   ```

3. **Stats are separate** - Live counters fetch from `/stats` endpoint independently

4. **Memory efficient** - Only current page data is kept in Pinia stores

### Recommended Backend Configuration

For handling millions of records:
- Database indexes on searchable fields (customer_id, proof_id)
- Efficient COUNT queries or cached totals
- Rate limiting on search endpoints
- Consider Elasticsearch for full-text search at scale

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Development

### Tech Stack
- **Vue 3** - Composition API
- **Pinia** - State management
- **Vue Router** - Client-side routing
- **TailwindCSS** - Utility-first CSS
- **Heroicons** - SVG icons
- **Vite** - Build tool

### Code Style
- Vue Single File Components (.vue)
- Composition API with `<script setup>`
- TailwindCSS for styling (no scoped CSS)
- Pinia stores with setup syntax

### Adding New Features

1. Create component in appropriate directory
2. Add store if needed (with pagination support)
3. Add route if it's a new page
4. Update sidebar navigation if needed
