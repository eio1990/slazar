const Constants = require('expo-constants');

console.log('\n=== Expo Configuration ===');
console.log('Process env EXPO_PUBLIC_BACKEND_URL:', process.env.EXPO_PUBLIC_BACKEND_URL);
console.log('Process env EXPO_PACKAGER_HOSTNAME:', process.env.EXPO_PACKAGER_HOSTNAME);
console.log('Process env EXPO_TUNNEL_SUBDOMAIN:', process.env.EXPO_TUNNEL_SUBDOMAIN);

// Check what will be in the manifest
const fs = require('fs');
const envContent = fs.readFileSync('.env', 'utf-8');
console.log('\n=== .env file content ===');
console.log(envContent);

const appJson = require('./app.json');
console.log('\n=== app.json extra config ===');
console.log(JSON.stringify(appJson.expo.extra, null, 2));
