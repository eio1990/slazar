const QRCode = require('qrcode');

// Правильный URL для Expo - используем preview URL без https://
const EXPO_URL = 'exp://butchery-app-1.preview.emergentagent.com';

QRCode.toString(EXPO_URL, { type: 'terminal', small: true }, (err, qr) => {
  if (err) {
    console.error('Error generating QR:', err);
    process.exit(1);
  }
  console.log('\n📱 ПРАВИЛЬНЫЙ QR КОД для iOS:\n');
  console.log(qr);
  console.log('\n🔗 URL для Expo Go:', EXPO_URL);
  console.log('\n📱 ИЛИ введите вручную в Expo Go:\n   butchery-app-1.preview.emergentagent.com\n');
  console.log('⚠️  ВАЖНО: Если не работает, попробуйте открыть в браузере Safari:');
  console.log('   https://production-hub-41.preview.emergentagent.com');
  console.log('   А затем используйте веб-версию приложения\n');
});
