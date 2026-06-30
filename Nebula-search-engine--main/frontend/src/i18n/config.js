import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import es from './locales/es.json';

const saved = (() => {
  try {
    const raw = localStorage.getItem('nebula_prefs');
    if (raw) {
      const prefs = JSON.parse(raw);
      if (prefs.language) return prefs.language;
    }
  } catch {}
  return null;
})();

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, es: { translation: es } },
  lng: saved || 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnObjects: true,
});

export default i18n;
