import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

// Import translations
import enCommon from './locales/en/common.json'
import enAuth from './locales/en/auth.json'
import enSettings from './locales/en/settings.json'
import enServer from './locales/en/server.json'

import koCommon from './locales/ko/common.json'
import koAuth from './locales/ko/auth.json'
import koSettings from './locales/ko/settings.json'
import koServer from './locales/ko/server.json'

import zhCommon from './locales/zh/common.json'
import zhAuth from './locales/zh/auth.json'
import zhSettings from './locales/zh/settings.json'
import zhServer from './locales/zh/server.json'

import jaCommon from './locales/ja/common.json'
import jaAuth from './locales/ja/auth.json'
import jaSettings from './locales/ja/settings.json'
import jaServer from './locales/ja/server.json'

// Get saved language from localStorage or use browser language
const savedLanguage = localStorage.getItem('language')
const browserLanguage = navigator.language.split('-')[0] // 'en-US' -> 'en', 'zh-CN' -> 'zh'
const supportedLanguages = ['en', 'ko', 'zh', 'ja']
const defaultLanguage = savedLanguage || (supportedLanguages.includes(browserLanguage) ? browserLanguage : 'en')

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        common: enCommon,
        auth: enAuth,
        settings: enSettings,
        server: enServer,
      },
      ko: {
        common: koCommon,
        auth: koAuth,
        settings: koSettings,
        server: koServer,
      },
      zh: {
        common: zhCommon,
        auth: zhAuth,
        settings: zhSettings,
        server: zhServer,
      },
      ja: {
        common: jaCommon,
        auth: jaAuth,
        settings: jaSettings,
        server: jaServer,
      },
    },
    lng: defaultLanguage,
    fallbackLng: 'en',
    defaultNS: 'common',
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    react: {
      useSuspense: false, // Disable suspense for now
    },
  })

// Save language preference when it changes
i18n.on('languageChanged', (lng) => {
  localStorage.setItem('language', lng)
})

export default i18n
