import { createContext, useContext, useMemo, useState } from 'react'
import {
  SUPPORTED_LANGUAGES,
  codeToStoryLanguage,
  storyLanguageToCode,
  translations,
} from '../i18n/translations'

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [langCode, setLangCodeState] = useState(() => {
    const saved = localStorage.getItem('yugen_ui_language')
    if (['EN', 'JA', 'HI', 'FR'].includes(saved)) return saved
    const savedStoryLang = localStorage.getItem('yugen_story_language')
    return storyLanguageToCode(savedStoryLang)
  })

  function setLanguageCode(nextCode) {
    const valid = ['EN', 'JA', 'HI', 'FR'].includes(nextCode) ? nextCode : 'EN'
    setLangCodeState(valid)
    localStorage.setItem('yugen_ui_language', valid)
    localStorage.setItem('yugen_story_language', codeToStoryLanguage(valid))
  }

  function setStoryLanguage(storyLang) {
    setLanguageCode(storyLanguageToCode(storyLang))
  }

  const value = useMemo(
    () => ({
      langCode,
      storyLanguage: codeToStoryLanguage(langCode),
      languages: SUPPORTED_LANGUAGES,
      t: translations[langCode] || translations.EN,
      setLanguageCode,
      setStoryLanguage,
    }),
    [langCode],
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return ctx
}
