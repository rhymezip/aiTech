<script>
  import { get } from 'svelte/store';
  import { currentLang, languages } from '../stores/i18n.js';
  import { authFetch, apiUrl } from '../stores/auth.js';

  let showDropdown = $state(false);
  let langCode = $state('tr');

  const unsub = currentLang.subscribe(v => langCode = v);

  async function selectLang(code) {
    currentLang.set(code);
    showDropdown = false;

    try {
      await authFetch(apiUrl + '/user/dil', {
        method: 'POST',
        body: JSON.stringify({ dil: code }),
      });
    } catch (e) {
      console.error(get(t).error + ':', e);
    }
  }

  function getCurrentLang() {
    return languages.find(l => l.code === langCode) || languages[0];
  }
</script>

<div class="lang-selector">
  <button class="lang-btn" onclick={() => showDropdown = !showDropdown}>
    <span class="flag">{getCurrentLang().flag}</span>
    <span class="code">{langCode.toUpperCase()}</span>
    <span class="arrow">{showDropdown ? '▲' : '▼'}</span>
  </button>

  {#if showDropdown}
    <div class="dropdown">
      {#each languages as lang}
        <button 
          class="lang-option" 
          class:active={lang.code === langCode}
          onclick={() => selectLang(lang.code)}
        >
          <span class="flag">{lang.flag}</span>
          <span class="name">{lang.name}</span>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .lang-selector { position: relative; }

  .lang-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 6px 10px;
    cursor: pointer;
    transition: all 0.2s;
    color: #a1a1aa;
    font-size: 12px;
  }

  .lang-btn:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.15);
    color: #fff;
  }

  .lang-btn .flag { font-size: 14px; }
  .lang-btn .code { font-weight: 600; letter-spacing: 0.5px; }
  .lang-btn .arrow { font-size: 8px; opacity: 0.6; }

  .dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 4px;
    background: rgba(15, 15, 18, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 6px;
    min-width: 140px;
    z-index: 1000;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  }

  .lang-option {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    background: none;
    border: none;
    padding: 8px 10px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.15s;
    color: #a1a1aa;
    font-size: 13px;
    text-align: left;
  }

  .lang-option:hover {
    background: rgba(255, 255, 255, 0.06);
    color: #fff;
  }

  .lang-option.active {
    background: rgba(59, 130, 246, 0.15);
    color: #60a5fa;
  }

  .lang-option .flag { font-size: 16px; }
  .lang-option .name { flex: 1; }
</style>