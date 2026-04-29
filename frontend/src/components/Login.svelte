<script>
  import { get } from 'svelte/store';
  import { onMount } from 'svelte';
  import { apiUrl, setAuth } from '../stores/auth.js';
  import { t } from '../stores/i18n.js';
  import LanguageSelector from './LanguageSelector.svelte';

  // Ana sayfa state
  let login        = $state('');
  let password     = $state('');
  let error        = $state('');
  let loading      = $state(false);
  let captcha      = $state('ABCDE');
  let userCaptcha  = $state('');
  let showPassword = $state(false);

  // Sayfa: 'login' | 'forgot'
  let page = $state('login');

  // Şifremi unuttum state
  let forgotLogin       = $state('');
  let forgotKod         = $state('');
  let forgotNewPass     = $state('');
  let forgotConfirmPass = $state('');
  let forgotError       = $state('');
  let forgotSuccess     = $state(false);
  let forgotLoading     = $state(false);
  let showForgotPass    = $state(false);

  // Scroll animasyonları
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

  async function handleForgot(e) {
    e.preventDefault();
    forgotError = '';
    forgotSuccess = false;

    if (!forgotLogin.trim())       { forgotError = get(t).usernamePlaceholder + ' ' + get(t).enterCode; return; }
    if (!forgotKod.trim())          { forgotError = get(t).enterCode; return; }
    if (!forgotNewPass.trim())      { forgotError = get(t).passwordPlaceholder; return; }
    if (forgotNewPass.length < 6)   { forgotError = get(t).registerErrorPasswordLength; return; }
    if (forgotNewPass !== forgotConfirmPass) { forgotError = get(t).registerErrorPasswordMismatch; return; }

    forgotLoading = true;
    try {
      const res = await fetch(apiUrl + '/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          login: forgotLogin.trim().toLowerCase(),
          ozel_kod: forgotKod.trim(),
          new_password: forgotNewPass
        }),
      });
      const data = await res.json();
      if (res.ok) {
        forgotSuccess = true;
      } else {
        forgotError = data.detail || get(t).error;
      }
    } catch { forgotError = get(t).serverError; }
    finally { forgotLoading = false; }
  }

  function goToLogin() {
    page = 'login';
    forgotLogin = ''; forgotKod = ''; forgotNewPass = ''; forgotConfirmPass = '';
    forgotError = ''; forgotSuccess = false;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  onMount(() => {
    generateCaptcha();
    window.addEventListener('scroll', handleScroll, { passive: true });
    setTimeout(handleScroll, 100);
    return () => window.removeEventListener('scroll', handleScroll);
  });
</script>

<!-- ───────────────── LOGIN SAYFASI ───────────────── -->
{#if page === 'login'}
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
      <p class="foot">
        <button class="link-btn" onclick={() => { page = 'forgot'; window.scrollTo({top:0}); }}>
          {$t.forgotPassword}
        </button>
      </p>
    </div>
  </main>

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

<!-- ───────────────── ŞİFREMİ UNUTTUM SAYFASI ───────────────── -->
{:else}
<div class="page forgot-page">
  <nav class="nav">
    <div class="logo">◎ <span>AiTech</span></div>
    <LanguageSelector />
  </nav>

  <div class="forgot-container">

    <!-- Sol: bilgi paneli -->
    <div class="forgot-info">
      <div class="info-inner">
        <div class="info-icon">🔐</div>
        <h2>{$t.forgotPassword}</h2>
        <p>{$t.forgotPasswordDesc}</p>

        <div class="info-steps">
          <div class="info-step">
            <span class="step-num">1</span>
            <div>
              <b>{$t.usernamePlaceholder}</b>
              <p>Hesabına ait kullanıcı adını gir</p>
            </div>
          </div>
          <div class="info-step">
            <span class="step-num">2</span>
            <div>
              <b>{$t.ozelKodPlaceholder}</b>
              <p>Kayıt sırasında verilen 8 haneli kodunu gir</p>
            </div>
          </div>
          <div class="info-step">
            <span class="step-num">3</span>
            <div>
              <b>{$t.newPasswordPlaceholder}</b>
              <p>En az 6 karakter yeni şifreni belirle</p>
            </div>
          </div>
        </div>

        <button class="back-btn" onclick={goToLogin}>
          ← {$t.loginButton} {$t.loginWelcome}
        </button>
      </div>
    </div>

    <!-- Sağ: form -->
    <div class="forgot-form-wrap">
      {#if forgotSuccess}
        <!-- Başarı ekranı -->
        <div class="success-box">
          <div class="success-icon">✓</div>
          <h2>Şifre Başarıyla Değiştirildi!</h2>
          <p>{$t.passwordResetSuccess}</p>
          <button class="btn" onclick={goToLogin}>
            {$t.loginButton} →
          </button>
        </div>
      {:else}
        <div class="forgot-form-card">
          <div class="form-header">
            <h2>{$t.forgotPassword}</h2>
            <p class="sub">Kimliğini doğrula ve yeni şifreni belirle</p>
          </div>

          <form onsubmit={handleForgot}>

            <!-- Kullanıcı adı -->
            <div class="field-group">
              <label>Kullanıcı Adı</label>
              <div class="input-wrap">
                <span class="input-icon">👤</span>
                <input
                  type="text"
                  placeholder={$t.usernamePlaceholder}
                  bind:value={forgotLogin}
                  autocomplete="username"
                  required
                />
              </div>
            </div>

            <!-- Özel kod -->
            <div class="field-group">
              <label>{$t.ozelKodPlaceholder}</label>
              <div class="input-wrap">
                <span class="input-icon">🔑</span>
                <input
                  type="text"
                  placeholder="XXXXXXXX"
                  bind:value={forgotKod}
                  autocomplete="off"
                  style="letter-spacing: 4px; font-family: monospace; font-size: 18px;"
                  required
                />
              </div>
              <p class="field-hint">Kayıt olduğunda sana verilen 8 haneli kod</p>
            </div>

            <div class="divider"><span>Yeni Şifre</span></div>

            <!-- Yeni şifre -->
            <div class="field-group">
              <label>{$t.newPasswordPlaceholder}</label>
              <div class="input-wrap">
                <span class="input-icon">🔒</span>
                <input
                  type={showForgotPass ? 'text' : 'password'}
                  placeholder={$t.newPasswordPlaceholder}
                  bind:value={forgotNewPass}
                  autocomplete="new-password"
                  required
                />
                <button type="button" class="eye" onclick={() => showForgotPass = !showForgotPass}>
                  {showForgotPass ? '◉' : '○'}
                </button>
              </div>
            </div>

            <!-- Şifre tekrar -->
            <div class="field-group">
              <label>{$t.confirmPasswordPlaceholder}</label>
              <div class="input-wrap">
                <span class="input-icon">🔒</span>
                <input
                  type={showForgotPass ? 'text' : 'password'}
                  placeholder={$t.confirmPasswordPlaceholder}
                  bind:value={forgotConfirmPass}
                  autocomplete="new-password"
                  required
                />
              </div>
              {#if forgotNewPass && forgotConfirmPass && forgotNewPass !== forgotConfirmPass}
                <p class="field-error">⚠ Şifreler eşleşmiyor</p>
              {/if}
            </div>

            {#if forgotError}
              <div class="alert-err">
                <span>⚠</span> {forgotError}
              </div>
            {/if}

            <button type="submit" class="btn submit-btn" disabled={forgotLoading}>
              {#if forgotLoading}
                <span class="spinner"></span> {$t.loading}
              {:else}
                🔐 {$t.resetPassword}
              {/if}
            </button>
          </form>

          <div class="form-footer">
            <button class="link-btn" onclick={goToLogin}>← {$t.loginButton}</button>
          </div>
        </div>
      {/if}
    </div>

  </div>
</div>
{/if}

<style>
  /* ── Genel ── */
  .page { background:#050507; color:#fff; min-height:100vh; }

  .nav {
    padding:20px 48px;
    position:fixed; top:0; left:0; right:0; z-index:100;
    background:rgba(5,5,7,.9); backdrop-filter:blur(20px);
    border-bottom:1px solid rgba(255,255,255,.05);
    display:flex; align-items:center; justify-content:space-between;
  }
  .logo { font-size:20px; font-weight:700; background:linear-gradient(135deg,#fff,#94a3b8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }

  /* ── Login sayfası ── */
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

  input { width:100%; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.06); border-radius:12px; padding:14px 16px; font-size:15px; color:#fff; margin-bottom:0; transition:all .2s ease; box-sizing:border-box; }
  input:focus { border-color:rgba(59,130,246,.5); background:rgba(255,255,255,.06); outline:none; }
  input::placeholder { color:#3f3f46; }

  .pass-wrap { position:relative; margin-bottom:14px; }
  .pass-wrap input, .input-wrap input { margin-bottom:0; }
  .pass-wrap .eye { position:absolute; right:14px; top:50%; transform:translateY(-50%); background:none; border:none; color:#52525b; font-size:18px; cursor:pointer; transition:color .2s; padding:0; }
  .pass-wrap .eye:hover { color:#60a5fa; }

  .captcha-wrap { display:grid; grid-template-columns:110px 1fr; gap:12px; margin-bottom:14px; align-items:start; }
  .captcha { background:linear-gradient(145deg,#18181c,#1f1f24); border:1px solid rgba(255,255,255,.06); border-radius:12px; padding:14px 12px; text-align:center; font-size:22px; font-weight:800; letter-spacing:6px; color:#60a5fa; font-family:monospace; user-select:none; cursor:pointer; transition:opacity .2s; }
  .captcha:hover { opacity:.8; }
  .captcha-wrap input { margin-bottom:0; }

  .err { color:#f87171; font-size:13px; margin-bottom:14px; margin-top:4px; }

  .btn { width:100%; background:linear-gradient(135deg,#3b82f6,#2563eb); color:#fff; padding:16px; border-radius:12px; font-size:15px; font-weight:600; border:none; cursor:pointer; transition:all .3s ease; display:flex; align-items:center; justify-content:center; gap:8px; }
  .btn:hover:not(:disabled) { transform:translateY(-2px); box-shadow:0 12px 32px rgba(59,130,246,.35); }
  .btn:disabled { opacity:.7; cursor:not-allowed; }

  .foot { font-size:14px; color:#52525b; margin-top:16px; text-align:center; }
  .foot a, .link-btn { color:#60a5fa; text-decoration:none; transition:color .2s; background:none; border:none; cursor:pointer; font-size:14px; padding:0; }
  .foot a:hover, .link-btn:hover { color:#93c5fd; }

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

  /* ── Şifremi Unuttum Sayfası ── */
  .forgot-page { min-height:100vh; }

  .forgot-container {
    display:grid;
    grid-template-columns:1fr 1fr;
    min-height:100vh;
    padding-top:72px;
  }

  /* Sol panel */
  .forgot-info {
    background: linear-gradient(145deg, rgba(15,15,20,1), rgba(20,20,30,1));
    border-right: 1px solid rgba(255,255,255,.06);
    display:flex; align-items:center; justify-content:center;
    padding: 60px 48px;
  }

  .info-inner { max-width:380px; }

  .info-icon {
    font-size:56px;
    margin-bottom:24px;
    display:block;
  }

  .info-inner h2 { font-size:32px; font-weight:700; margin-bottom:12px; }
  .info-inner > p { font-size:16px; color:#71717a; line-height:1.7; margin-bottom:40px; }

  .info-steps { display:flex; flex-direction:column; gap:20px; margin-bottom:40px; }

  .info-step {
    display:flex; gap:16px; align-items:flex-start;
    padding:16px; border-radius:12px;
    background:rgba(255,255,255,.03);
    border:1px solid rgba(255,255,255,.05);
    transition:all .3s ease;
  }
  .info-step:hover { background:rgba(59,130,246,.06); border-color:rgba(59,130,246,.15); }

  .step-num {
    min-width:32px; height:32px;
    background:linear-gradient(135deg,#3b82f6,#2563eb);
    border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:14px; font-weight:700;
    flex-shrink:0;
  }

  .info-step b { display:block; font-size:14px; color:#e4e4e7; margin-bottom:4px; }
  .info-step p { font-size:13px; color:#52525b; margin:0; }

  .back-btn {
    background:rgba(255,255,255,.05);
    border:1px solid rgba(255,255,255,.08);
    color:#a1a1aa;
    padding:12px 24px;
    border-radius:10px;
    cursor:pointer;
    font-size:14px;
    transition:all .2s ease;
    width:100%;
  }
  .back-btn:hover { background:rgba(255,255,255,.08); color:#fff; }

  /* Sağ panel - form */
  .forgot-form-wrap {
    display:flex; align-items:center; justify-content:center;
    padding:60px 48px;
    background:#050507;
  }

  .forgot-form-card {
    width:100%; max-width:420px;
  }

  .form-header { margin-bottom:32px; }
  .form-header h2 { font-size:28px; font-weight:700; margin-bottom:8px; }
  .form-header .sub { font-size:14px; color:#52525b; }

  .field-group { margin-bottom:20px; }
  .field-group label { display:block; font-size:13px; font-weight:600; color:#a1a1aa; margin-bottom:8px; letter-spacing:.5px; text-transform:uppercase; }

  .input-wrap {
    position:relative;
    display:flex; align-items:center;
  }
  .input-wrap .input-icon {
    position:absolute; left:14px;
    font-size:16px;
    pointer-events:none;
    z-index:1;
  }
  .input-wrap input {
    padding-left:42px;
  }
  .input-wrap .eye {
    position:absolute; right:14px;
    background:none; border:none;
    color:#52525b; font-size:18px; cursor:pointer;
    transition:color .2s; padding:0;
    z-index:1;
  }
  .input-wrap .eye:hover { color:#60a5fa; }

  .field-hint { font-size:12px; color:#3f3f46; margin-top:6px; }
  .field-error { font-size:12px; color:#f87171; margin-top:6px; }

  .divider {
    display:flex; align-items:center; gap:12px;
    margin:24px 0;
  }
  .divider::before, .divider::after {
    content:''; flex:1;
    border-top:1px solid rgba(255,255,255,.06);
  }
  .divider span { font-size:12px; color:#3f3f46; font-weight:600; letter-spacing:1px; text-transform:uppercase; white-space:nowrap; }

  .alert-err {
    background:rgba(239,68,68,.1);
    border:1px solid rgba(239,68,68,.2);
    border-radius:10px;
    padding:12px 16px;
    font-size:14px;
    color:#fca5a5;
    margin-bottom:20px;
    display:flex; gap:8px; align-items:center;
  }

  .submit-btn { margin-top:8px; padding:17px; font-size:16px; }

  .spinner {
    width:16px; height:16px;
    border:2px solid rgba(255,255,255,.3);
    border-top-color:#fff;
    border-radius:50%;
    animation:spin .7s linear infinite;
    display:inline-block;
  }
  @keyframes spin { to { transform:rotate(360deg); } }

  .form-footer {
    margin-top:24px;
    text-align:center;
    padding-top:20px;
    border-top:1px solid rgba(255,255,255,.05);
  }

  /* Başarı ekranı */
  .success-box {
    width:100%; max-width:420px;
    text-align:center;
    padding:48px 32px;
    background:rgba(12,12,15,.8);
    border:1px solid rgba(34,197,94,.15);
    border-radius:24px;
  }
  .success-icon {
    width:80px; height:80px;
    background:linear-gradient(135deg,#22c55e,#16a34a);
    border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:40px;
    margin:0 auto 24px;
    box-shadow:0 0 40px rgba(34,197,94,.3);
  }
  .success-box h2 { font-size:24px; margin-bottom:12px; color:#4ade80; }
  .success-box p { color:#71717a; font-size:15px; margin-bottom:32px; }
  .success-box .btn { max-width:200px; margin:0 auto; }

  /* ── Responsive ── */
  @media (max-width:900px) {
    .hero { grid-template-columns:1fr; gap:60px; padding:120px 24px 80px; text-align:center; }
    .content p { margin:0 auto; }
    .content h1 { font-size:40px; }
    .grid { grid-template-columns:1fr; }
    .steps { flex-direction:column; }
    .arrow { transform:rotate(90deg); }
    .who { grid-template-columns:1fr; }
    .features, .how { padding:80px 24px; }

    .forgot-container { grid-template-columns:1fr; }
    .forgot-info { display:none; }
    .forgot-form-wrap { padding:40px 24px; }
  }
</style>
