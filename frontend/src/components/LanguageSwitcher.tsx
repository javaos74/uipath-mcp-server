import { useTranslation } from 'react-i18next'
import { ChangeEvent } from 'react'
import './LanguageSwitcher.css'

export default function LanguageSwitcher() {
  const { i18n } = useTranslation()

  const languages = [
    { code: 'en', label: 'English', flag: '🇺🇸' },
    { code: 'ko', label: '한국어', flag: '🇰🇷' },
    { code: 'zh', label: '中文', flag: '🇨🇳' },
    { code: 'ja', label: '日本語', flag: '🇯🇵' },
  ]

  const handleLanguageChange = (e: ChangeEvent<HTMLSelectElement>) => {
    i18n.changeLanguage(e.target.value)
  }

  const currentLang = languages.find(lang => lang.code === i18n.language)

  return (
    <div className="language-switcher">
      <span className="current-flag">{currentLang?.flag}</span>
      <select
        className="lang-select"
        value={i18n.language}
        onChange={handleLanguageChange}
        aria-label="Select language"
      >
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.flag} {lang.label}
          </option>
        ))}
      </select>
    </div>
  )
}
