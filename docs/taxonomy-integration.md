# Taxonomy Integration for YouTube Workflows

## Overview
This document explains how to integrate the shared taxonomy configuration between Mission Control (port 3007) and Social Intelligence Agent (port 8080).

## Files Created/Modified

1. **Shared Taxonomy Configuration**
   - `services/mission-control/src/utils/shared-taxonomy.ts`

2. **UI Components**
   - `services/mission-control/src/components/workflows/CategoryDropdown.tsx`
   - `services/mission-control/src/pages/workflows/niche-scout/index-with-dropdown.tsx`

## How to Implement

### 1. Using the New Components

To replace the current category dropdown with the shared taxonomy version:

```tsx
// Import the dropdown component
import CategoryDropdown from "../../../components/workflows/CategoryDropdown";

// Then in your component
<CategoryDropdown
  value={form.category}
  onChange={(value) => {
    updateForm("category", value);
    updateForm("subcategory", "");
  }}
/>
```

### 2. Matching Existing UI

The shared taxonomy has been configured to match the categories seen in the UI:
- All
- Gaming
- Education
- Entertainment
- Howto & Style
- Science & Technology

### 3. Integration with Agent Orchestrator

To use the same taxonomy in the Agent Orchestrator:

1. Copy the `shared-taxonomy.ts` file to `services/agent-orchestrator/src/config/taxonomy.ts`
2. Update imports in the Agent's components to use this configuration

## Testing the Integration

1. Start Mission Control on port 3007:
   ```bash
   cd services/mission-control
   npm run dev
   ```

2. Navigate to http://localhost:3007/workflows/niche-scout

3. Verify that the category dropdown shows the correct options

4. Start the Agent Orchestrator on port 8080 and verify the same taxonomy is used

## Troubleshooting

If the dropdown doesn't display properly:
1. Check browser console for errors
2. Verify the component is correctly imported
3. Check that there are no CSS conflicts

## Benefits of Shared Taxonomy

- Consistent category structure across platforms
- Centralized management of taxonomy changes
- Improved data consistency for reporting and analytics
