# Internationalization (i18n) Guide

This project uses `react-i18next` for internationalization support.

## Structure

```
i18n/
├── config.ts              # i18n configuration
└── locales/
    ├── en/               # English translations
    │   ├── common.json   # Common UI elements
    │   ├── auth.json     # Authentication pages
    │   ├── settings.json # Settings page
    │   └── server.json   # Server management
    └── ko/               # Korean translations
        ├── common.json
        ├── auth.json
        ├── settings.json
        └── server.json
```

## Usage in Components

### Basic Translation

```typescript
import { useTranslation } from 'react-i18next'

function MyComponent() {
  const { t } = useTranslation('namespace')
  
  return <h1>{t('key')}</h1>
}
```

### With Interpolation

```typescript
// Translation file: { "welcome": "Welcome, {{name}}!" }
const { t } = useTranslation()
return <p>{t('welcome', { name: 'John' })}</p>
```

### With Pluralization

```typescript
// Translation file: 
// { 
//   "tools": "{{count}} tool",
//   "tools_plural": "{{count}} tools"
// }
const { t } = useTranslation()
return <p>{t('tools', { count: 5 })}</p>
```

### Change Language

```typescript
const { i18n } = useTranslation()

// Change language
i18n.changeLanguage('ko')

// Get current language
const currentLang = i18n.language
```

## Adding a New Language

1. Create a new folder in `locales/` (e.g., `ja/` for Japanese)
2. Copy all JSON files from `en/` to the new folder
3. Translate the values (keep the keys the same)
4. Import translations in `config.ts`:
   ```typescript
   import jaCommon from './locales/ja/common.json'
   // ... other imports
   ```
5. Add to resources in `config.ts`:
   ```typescript
   resources: {
     // ... existing languages
     ja: {
       common: jaCommon,
       // ... other namespaces
     }
   }
   ```
6. Add language option to `LanguageSwitcher.tsx`

## Translation File Guidelines

- **Keep keys consistent** across all languages
- **Use nested objects** for better organization
- **Use descriptive keys** (e.g., `button.save` instead of `btn1`)
- **Include context** in key names when needed (e.g., `auth.login.button` vs `settings.save.button`)
- **Use interpolation** for dynamic content: `"Welcome, {{name}}!"`
- **Use pluralization** for countable items: `"tools"` and `"tools_plural"`

## Namespaces

- **common**: Shared UI elements (buttons, status, messages)
- **auth**: Login, register, logout
- **settings**: Settings page
- **server**: Server and tool management

## Best Practices

1. **Always use translation keys**, never hardcode text
2. **Test with different languages** to ensure UI doesn't break
3. **Keep translations short** for buttons and labels
4. **Provide context** in longer descriptions
5. **Use the same namespace** for related components
6. **Update all language files** when adding new keys

## Language Detection

The app automatically:
1. Checks `localStorage` for saved language preference
2. Falls back to browser language if supported
3. Defaults to English if browser language is not supported

Language preference is saved automatically when changed.
