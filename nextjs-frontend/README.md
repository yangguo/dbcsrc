# CSRC Case Analysis System - Next.js Frontend

A modern Next.js frontend for the CSRC (China Securities Regulatory Commission) case analysis system, converted from the original Streamlit application.

## Features

- **案例总数 (Case Summary)**: View case statistics and charts
- **案例搜索2 (Case Search)**: Search and filter cases with advanced options
- **案例更新2 (Case Update)**: Update case data from various organizations
- **附件处理2 (Attachment Processing)**: Analyze, download, and convert attachments
- **案例分类2 (Case Classification)**: Classify cases using AI/ML models
- **案例下载2 (Case Download)**: Manage case downloads and exports
- **案例上线2 (Case Upload)**: Deploy cases to production environments

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **UI Library**: Ant Design
- **Styling**: Tailwind CSS
- **Charts**: Apache ECharts
- **HTTP Client**: Axios
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)

## Prerequisites

- Node.js 18+ 
- npm or yarn
- Backend API running on `http://localhost:8000`

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd nextjs-frontend
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

3. Create environment variables (optional):
```bash
cp .env.example .env.local
```

Edit `.env.local` if you need to customize the API base URL:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Development

Start the development server:
```bash
npm run dev
# or
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Build

Build for production:
```bash
npm run build
# or
yarn build
```

Start production server:
```bash
npm start
# or
yarn start
```

## Project Structure

```
nextjs-frontend/
├── src/
│   ├── app/                 # Next.js App Router
│   │   ├── globals.css      # Global styles
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Main dashboard
│   ├── components/          # React components
│   │   ├── AttachmentProcessing.tsx
│   │   ├── CaseClassification.tsx
│   │   ├── CaseDownload.tsx
│   │   ├── CaseSearch.tsx
│   │   ├── CaseSummary.tsx
│   │   ├── CaseUpdate.tsx
│   │   └── CaseUpload.tsx
│   └── services/            # API services
│       └── api.ts           # API client and interfaces
├── public/                  # Static assets
├── next.config.js          # Next.js configuration
├── tailwind.config.js      # Tailwind CSS configuration
├── tsconfig.json           # TypeScript configuration
└── package.json            # Dependencies and scripts
```

## API Integration

The frontend communicates with the backend API through the following endpoints:

- `GET /api/summary` - Get case statistics
- `POST /api/search` - Search cases
- `POST /api/update` - Update case data
- `POST /api/attachments/analyze` - Analyze attachments
- `POST /api/attachments/download` - Download attachments
- `POST /api/convert` - Convert documents
- `POST /api/extract` - Extract text
- `POST /api/classify` - Classify cases
- `POST /api/batch-classify` - Batch classify cases
- `GET /api/downloads` - Get download status
- `POST /api/upload` - Upload cases

## Configuration

### API Base URL

The API base URL is configured in `next.config.js` with a rewrite rule:

```javascript
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
};
```

### Ant Design Theme

Custom theme configuration is in `src/app/layout.tsx`:

```typescript
const theme = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
  },
};
```

## Features Overview

### Dashboard
- Sidebar navigation with all major functions
- Responsive design for mobile and desktop
- Chinese language support

### Case Summary
- Total case count and statistics
- Interactive charts showing case distribution
- Monthly trend analysis

### Case Search
- Advanced search with multiple filters
- Pagination and sorting
- Case detail modal
- Export functionality

### Case Update
- Organization-based data updates
- Progress tracking
- Batch processing
- Error handling and retry

### Attachment Processing
- File analysis and statistics
- Bulk download capabilities
- Format conversion (Word, OFD)
- Text extraction

### Case Classification
- AI-powered case classification
- Custom label management
- Batch processing
- CSV import/export

### Case Download
- Download queue management
- Progress tracking
- Retry failed downloads
- File format options

### Case Upload
- Production deployment
- Environment configuration
- Batch upload with progress
- Validation and verification

## Styling

### Tailwind CSS
Utility-first CSS framework for rapid UI development.

### Ant Design
Enterprise-class UI design language with React components.

### Custom Styles
Global styles in `src/app/globals.css` include:
- Chinese font support (Noto Sans SC)
- Custom Ant Design overrides
- Responsive utilities

## Development Guidelines

### Code Style
- Use TypeScript for type safety
- Follow React best practices
- Use functional components with hooks
- Implement proper error handling

### Component Structure
- Keep components focused and reusable
- Use proper TypeScript interfaces
- Implement loading and error states
- Follow Ant Design patterns

### API Integration
- Use the centralized API service
- Implement proper error handling
- Use React Query for data fetching
- Handle loading states consistently

## Deployment

### Vercel (Recommended)
```bash
npm install -g vercel
vercel
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Environment Variables
Set the following environment variables in production:
- `NEXT_PUBLIC_API_BASE_URL`: Backend API URL
- `NODE_ENV`: Set to `production`

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Ensure backend is running on `http://localhost:8000`
   - Check CORS configuration
   - Verify API endpoints

2. **Build Errors**
   - Clear `.next` folder: `rm -rf .next`
   - Reinstall dependencies: `rm -rf node_modules && npm install`
   - Check TypeScript errors: `npm run type-check`

3. **Styling Issues**
   - Ensure Tailwind CSS is properly configured
   - Check Ant Design theme conflicts
   - Verify CSS import order

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.