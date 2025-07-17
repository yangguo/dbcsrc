# Frontend Development Standards

## Next.js Project Structure
- Use App Router (Next.js 14+) for all new development
- Organize components in `src/components/` directory
- Keep API services in `src/services/` directory
- Use TypeScript for all components and services
- Follow Next.js file-based routing conventions

## Component Development
- Use functional components with React hooks
- Implement proper TypeScript interfaces for all props
- Follow Ant Design component patterns and guidelines
- Use Tailwind CSS for custom styling
- Implement proper loading and error states

## State Management
- Use Zustand for global state management
- Implement TanStack Query (React Query) for server state
- Keep component state local when possible
- Use proper TypeScript types for all state

## API Integration
- Centralize API calls in `src/services/api.ts`
- Use axios for HTTP requests with proper error handling
- Implement request/response interceptors for common logic
- Handle loading states and error boundaries
- Use proper TypeScript interfaces for API responses

## UI/UX Standards
- Follow Ant Design design system principles
- Implement responsive design for mobile and desktop
- Use proper Chinese language support (Noto Sans SC font)
- Include proper accessibility attributes
- Implement consistent error messaging and validation

## Performance Optimization
- Use Next.js Image component for optimized images
- Implement proper code splitting and lazy loading
- Use React.memo for expensive components
- Optimize bundle size with proper imports
- Implement proper caching strategies

## Development Workflow
- Use ESLint and Prettier for code formatting
- Implement proper TypeScript strict mode
- Use proper Git commit conventions
- Include comprehensive error handling
- Test components with proper mock data

## Deployment Standards
- Configure proper environment variables
- Use Next.js rewrites for API proxy in development
- Implement proper build optimization
- Include proper Docker configuration
- Set up proper CORS and security headers