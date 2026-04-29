<script>
  import { onMount } from 'svelte';
  import { apiUrl } from '../stores/auth.js';
  import LanguageSelector from '../components/LanguageSelector.svelte';

  import { t, currentLang } from '../stores/i18n.js';
  let { goToLogin = () => {} } = $props();

  let role         = $state(null);
  let step         = $state(1);
  let ad           = $state('');
  let soyad        = $state('');
  let loginName    = $state('');   // user picks their own login name
  let password     = $state('');
  let confirmPass  = $state('');
  let hocaKodu     = $state('');
  let captcha      = $state('ABCDE');
  let userCaptcha  = $state('');
  let showPassword = $state(false);
  let error        = $state('');
  let loading      = $state(false);
  let ozelKod      = $state('');
  let formKey      = $state(0);
  let sections     = $state({ main: false, features: false, footer: false });
  let usernameCheck = $state({ checked: false, available: false, reason: '' });
  let passwordStrength = $state({ score: 0, text: '' });
  let checkTimeout    = $state(null);

  function generateCaptcha() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    captcha = Array.from({ length: 5 }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
  }

  function handleScroll() {
    const wh = window.innerHeight;
    const selectors = { main: '.main', features: '.features', footer: 'footer' };
    Object.entries(selectors).forEach(([k, s]) => {
      const el = document.querySelector(s);
      if (el && el.getBoundingClientRect().top < wh * 0.9) sections[k] = true;
    });
  }

  function goToStep(newStep, roleVal = null) {
    if (roleVal) role = roleVal;
    formKey++;
    step = newStep;
    if (newStep === 1) {
      setTimeout(() => { sections.main = true; }, 50);
    }
  }

  async function checkUsername() {
    if (!loginName || loginName.length < 3) {
      usernameCheck = { checked: false, available: false, reason: '' };
      return;
    }
    try {
      const lang = $currentLang;
      const res = await fetch(apiUrl + '/auth/check-username/' + loginName.trim().toLowerCase() + '?lang=' + lang);
      const data = await res.json();
      usernameCheck = { checked: true, available: data.available, reason: data.reason, message: data.message };
    } catch {
      usernameCheck = { checked: false, available: false, reason: '' };
    }
  }

  function onUsernameInput(e) {
    loginName = e.target.value;
    if (checkTimeout) clearTimeout(checkTimeout);
    checkTimeout = setTimeout(checkUsername, 400);
  }

  function checkPasswordStrength(pass) {
    let score = 0;
    if (!pass) { passwordStrength = { score: 0, text: '' }; return; }
    if (pass.length >= 6) score++;
    if (pass.length >= 8) score++;
    if (/[a-z]/.test(pass) && /[A-Z]/.test(pass)) score++;
    if (/[0-9]/.test(pass)) score++;
    if (/[^a-zA-Z0-9]/.test(pass)) score++;
    
    const texts = ['', 'Çok zayıf', 'Zayıf', 'Orta', 'İyi', 'Güçlü', 'Çok güçlü'];
    passwordStrength = { score, text: texts[score] };
  }

  function onPasswordInput(e) {
    password = e.target.value;
    checkPasswordStrength(password);
  }

  async function handleSubmit() {
    error = '';
    if (userCaptcha.toUpperCase() !== captcha) { error = $t.registerErrorCaptcha; generateCaptcha(); return; }
    if (password !== confirmPass) { error = $t.registerErrorPasswordMismatch; return; }
    if (password.length < 6) { error = $t.registerErrorPasswordLength; return; }
    if (!loginName.trim()) { error = $t.registerErrorUsernameEmpty; return; }
    if (loginName.length < 3) { error = $t.registerErrorUsernameLength; return; }
    if (!/^[a-zA-Z0-9_]+$/.test(loginName)) { error = $t.registerErrorUsernameInvalid; return; }

    loading = true;
    try {
      const payload = {
        login:     loginName.trim().toLowerCase(),
        password,
        ad:        ad.trim(),
        soyad:     soyad.trim(),
        role,
        hoca_kodu: role === 'student' ? hocaKodu.trim().toUpperCase() : null,
      };
      const res  = await fetch(apiUrl + '/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.ozel_kod) {
        ozelKod = data.ozel_kod;
        goToStep(3);
      } else {
        error = data.detail || $t.registerFailed;
        generateCaptcha();
      }
    } catch {
      error = $t.serverError;
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
    <button class="back" onclick={goToLogin}>← {$t.back}</button>
    <div class="logo">◎ <span>AiTech</span></div>
    <LanguageSelector />
  </nav>

  <main class="main" class:visible={sections.main}>
    {#key formKey}
      <div class="form-wrapper">
        {#if step === 1}
          <div class="form-content">
            <h1>{$t.createAccount}</h1>
            <p class="sub">{$t.registerSubtitle}</p>
            <div class="roles">
              <button class="role" onclick={() => goToStep(2, 'teacher')}>
                <span>👨‍🏫</span>
                <div><b>{$t.roleTeacher}</b><p>{$t.roleTeacherDesc}</p></div>
              </button>
              <button class="role" onclick={() => goToStep(2, 'student')}>
                <span>🎓</span>
                <div><b>{$t.roleStudent}</b><p>{$t.roleStudentDesc}</p></div>
              </button>
            </div>
          </div>

        {:else if step === 2}
          <div class="form-content">
            <button class="back-link" onclick={() => goToStep(1)}>← {$t.backToRole}</button>
            <h1>{role === 'teacher' ? $t.teacherRegisterTitle : $t.studentRegisterTitle}</h1>
            <p class="sub">{$t.registerStepSubtitle}</p>

            <form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
              <div class="row">
                <input type="text" placeholder={$t.namePlaceholder} bind:value={ad} required />
                <input type="text" placeholder={$t.surnamePlaceholder} bind:value={soyad} required />
              </div>

              <input type="text" placeholder={$t.usernameFullPlaceholder} bind:value={loginName} oninput={onUsernameInput} autocomplete="username" required />
              {#if usernameCheck.checked}
                <p class="input-feedback" class:ok={usernameCheck.available} class:err={!usernameCheck.available}>
                  {usernameCheck.message || (usernameCheck.available ? $t.usernameAvailable : usernameCheck.reason === 'taken' ? $t.usernameTaken : usernameCheck.reason === 'only_numbers' ? $t.usernameOnlyNumbers : usernameCheck.reason === 'short' ? $t.usernameTooShort : $t.usernameInvalidChars)}
                </p>
              {/if}

              <input type={showPassword ? 'text' : 'password'} placeholder={$t.passwordFullPlaceholder} bind:value={password} oninput={onPasswordInput} autocomplete="new-password" required />
              {#if passwordStrength.score > 0}
                <p class="input-feedback" class:ok={passwordStrength.score >= 3} class:err={passwordStrength.score < 3}>
                  {$t.passwordStrength}{passwordStrength.score === 1 ? $t.passwordVeryWeak : passwordStrength.score === 2 ? $t.passwordWeak : passwordStrength.score === 3 ? $t.passwordMedium : passwordStrength.score === 4 ? $t.passwordGood : passwordStrength.score === 5 ? $t.passwordStrong : $t.passwordVeryStrong}
                </p>
              {/if}
              <input type={showPassword ? 'text' : 'password'} placeholder={$t.confirmPasswordPlaceholder} bind:value={confirmPass} autocomplete="new-password" required />



              <div class="captcha-wrap">
                <button type="button" class="captcha" onclick={generateCaptcha} title={$t.captchaRefreshTitle}>{captcha}</button>
                <input type="text" placeholder={$t.captchaPlaceholder} bind:value={userCaptcha} maxlength="5" required />
              </div>

              <button type="button" class="pass-btn" onclick={() => showPassword = !showPassword}>
                {showPassword ? $t.showPasswordHide : $t.showPasswordShow}
              </button>

              {#if error}<p class="err">{error}</p>{/if}

              <button type="submit" class="btn" disabled={loading}>
                {loading ? $t.registerLoading : $t.registerTitle}
              </button>
            </form>
          </div>

        {:else if step === 3}
          <div class="form-content">
            <div class="success">
              <div class="check">✓</div>
              <h1>{$t.registerSuccessTitle}</h1>
              <p class="sub">{$t.registerSuccessSubtitle}</p>

              <div class="kod-box">
                <p class="label">{$t.specialCodeLabel}</p>
                <p class="kod">{ozelKod}</p>
                <p class="desc">{$t.specialCodeDesc}</p>
              </div>

              <button class="btn" onclick={goToLogin}>{$t.loginButton} →</button>
            </div>
          </div>
        {/if}
      </div>
    {/key}
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

  <footer class:visible={sections.footer}>
    <div class="logo">◎ <span>AiTech</span></div>
    <p>{$t.footerText}</p>
  </footer>
</div>

<style>
  .page { background:#050507; color:#fff; min-height:100vh; }
  .nav { padding:20px 30px; position:fixed; top:0; left:0; right:0; z-index:100; background:rgba(5,5,7,.85); backdrop-filter:blur(20px); border-bottom:1px solid rgba(255,255,255,.04); display:flex; align-items:center; gap:16px; }
  .back { background:none; border:none; color:#71717a; font-size:15px; cursor:pointer; transition:color .2s; }
  .back:hover { color:#fff; }
  .logo { font-size:20px; font-weight:700; background:linear-gradient(135deg,#fff,#94a3b8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }

  .main { max-width:440px; margin:0 auto; padding:100px 24px 80px; opacity:0; transform:translateY(40px); transition:all 1s cubic-bezier(.16,1,.3,1); }
  .main.visible { opacity:1; transform:translateY(0); }

  .form-content { animation:stepIn .5s cubic-bezier(.16,1,.3,1); }
  @keyframes stepIn { from { opacity:0; transform:translateX(30px); } to { opacity:1; transform:translateX(0); } }

  h1 { font-size:30px; font-weight:700; margin-bottom:8px; }
  .sub { color:#71717a; margin-bottom:32px; font-size:14px; }

  .roles { display:flex; flex-direction:column; gap:14px; }
  .role { background:rgba(20,20,24,.8); border:1px solid rgba(255,255,255,.06); border-radius:16px; padding:24px; display:flex; align-items:center; gap:18px; text-align:left; width:100%; cursor:pointer; transition:all .4s cubic-bezier(.16,1,.3,1); }
  .role:hover { transform:translateY(-4px); border-color:rgba(255,255,255,.12); background:rgba(30,30,38,.9); }
  .role span { font-size:36px; }
  .role b { display:block; font-size:18px; transition:color .2s; }
  .role:hover b { color:#60a5fa; }
  .role p { font-size:14px; color:#71717a; margin:0; }

  .row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  input { width:100%; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.06); border-radius:12px; padding:14px 16px; font-size:15px; color:#fff; margin-bottom:12px; transition:all .25s ease; box-sizing:border-box; }
  input:focus { border-color:rgba(59,130,246,.5); background:rgba(255,255,255,.06); outline:none; }
  input::placeholder { color:#3f3f46; }

  .captcha-wrap { display:grid; grid-template-columns:110px 1fr; gap:12px; margin-bottom:12px; align-items:start; }
  .captcha { background:linear-gradient(145deg,#18181c,#1f1f24); border:1px solid rgba(255,255,255,.06); border-radius:12px; padding:14px 12px; text-align:center; font-size:20px; font-weight:800; letter-spacing:6px; color:#60a5fa; font-family:monospace; user-select:none; cursor:pointer; transition:opacity .2s; }
  .captcha:hover { opacity:.8; }

  .pass-btn { background:none; border:none; color:#71717a; font-size:14px; margin-bottom:16px; cursor:pointer; transition:color .2s; }
  .pass-btn:hover { color:#60a5fa; }

  .err { color:#ef4444; font-size:13px; margin-bottom:14px; }

  .input-feedback { font-size:12px; margin-top:-8px; margin-bottom:10px; padding:4px 0; }
  .input-feedback.ok { color:#22c55e; }
  .input-feedback.err { color:#ef4444; }

  .btn { width:100%; background:linear-gradient(135deg,#3b82f6,#2563eb); color:#fff; padding:16px; border-radius:12px; font-size:15px; font-weight:600; border:none; cursor:pointer; transition:all .3s ease; }
  .btn:hover:not(:disabled) { transform:translateY(-2px); box-shadow:0 12px 32px rgba(59,130,246,.35); }
  .btn:disabled { opacity:.7; cursor:not-allowed; }

  .back-link { background:none; border:none; color:#71717a; font-size:14px; margin-bottom:16px; display:block; cursor:pointer; transition:color .2s; }
  .back-link:hover { color:#fff; }

  .success { text-align:center; }
  .check { width:72px; height:72px; background:linear-gradient(135deg,#22c55e,#16a34a); border-radius:50%; font-size:36px; display:flex; align-items:center; justify-content:center; margin:0 auto 24px; animation:popIn .6s cubic-bezier(.16,1,.3,1); }
  @keyframes popIn { 0% { transform:scale(0); } 60% { transform:scale(1.15); } 100% { transform:scale(1); } }

  .kod-box { background:rgba(20,20,24,.8); border:1px solid rgba(59,130,246,.2); border-radius:16px; padding:28px; margin:28px 0; }
  .label { font-size:13px; color:#71717a; margin-bottom:12px; }
  .kod { font-size:32px; font-weight:700; letter-spacing:6px; color:#60a5fa; font-family:monospace; }
  .desc { font-size:13px; color:#52525b; margin-top:12px; }

  .features { padding:80px 24px; max-width:800px; margin:0 auto; opacity:0; transform:translateY(50px); transition:all 1s cubic-bezier(.16,1,.3,1); }
  .features.visible { opacity:1; transform:translateY(0); }
  .features h2 { font-size:32px; text-align:center; margin-bottom:32px; }
  .grid { display:grid; grid-template-columns:repeat(2,1fr); gap:16px; }
  .card { background:rgba(20,20,24,.6); border-radius:16px; padding:24px; transition:all .4s ease; }
  .card:hover { transform:translateY(-6px); }
  .card h3 { font-size:18px; margin:14px 0 8px; }
  .card p { font-size:14px; color:#71717a; }

  footer { padding:50px 24px; text-align:center; opacity:0; transform:translateY(30px); transition:all .8s ease; }
  footer.visible { opacity:1; transform:translateY(0); }
  footer .logo { font-size:20px; font-weight:700; margin-bottom:12px; background:linear-gradient(135deg,#fff,#94a3b8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  footer p { color:#52525b; font-size:14px; }

  @media (max-width:500px) { .grid { grid-template-columns:1fr; } .row { grid-template-columns:1fr; } }
</style>
