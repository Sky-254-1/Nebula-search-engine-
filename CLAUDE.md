# Nebula Search Engine - Design System Rules

## Project Overview

Nebula Search Engine is a modern search engine with a Python FastAPI backend and React + Vite frontend. The project emphasizes a clean, modern UI with dark/light theme support and accessibility.

---

## MCP Servers

### Figma MCP Server Rules

These rules define how to translate Figma designs into code for the Nebula Search Engine project.

## Component Organization

- **Frontend components are located in**: `frontend/src/components/`
- **Page components are located in**: `frontend/src/pages/`
- **Hooks are located in**: `frontend/src/hooks/`
- **API clients are in**: `frontend/src/api/`
- **Shared utilities are in**: `frontend/src/utils/`
- **Component naming**: Use PascalCase for component files (e.g., `SearchBar.jsx`, `AuthModal.jsx`)
- **Hook naming**: Use camelCase with `use` prefix (e.g., `useSearch.js`, `useAI.js`)
- **Components are exported as named exports**: `export function ComponentName() {}`

## Figma Implementation Flow

**IMPORTANT: Follow this exact sequence for every Figma design implementation:**

1. **Run `get_design_context`** first to fetch the structured representation for the exact node(s)
2. **If the response is too large or truncated**, run `get_metadata` to get the high-level node map, then re-fetch only the required node(s) with `get_design_context`
3. **Run `get_screenshot`** for a visual reference of the node variant being implemented
4. **Only after you have both `get_design_context` and `get_screenshot`**, download any assets needed and start implementation
5. **Translate the output** (usually React + Tailwind) into this project's conventions, styles, and framework
6. **Validate against Figma** for 1:1 look and behavior before marking complete

## Styling Rules

### CSS Architecture

- **IMPORTANT: Use CSS custom properties (CSS variables) for all theme-able values**
- **All global styles are in**: `frontend/src/styles/app.css`
- **NO CSS Modules or styled-components** - use plain CSS with semantic class names
- **NO Tailwind CSS** - use the project's custom CSS architecture
- **Styling approach**: Use semantic CSS classes defined in `app.css`

### Design Tokens

**IMPORTANT: Never hardcode colors, spacing, or typography - always use CSS variables defined in `:root`**

#### Color Tokens (defined in `frontend/src/styles/app.css`)

```css
:root {
  --bg: #0b0c10;               /* Background color (dark) */
  --surface: #1f2229;          /* Surface/card background */
  --text: #e0e0e0;             /* Primary text color */
  --text-dim: rgba(224, 224, 224, 0.6); /* Secondary/muted text */
  --accent: #7c5cfc;           /* Primary accent color (purple) */
  --accent-glow: #a78bfa;      /* Lighter accent for gradients */
  --border: rgba(255, 255, 255, 0.08); /* Border color */
  --radius: 16px;              /* Standard border radius */
}

body[data-theme='light'] {
  --bg: #f8f9fa;
  --surface: #ffffff;
  --text: #202124;
  --text-dim: rgba(32, 33, 36, 0.6);
  --accent: #5e4ae3;
  --border: rgba(0, 0, 0, 0.1);
}
```

**Usage:**
- Background colors: Use `var(--bg)` for page backgrounds, `var(--surface)` for cards/panels
- Text colors: Use `var(--text)` for primary text, `var(--text-dim)` for secondary/muted text
- Accent colors: Use `var(--accent)` for primary actions, `var(--accent-glow)` for hover states and gradients
- Borders: Always use `var(--border)` for consistent borders across themes

#### Spacing Guidelines

- Use `rem` units for spacing (1rem = 16px)
- Common spacing values: `0.5rem` (8px), `0.75rem` (12px), `1rem` (16px), `1.5rem` (24px), `2rem` (32px)
- Padding for cards/panels: `1rem 1.2rem` (16px vertical, 19.2px horizontal)
- Gap between elements: Use `0.5rem`, `1rem`, or `1.5rem` depending on visual hierarchy

#### Typography Tokens

- **Font family**: `Inter, system-ui, sans-serif` (system font stack with Inter as primary)
- **Font sizes**: Use `clamp()` for responsive typography (e.g., `clamp(2.5rem, 8vw, 4rem)`)
- **Font weights**: 
  - Normal text: `400` (default)
  - Medium: `500` (used for links)
  - Bold: `700` (used for headings and logo)
- **Line heights**: Keep default or adjust per component needs

#### Border Radius

- **Standard radius**: `var(--radius)` (16px) for cards, modals, panels
- **Pill/rounded buttons**: `border-radius: 999px` for pill-shaped elements (buttons, search bar)
- **Small radius**: `8px` or `12px` for input fields, selects, toasts

## Component Patterns

### Component Structure

All React components should follow this pattern:

```jsx
export function ComponentName({ prop1, prop2, onEvent }) {
  // Component logic here
  
  return (
    <div className="component-name">
      {/* JSX here */}
    </div>
  );
}
```

### Props Conventions

- **IMPORTANT: Use destructured props in function signature**
- **Event handlers**: Use `onEventName` convention (e.g., `onChange`, `onSubmit`, `onClick`)
- **Boolean props**: Use positive naming (e.g., `loading`, `disabled`, `visible`)
- **Pass data down, callbacks up**: Components receive data via props, send events via callbacks
- **Accessibility**: Always include `aria-label` for interactive elements without visible text

### Common Component Classes

**Buttons:**
```css
.btn                    /* Base button style */
.btn.primary           /* Primary action button (accent background) */
.btn.ghost             /* Transparent background button */
```

**Cards and Panels:**
```css
.result-card           /* Search result card */
.modal                 /* Modal dialog */
.ai-box                /* AI response container */
.error-box             /* Error message container */
.empty-state           /* Empty state placeholder */
```

**Layout:**
```css
.page                  /* Page wrapper (min-height: 100vh) */
.header                /* Header container */
.hero                  /* Hero section */
.results-grid          /* Grid layout for results */
```

**Form Elements:**
```css
.search-bar            /* Search bar container */
.modal input           /* Modal form inputs */
.backend-select select /* Select dropdown styling */
```

### State Management

- **Context API**: Use React Context for global state (auth, search)
- **Providers**: Wrap app in `<AuthProvider>`, `<SearchProvider>` as needed
- **Local state**: Use `useState` for component-specific state
- **Side effects**: Use `useEffect` for data fetching, subscriptions

## Asset Handling

### Images and Icons

- **IMPORTANT: If the Figma MCP server returns a localhost source for an image or SVG, use that source directly**
- **DO NOT import/add new icon packages** - all assets should come from the Figma design
- **DO NOT use or create placeholders** if a localhost source is provided
- **Emoji icons**: The project currently uses emoji for simple icons (e.g., `🔍` for search)
- **SVG assets**: Store downloaded SVGs in `frontend/public/` directory
- **Image optimization**: Use appropriate formats (WebP for photos, SVG for icons)

### Static Assets

- Public assets go in: `frontend/public/`
- Reference public assets with absolute paths: `/assets/image.png`

## Figma to Code Translation Rules

### When Translating Figma Designs:

1. **Replace Tailwind classes** with semantic CSS classes from `app.css`
2. **Map Figma colors** to CSS variables:
   - Background → `var(--bg)` or `var(--surface)`
   - Text → `var(--text)` or `var(--text-dim)`
   - Accent/brand colors → `var(--accent)` or `var(--accent-glow)`
   - Borders → `var(--border)`

3. **Map Figma spacing** to rem units:
   - 4px → `0.25rem`
   - 8px → `0.5rem`
   - 12px → `0.75rem`
   - 16px → `1rem`
   - 24px → `1.5rem`

4. **Handle responsive design**:
   - Use `clamp()` for fluid typography
   - Use `min()` for max-width constraints (e.g., `min(420px, 92vw)`)
   - Use CSS Grid and Flexbox for layouts
   - Consider mobile-first approach

5. **Preserve visual fidelity**:
   - Match exact spacing, sizing, and colors from Figma
   - Maintain hover states and transitions
   - Ensure consistent border radius usage

## Accessibility Standards

**IMPORTANT: All components must meet basic accessibility requirements:**

- All interactive elements must have visible focus states
- Forms must have proper labels and aria-labels
- Images must have alt text (or `aria-hidden="true"` for decorative images)
- Buttons must have descriptive text or aria-labels
- Color contrast must meet WCAG AA standards (already ensured by CSS variables)
- Use semantic HTML elements (`<button>`, `<nav>`, `<main>`, etc.)
- Include `aria-busy` for loading states
- Include `aria-disabled` for disabled interactive elements

## Code Quality Standards

### JavaScript/React Best Practices

- **Use ES6+ syntax**: Arrow functions, destructuring, template literals
- **Prefer functional components**: No class components
- **Use hooks appropriately**: `useState`, `useEffect`, `useContext`, custom hooks
- **Keep components focused**: Single responsibility principle
- **Extract reusable logic**: Create custom hooks for shared behavior
- **Handle errors gracefully**: Use error boundaries and try/catch blocks
- **Avoid inline styles**: Use CSS classes from `app.css`

### Import Organization

```jsx
// 1. React and third-party imports
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

// 2. Internal components and hooks
import { SearchBar } from '../components/SearchBar';
import { useSearch } from '../hooks/useSearch';

// 3. Utilities and APIs
import { storage } from '../utils/storage';
import { searchAPI } from '../api/search';

// 4. Styles
import '../styles/app.css';
```

### Performance Considerations

- **Lazy load pages**: Use `React.lazy()` for route-based code splitting
- **Memoize expensive computations**: Use `useMemo` when appropriate
- **Debounce inputs**: For search bars and real-time filtering
- **Optimize re-renders**: Use `React.memo` sparingly, only for expensive components
- **Use Suspense**: Wrap lazy-loaded components in `<Suspense>` with fallback

## Theme Support

**The project supports dark and light themes via data attributes:**

```javascript
// Toggle theme
document.body.dataset.theme = 'light'; // or 'dark'
```

- **Default theme**: Dark mode (`:root` variables)
- **Light theme**: Applied via `body[data-theme='light']` selector
- **IMPORTANT**: Always use CSS variables so components automatically adapt to theme changes
- **Never hardcode colors** - this breaks theme switching

## Testing Guidelines

- **Unit tests**: Use the project's test framework for component tests
- **Test user interactions**: Click handlers, form submissions, state changes
- **Test edge cases**: Empty states, error states, loading states
- **Accessibility tests**: Verify keyboard navigation, aria labels
- **Integration tests**: Located in `tests/e2e/` directory

## Backend Integration

- **API base URL**: Proxied through Vite dev server (`/api`, `/health`)
- **Production API**: Configured via environment variables
- **API clients**: Located in `frontend/src/api/`
- **Error handling**: Always handle API errors with user-friendly messages
- **Loading states**: Show loading indicators during API calls
- **Authentication**: Use `AuthContext` for auth state and token management

## Common Anti-Patterns to Avoid

❌ **DO NOT:**
- Hardcode colors (use CSS variables)
- Use Tailwind classes (use semantic CSS classes)
- Use CSS-in-JS libraries (use plain CSS)
- Create inline styles (define classes in app.css)
- Import unnecessary dependencies (keep bundle size small)
- Bypass authentication guards
- Ignore error states
- Skip accessibility attributes

✅ **DO:**
- Use CSS variables for all theme-able values
- Define semantic CSS classes in app.css
- Follow existing component patterns
- Handle loading and error states
- Include proper aria-labels
- Validate forms before submission
- Show user feedback (toasts, messages)
- Keep components small and focused

## Quick Reference

### File Locations
- Components: `frontend/src/components/`
- Pages: `frontend/src/pages/`
- Hooks: `frontend/src/hooks/`
- API clients: `frontend/src/api/`
- Styles: `frontend/src/styles/app.css`
- Public assets: `frontend/public/`

### CSS Variable Quick Reference
```css
var(--bg)          /* Page background */
var(--surface)     /* Card/panel background */
var(--text)        /* Primary text */
var(--text-dim)    /* Secondary text */
var(--accent)      /* Primary accent (purple) */
var(--accent-glow) /* Lighter accent */
var(--border)      /* Border color */
var(--radius)      /* Standard border radius (16px) */
```

### Common CSS Classes
```css
.btn, .btn.primary, .btn.ghost
.page, .header, .hero
.search-bar
.result-card, .results-grid
.modal, .modal-overlay
.toast, .toast-error, .toast-success
.skeleton-card, .ai-skeleton
```

---

## Design System Evolution

These rules should be updated as the project evolves. When making architectural changes:

1. Update this file to reflect new patterns
2. Communicate changes to the team
3. Update existing components to match new standards
4. Ensure backward compatibility when possible

**Last updated**: January 2025
