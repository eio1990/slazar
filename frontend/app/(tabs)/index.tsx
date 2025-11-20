import { Redirect } from 'expo-router';

// Redirect to operations tab as default screen
export default function Index() {
  return <Redirect href="/(tabs)/operations" />;
}
