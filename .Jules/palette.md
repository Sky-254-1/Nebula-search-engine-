## 2025-06-26 - Standardizing Modal Interaction Patterns
**Learning:** The application had an inconsistent modal implementation where standard UX expectations (Escape to close, click-outside to close) were missing. This creates a "trapped" feeling for users, especially those using keyboard navigation or assistive technologies.
**Action:** Always implement `useEffect` for Escape key listeners and `onClick` handlers on overlays for modals. Ensure the close button is not just present in code but visually accessible and consistently styled.
