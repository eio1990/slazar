import 'dotenv/config';

export default {
  expo: {
    name: "Склад - Управління запасами",
    slug: "warehouse-management",
    version: "1.0.0",
    orientation: "portrait",
    icon: "./assets/icon.png",
    userInterfaceStyle: "light",
    newArchEnabled: true,
    splash: {
      image: "./assets/splash-icon.png",
      resizeMode: "contain",
      backgroundColor: "#ffffff"
    },
    ios: {
      supportsTablet: true
    },
    android: {
      adaptiveIcon: {
        foregroundImage: "./assets/adaptive-icon.png",
        backgroundColor: "#ffffff"
      }
    },
    web: {
      favicon: "./assets/favicon.png",
      bundler: "metro"
    },
    locales: {
      uk: "./i18n/uk.json"
    },
    scheme: "warehouse-management",
    plugins: [
      "expo-router",
      [
        "expo-font",
        {
          "fonts": ["./assets/fonts/SpaceMono-Regular.ttf"]
        }
      ],
      "expo-secure-store",
      "expo-web-browser"
    ],
    experiments: {
      typedRoutes: true
    },
    extra: {
      EXPO_PUBLIC_BACKEND_URL: process.env.EXPO_PUBLIC_BACKEND_URL || "http://localhost:8001"
    }
  }
};
