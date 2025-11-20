const QRCode = require('qrcode');

const EXPO_URL = 'exp://butchery-app-1.preview.emergentagent.com';

QRCode.toString(EXPO_URL, { type: 'terminal', small: true }, (err, qr) => {
  if (err) {
    console.error('Error generating QR:', err);
    process.exit(1);
  }
  console.log('\n📱 Сканируйте QR код с помощью Expo Go на iOS:\n');
  console.log(qr);
  console.log('\n🔗 Прямая ссылка:', EXPO_URL);
  console.log('\n📱 Или откройте Expo Go и введите: butchery-app-1.preview.emergentagent.com\n');
});
