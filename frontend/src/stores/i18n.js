import { writable, derived } from 'svelte/store';

export const languages = [
  { code: 'tr', name: 'Türkçe', flag: '🇹🇷' },
  { code: 'tk', name: 'Türkmençe', flag: '🇹🇲' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'zh', name: '中文', flag: '🇨🇳' },
  { code: 'ko', name: '한국어', flag: '🇰🇷' },
  { code: 'ja', name: '日本語', flag: '🇯🇵' },
  { code: 'pt', name: 'Português', flag: '🇧🇷' },
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
];

import tr from './languages/tr.js';
import tk from './languages/tk.js';
import en from './languages/en.js';
import zh from './languages/zh.js';
import ko from './languages/ko.js';
import ja from './languages/ja.js';
import pt from './languages/pt.js';
import ru from './languages/ru.js';
import fr from './languages/fr.js';

const translations = {
  tr,
  tk,
  en,
  zh,
  ko,
  ja,
  pt,
  ru,
  fr,
};

function createI18n() {
  const { subscribe, set, update } = writable('en');

  return {
    subscribe,
    set: (lang) => {
      localStorage.setItem('language', lang);
      set(lang);
    },
    init: () => {
      const saved = localStorage.getItem('language');
      if (saved && translations[saved]) {
        set(saved);
      } else {
        const browserLang = navigator.language?.split('-')[0];
        const found = languages.find(l => l.code === browserLang);
        set(found && translations[found.code] ? found.code : 'tr');
      }
    },
  };
}

export const currentLang = createI18n();
export const initI18n = currentLang.init;

export const t = derived(currentLang, ($lang) => {
  return translations[$lang] || translations.tr;
});