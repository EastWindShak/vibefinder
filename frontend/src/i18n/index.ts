import en from './translations/en.json'
import es from './translations/es.json'
import de from './translations/de.json'
import fr from './translations/fr.json'
import it from './translations/it.json'
import hi from './translations/hi.json'

export type Language = 'en' | 'de' | 'es' | 'fr' | 'it' | 'hi'

export const LANGUAGES: { code: Language; name: string }[] = [
  { code: 'en', name: 'English' },
  { code: 'de', name: 'Deutsch' },
  { code: 'es', name: 'Español' },
  { code: 'fr', name: 'Français' },
  { code: 'it', name: 'Italiano' },
  { code: 'hi', name: 'हिंदी' },
]

export const translations: Record<Language, typeof en> = {
  en,
  es,
  de,
  fr,
  it,
  hi,
}

export const DEFAULT_LANGUAGE: Language = 'en'

export function getStoredLanguage(): Language {
  const stored = localStorage.getItem('language')
  if (stored && LANGUAGES.some(l => l.code === stored)) {
    return stored as Language
  }
  
  // Try to detect browser language
  const browserLang = navigator.language.split('-')[0]
  if (LANGUAGES.some(l => l.code === browserLang)) {
    return browserLang as Language
  }
  
  return DEFAULT_LANGUAGE
}

export function setStoredLanguage(language: Language): void {
  localStorage.setItem('language', language)
}
