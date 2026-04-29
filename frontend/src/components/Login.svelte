<script>
  import { get } from 'svelte/store';
  import { onMount } from 'svelte';
  import { apiUrl, setAuth } from '../stores/auth.js';
import { t } from '../stores/i18n.js';
import LanguageSelector from '../components/LanguageSelector.svelte';

  let login       = $state('');
  let password    = $state('');
  let error       = $state('');
  let loading     = $state(false);
  let captcha     = $state('ABCDE');
  let userCaptcha = $state('');
  let showPassword = $state(false);
  let showForgot = $state(false);
  let forgotKod = $state('');
  let forgotNewPass = $state('');
  let forgotConfirmPass = $state('');
  let forgotError = $state('');
  let forgotSuccess = $state(false);
  let forgotLoading = $state(false);

  async function handleForgot(e) {
    e.preventDefault();
    forgotError = '';
    forgotSuccess = false;
    
    if (!forgotKod.trim()) { forgotError = get(t).enterCode; return; }
    if (!forgotNewPass.trim()) { forgotError = get(t).passwordPlaceholder; return; }
    if (forgotNewPass.length < 6) { forgotError = get(t).registerErrorPasswordLength; return; }
    if (forgotNewPass !== forgotConfirmPass) { forgotError = get(t).registerErrorPasswordMismatch; return; }
    
    forgotLoading = true;
    try {
      const res = await fetch(apiUrl + '/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ozel_kod: forgotKod.trim(), new_password: forgotNewPass }),
      });
      const data = await res.json();
      if (res.ok) {
        forgotSuccess = true;
        setTimeout(() => { showForgot = false; forgotKod = ''; forgotNewPass = ''; forgotConfirmPass = ''; }, 2000);
      } else {
        forgotError = data.detail || get(t).error;
      }
    } catch { forgotError = get(t).serverError; }
    finally { forgotLoading = false; }
  }

  let sections = $state({ hero: false, features: false, how: false, who: false, footer: false });

  function generateCaptcha() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    captcha = Array.from({ length: 5 }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
  }

  function handleScroll() {
    const wh = window.innerHeight;
    const map = { hero: '.hero', features: '.features', how: '.how', who: '.who', footer: 'footer' };
    Object.entries(map).forEach(([k, sel]) => {
      const el = document.querySelector(sel);
      if (el && el.getBoundingClientRect().top < wh * 0.9) sections[k] = true;
    });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    error = '';
    if (userCaptcha.toUpperCase() !== captcha) {
      error = get(t).captchaError;
      generateCaptcha();
      return;
    }
    loading = true;
    try {
      const res  = await fetch(apiUrl + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ login: login.trim().toLowerCase(), password }),
      });
      const data = await res.json();
      if (data.token) {
        setAuth(data.user, data.token);
      } else {
        error = data.detail || get(t).error;
        generateCaptcha();
      }
    } catch {
      error = get(t).error;
      generateCaptcha();
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    generateCaptcha();
    window.addEventListener('scroll', handleScroll, { passive: true });
    setTimeout(handleScroll, 100);
    return () => window.removeEventListener('scroll', handleScroll);
  });
</script>

<div class="page">
<nav class="nav">
  <div class="logo">◎ <span>AiTech</span></div>
  <LanguageSelector />
</nav>

  <main class="hero" class:visible={sections.hero}>
    <div class="content">
      <span class="badge">{$t.heroBadge}</span>
      <h1>{$t.heroTitleSplit.first}<br/><span class="accent">{$t.heroTitleSplit.ai}</span><br/>{$t.heroTitleSplit.last}</h1>
      <p>{$t.heroDesc}</p>
    </div>

    <div class="login-box">
      <h2>{$t.loginWelcome}</h2>
      <p class="sub">{$t.loginSubtitle}</p>

      <form onsubmit={handleSubmit}>
        <input type="text" placeholder={$t.usernamePlaceholder} bind:value={login} autocomplete="username" required />

        <div class="pass-wrap">
          <input type={showPassword ? 'text' : 'password'} placeholder={$t.passwordPlaceholder} bind:value={password} autocomplete="current-password" required />
          <button type="button" class="eye" onclick={() => showPassword = !showPassword}>
            {showPassword ? '◉' : '○'}
          </button>
        </div>

        <div class="captcha-wrap">
          <button type="button" class="captcha" onclick={generateCaptcha} title={$t.captchaRefreshTitle}>{captcha}</button>
          <input type="text" placeholder={$t.captchaPlaceholder} bind:value={userCaptcha} maxlength="5" required />
        </div>

        {#if error}<p class="err">{error}</p>{/if}

        <button type="submit" class="btn" disabled={loading}>
          {loading ? $t.loginLoading : $t.loginButton}
        </button>
      </form>

      <p class="foot">{$t.noAccount} <a href="#register">{$t.createAccount}</a></p>
      <p class="foot"><a href="#forgot" onclick={() => showForgot = true}>{$t.forgotPassword}</a></p>
    </div>
  </main>

  {#if showForgot}
  <div class="modal-overlay" role="dialog" aria-modal="true" onclick={() => showForgot = false} onkeydown={(e) => e.key === 'Escape' && (showForgot = false)} tabindex="-1">
    <div class="forgot-box" role="document" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()}>
      <button class="close-btn" onclick={() => showForgot = false}>✕</button>
      <h2>{$t.forgotPassword}</h2>
      <p class="sub">{$t.forgotPasswordDesc}</p>
      
      <form onsubmit={handleForgot}>
        <input type="text" placeholder={$t.ozelKodPlaceholder} bind:value={forgotKod} required />
        <input type="password" placeholder={$t.newPasswordPlaceholder} bind:value={forgotNewPass} required />
        <input type="password" placeholder={$t.confirmPasswordPlaceholder} bind:value={forgotConfirmPass} required />
        
        {#if forgotError}<p class="err">{forgotError}</p>{/if}
        {#if forgotSuccess}<p class="success">✓ {$t.passwordResetSuccess}</p>{/if}
        
        <button type="submit" class="btn" disabled={forgotLoading}>
          {forgotLoading ? $t.loading : $t.resetPassword}
        </button>
      </form>
      
      <div class="lang-selector">
        <LanguageSelector />
      </div>
    </div>
  </div>
  {/if}

  <section class="features" class:visible={sections.features}>
    <h2>{$t.featuresTitle}</h2>
    <div class="grid">
      <div class="card">🤖<h3>{$t.featureAiSupportTitle}</h3><p>{$t.featureAiSupportDesc}</p></div>
      <div class="card">📊<h3>{$t.featureAnalyticsTitle}</h3><p>{$t.featureAnalyticsDesc}</p></div>
      <div class="card">🔒<h3>{$t.featureSecureTitle}</h3><p>{$t.featureSecureDesc}</p></div>
      <div class="card">💬<h3>{$t.featureQuestionsTitle}</h3><p>{$t.featureQuestionsDesc}</p></div>
    </div>
  </section>

  <section class="how" class:visible={sections.how}>
    <h2>{$t.howTitle}</h2>
    <div class="steps">
      <div class="step"><span class="num">01</span><b>{$t.howStep1Teacher}</b><p>{$t.howStep1Desc}</p></div>
      <span class="arrow">→</span>
      <div class="step"><span class="num">02</span><b>{$t.howStep2Student}</b><p>{$t.howStep2Desc}</p></div>
      <span class="arrow">→</span>
      <div class="step"><span class="num">03</span><b>{$t.howStep3Question}</b><p>{$t.howStep3Desc}</p></div>
      <span class="arrow">→</span>
      <div class="step"><span class="num">04</span><b>{$t.howStep4Stats}</b><p>{$t.howStep4Desc}</p></div>
    </div>
  </section>

  <section class="who" class:visible={sections.who}>
    <div class="col">
      <span class="badge">{$t.roleTeacher}</span>
      <h2>{$t.whoTeacherTitle}</h2>
      <ul><li>✓ {$t.addLesson}</li><li>✓ {$t.addStudent}</li><li>✓ AI {$t.aiAssistant}</li></ul>
    </div>
    <div class="col">
      <span class="badge">{$t.roleStudent}</span>
      <h2>{$t.whoStudentTitle}</h2>
      <ul><li>✓ {$t.lessons}</li><li>✓ {$t.questions}</li><li>✓ AI {$t.answer}</li></ul>
    </div>
  </section>

  <footer class:visible={sections.footer}>
    <div class="logo">◎ <span>AiTech</span></div>
    <p>{$t.footerText}</p>
  </footer>
</div>

<style>
  .page { background:#050507; color:#fff; min-height:100vh; }

  .nav { padding:24px 48px; position:fixed; top:0; left:0; right:0; z-index:100; background:rgba(5,5,7,.85); backdrop-filter:blur(20px); border-bottom:1px solid rgba(255,255,255,.04); }
  .logo { font-size:22px; font-weight:700; background:linear-gradient(135deg,#fff,#94a3b8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }

  .hero { display:grid; grid-template-columns:1fr 380px; gap:100px; max-width:1100px; margin:0 auto; padding:140px 48px 100px; align-items:center; opacity:0; transform:translateY(40px); transition:all 1s cubic-bezier(.16,1,.3,1); }
  .hero.visible { opacity:1; transform:translateY(0); }

  .content { opacity:0; transform:translateY(30px); transition:all .8s cubic-bezier(.16,1,.3,1) .2s; }
  .hero.visible .content { opacity:1; transform:translateY(0); }

  .badge { display:inline-block; padding:8px 16px; background:rgba(59,130,246,.1); border:1px solid rgba(59,130,246,.2); border-radius:100px; font-size:13px; color:#60a5fa; margin-bottom:28px; }
  .content h1 { font-size:56px; font-weight:700; line-height:1.05; letter-spacing:-1px; margin-bottom:20px; }
  .accent { background:linear-gradient(135deg,#3b82f6,#8b5cf6,#a855f7); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  .content p { font-size:18px; color:#71717a; line-height:1.7; max-width:440px; }

  .login-box { background:rgba(12,12,15,.8); border:1px solid rgba(255,255,255,.06); border-radius:20px; padding:32px; opacity:0; transform:translateY(30px); transition:all .8s cubic-bezier(.16,1,.3,1) .3s; }
  .hero.visible .login-box { opacity:1; transform:translateY(0); }
  .login-box h2 { font-size:24px; margin-bottom:4px; }
  .sub { font-size:14px; color:#52525b; margin-bottom:24px; }

  input { width:100%; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.06); border-radius:12px; padding:16px; font-size:15px; color:#fff; margin-bottom:14px; transition:all .2s ease; box-sizing:border-box; }
  input:focus { border-color:rgba(59,130,246,.5); background:rgba(255,255,255,.06); outline:none; }
  input::placeholder { color:#3f3f46; }

  .pass-wrap { position:relative; margin-bottom:14px; }
  .pass-wrap input { margin-bottom:0; }
  .pass-wrap .eye { position:absolute; right:14px; top:50%; transform:translateY(-50%); background:none; border:none; color:#52525b; font-size:18px; cursor:pointer; transition:color .2s; }
  .pass-wrap .eye:hover { color:#60a5fa; }

  .captcha-wrap { display:grid; grid-template-columns:110px 1fr; gap:12px; margin-bottom:14px; align-items:start; }
  .captcha { background:linear-gradient(145deg,#18181c,#1f1f24); border:1px solid rgba(255,255,255,.06); border-radius:12px; padding:16px 12px; text-align:center; font-size:22px; font-weight:800; letter-spacing:6px; color:#60a5fa; font-family:monospace; user-select:none; cursor:pointer; transition:opacity .2s; }
  .captcha:hover { opacity:.8; }

  .err { color:#f87171; font-size:13px; margin-bottom:14px; }

  .btn { width:100%; background:linear-gradient(135deg,#3b82f6,#2563eb); color:#fff; padding:16px; border-radius:12px; font-size:15px; font-weight:600; border:none; cursor:pointer; transition:all .3s ease; }
  .btn:hover:not(:disabled) { transform:translateY(-2px); box-shadow:0 12px 32px rgba(59,130,246,.35); }
  .btn:disabled { opacity:.7; cursor:not-allowed; }

  .foot { font-size:14px; color:#52525b; margin-top:20px; text-align:center; }
  .foot a { color:#60a5fa; text-decoration:none; transition:color .2s; }
  .foot a:hover { color:#93c5fd; }

  .features, .how, .who { padding:100px 48px; max-width:1100px; margin:0 auto; opacity:0; transform:translateY(50px); transition:all 1s cubic-bezier(.16,1,.3,1); }
  .features.visible, .how.visible, .who.visible { opacity:1; transform:translateY(0); }

  .features h2, .how h2 { font-size:36px; text-align:center; margin-bottom:40px; }
  .grid { display:grid; grid-template-columns:repeat(2,1fr); gap:20px; }
  .card { background:rgba(20,20,24,.6); border:1px solid rgba(255,255,255,.04); border-radius:20px; padding:28px; transition:all .4s cubic-bezier(.16,1,.3,1); }
  .card:hover { transform:translateY(-8px); border-color:rgba(59,130,246,.2); }
  .card h3 { font-size:20px; margin:16px 0 8px; }
  .card p { font-size:15px; color:#71717a; }

  .steps { display:flex; justify-content:center; align-items:center; gap:20px; flex-wrap:wrap; }
  .step { background:rgba(20,20,24,.6); border-radius:16px; padding:24px; text-align:center; min-width:140px; transition:all .4s ease; }
  .step:hover { transform:scale(1.05); }
  .num { display:block; font-size:28px; font-weight:700; color:#3b82f6; margin-bottom:8px; }
  .step b { display:block; font-size:16px; margin-bottom:4px; }
  .step p { font-size:13px; color:#52525b; }
  .arrow { font-size:28px; color:#3b82f6; }

  .who { display:grid; grid-template-columns:1fr 1fr; gap:30px; }
  .col { background:rgba(20,20,24,.6); border-radius:20px; padding:36px; transition:all .4s ease; }
  .col:hover { transform:translateY(-6px); }
  .col .badge { display:inline-block; padding:8px 14px; background:rgba(59,130,246,.1); border:1px solid rgba(59,130,246,.2); border-radius:100px; font-size:12px; color:#60a5fa; margin-bottom:16px; }
  .col h2 { font-size:26px; margin-bottom:24px; }
  .col ul { list-style:none; padding:0; }
  .col li { font-size:16px; color:#a1a1aa; margin-bottom:14px; transition:all .2s; }
  .col li:hover { color:#fff; transform:translateX(6px); }

  footer { padding:60px 48px; text-align:center; opacity:0; transform:translateY(30px); transition:all .8s ease; }
  footer.visible { opacity:1; transform:translateY(0); }
  footer .logo { margin-bottom:16px; }
  footer p { color:#52525b; font-size:14px; }

  @media (max-width:900px) {
    .hero { grid-template-columns:1fr; gap:60px; padding:120px 24px 80px; text-align:center; }
    .content p { margin:0 auto; }
    .content h1 { font-size:40px; }
    .grid { grid-template-columns:1fr; }
    .steps { flex-direction:column; }
    .arrow { transform:rotate(90deg); }
    .who { grid-template-columns:1fr; }
    .features, .how { padding:80px 24px; }
  
  .modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,.8); z-index:200; display:flex; align-items:center; justify-content:center; }
  .forgot-box { background:rgba(12,12,15,.95); border:1px solid rgba(255,255,255,.08); border-radius:20px; padding:32px; max-width:380px; width:90%; position:relative; }
.forgot-box .close-btn { position:absolute; right:16px; top:16px; background:none; border:none; color:#71717a; font-size:20px; cursor:pointer; }
  .forgot-box h2 { margin-bottom:8px; }
  .forgot-box .lang-selector { margin-top:24px; padding-top:16px; border-top:1px solid rgba(255,255,255,.06); display:flex; justify-content:center; }
.forgot-box .success { color:#22c55e; padding:12px; background:rgba(34,197,94,.1); border-radius:8px; text-align:center; }
  }
</style>
