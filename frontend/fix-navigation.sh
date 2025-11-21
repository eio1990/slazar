#!/bin/bash

# Fix navigation in butchery files
find /app/frontend/app/butchery -name "*.tsx" -type f -exec sed -i "s/router\.back()/router.push('\/(tabs)\/butchery' as any)/g" {} \;

# Fix navigation in batches files (production tab)
find /app/frontend/app/batches -name "*.tsx" -type f -exec sed -i "s/router\.back()/router.push('\/(tabs)\/production' as any)/g" {} \;

# Fix navigation in stock/index.tsx (should go to operations tab)
sed -i "s/router\.back()/router.push('\/(tabs)\/operations' as any)/g" /app/frontend/app/stock/index.tsx

# Fix navigation in recipes files (should go to operations tab via hamburger menu)
find /app/frontend/app/recipes -name "*.tsx" -type f -exec sed -i "s/router\.back()/router.push('\/(tabs)\/operations' as any)/g" {} \;

# Fix navigation in analytics (should go to operations tab via hamburger menu)
if [ -f /app/frontend/app/analytics/index.tsx ]; then
  sed -i "s/router\.back()/router.push('\/(tabs)\/operations' as any)/g" /app/frontend/app/analytics/index.tsx
fi

echo "Navigation fixes applied!"
