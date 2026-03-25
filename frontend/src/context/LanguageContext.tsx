import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'
import { 
  Language, 
  translations, 
  getStoredLanguage, 
  setStoredLanguage,
  DEFAULT_LANGUAGE 
} from '../i18n'

type TranslationValue = string | { [key: string]: TranslationValue }
type Translations = typeof translations['en']

interface LanguageContextType {
  language: Language
  setLanguage: (lang: Language) => void
  t: (key: string, params?: Record<string, string | number>) => string
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(DEFAULT_LANGUAGE)

  useEffect(() => {
    const stored = getStoredLanguage()
    setLanguageState(stored)
  }, [])

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang)
    setStoredLanguage(lang)
  }, [])

  const t = useCallback((key: string, params?: Record<string, string | number>): string => {
    const keys = key.split('.')
    let value: TranslationValue = translations[language] as unknown as TranslationValue

    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = (value as Record<string, TranslationValue>)[k]
      } else {
        // Fallback to English
        value = translations[DEFAULT_LANGUAGE] as unknown as TranslationValue
        for (const fallbackKey of keys) {
          if (value && typeof value === 'object' && fallbackKey in value) {
            value = (value as Record<string, TranslationValue>)[fallbackKey]
          } else {
            return key // Return key if translation not found
          }
        }
        break
      }
    }

    if (typeof value !== 'string') {
      return key
    }

    // Replace parameters
    let result = value
    if (params) {
      Object.entries(params).forEach(([paramKey, paramValue]) => {
        result = result.replace(new RegExp(`{${paramKey}}`, 'g'), String(paramValue))
      })
    }

    return result
  }, [language])

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return context
}

// Convenience hook for just translations
export function useTranslation() {
  const { t } = useLanguage()
  return { t }
}
