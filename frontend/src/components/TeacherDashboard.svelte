<script>
import { onMount } from 'svelte';
  import { apiUrl, authFetch } from '../stores/auth.js';
  import LanguageSelector from '../components/LanguageSelector.svelte';
  import { t } from '../stores/i18n.js';

  let { handleLogout = () => {}, user = {} } = $props();

  let activeTab    = $state('lessons');
  let lessons      = $state([]);
  let students    = $state([]);
  let filteredStudents = $state([]);
  let notifications = $state([]);
  let stats        = $state({ ogrenci_sayisi: 0, ders_sayisi: 0, soru_sayisi: 0, hoca_kodu: '' });
  let loadingData  = $state(true);

  let studentSearch = $state('');

  $effect(() => {
    if (studentSearch.trim() === '') {
      filteredStudents = students;
    } else {
      const q = studentSearch.toLowerCase();
      filteredStudents = students.filter(s => 
        s.ad.toLowerCase().includes(q) || s.soyad.toLowerCase().includes(q)
      );
    }
  });

  // Add lesson form
  let showAddLesson   = $state(false);
  let newLessonTema   = $state('');
  let newLessonIcerik = $state('');
  let savingLesson    = $state(false);

  // Delete confirm
  let confirmDelete = $state(null);   // lesson.id
  let confirmDeleteStudent = $state(null);   // ogrenci_id

  // Edit lesson
  let editingLesson = $state(null);   // lesson object
  let editTema = $state('');
  let editIcerik = $state('');
  let savingEdit = $state(false);

  // Attention detail
  let selectedNotif     = $state(null);
  let breakdown         = $state(null);   // { tema, ogrenciler[] }
  let loadingBreakdown  = $state(false);
  let expandedStudent   = $state(null);   // ogrenci_id

  async function loadBreakdown(dersId) {
    loadingBreakdown = true;
    breakdown = null;
    expandedStudent = null;
    try {
      const res  = await authFetch(apiUrl + '/teacher/breakdown/' + dersId);
      const data = await res.json();
      breakdown = data;
    } catch { breakdown = null; }
    finally { loadingBreakdown = false; }
  }

  // AI chat
  let aiMessages = $state([
    { role: 'assistant', content: $t.aiAssistantWelcome }
  ]);
  let aiInput   = $state('');
  let aiLoading = $state(false);

  let unreadCount   = $derived(notifications.filter(n => !n.goruldu).length);
  let attentionList = $derived(notifications.filter(n => n.yuzde >= 15));

  let copySuccess = $state(false);

  // ── Data loading ────────────────────────────────────────────────────────────
  async function loadAll() {
    loadingData = true;
    await Promise.all([loadLessons(), loadNotifications(), loadStats(), loadStudents()]);
    loadingData = false;
  }

  async function loadLessons() {
    try {
      const res  = await authFetch(apiUrl + '/lessons');
      const data = await res.json();
      if (data.lessons) lessons = data.lessons;
    } catch { /* keep existing */ }
  }

  async function loadStudents() {
    try {
      const res  = await authFetch(apiUrl + '/teacher/students');
      const data = await res.json();
      if (data.students) {
        students = data.students;
        filteredStudents = data.students;
      }
    } catch { /* keep existing */ }
  }

  async function loadNotifications() {
    try {
      const res  = await authFetch(apiUrl + '/notifications');
      const data = await res.json();
      if (data.notifications) notifications = data.notifications;
    } catch {}
  }

  async function loadStats() {
    try {
      const res  = await authFetch(apiUrl + '/teacher/stats');
      if (!res.ok) {
        console.error('Stats API error:', res.status, await res.text());
        return;
      }
      const data = await res.json();
      console.log('Stats loaded:', data);
      stats = { ...stats, ...data };
    } catch (e) {
      console.error('loadStats failed:', e);
    }
  }

  // ── Lesson actions ──────────────────────────────────────────────────────────
  async function addLesson() {
    if (!newLessonTema.trim()) return;
    savingLesson = true;
    try {
      const res = await authFetch(apiUrl + '/lessons', {
        method: 'POST',
        body: JSON.stringify({ tema: newLessonTema.trim(), icerik: newLessonIcerik.trim() || null }),
      });
      if (res.ok) {
        newLessonTema = ''; newLessonIcerik = ''; showAddLesson = false;
        await loadLessons();
      }
    } finally { savingLesson = false; }
  }

  async function deleteLesson(id) {
    try {
      await authFetch(apiUrl + '/lessons/' + id, { method: 'DELETE' });
      lessons = lessons.filter(l => l.id !== id);
      confirmDelete = null;
    } catch {}
  }

  async function deleteStudent(id) {
    try {
      await authFetch(apiUrl + '/teacher/students/' + id, { method: 'DELETE' });
      students = students.filter(s => s.id !== id);
      confirmDeleteStudent = null;
    } catch {}
  }

  function startEdit(lesson) {
    editingLesson = lesson;
    editTema = lesson.tema;
    editIcerik = lesson.icerik || '';
  }

  async function saveEdit() {
    if (!editTema.trim()) return;
    savingEdit = true;
    try {
      const res = await authFetch(apiUrl + '/lessons/' + editingLesson.id, {
        method: 'PUT',
        body: JSON.stringify({ tema: editTema.trim(), icerik: editIcerik.trim() || null }),
      });
      if (res.ok) {
        lessons = lessons.map(l => l.id === editingLesson.id ? { ...l, tema: editTema.trim(), icerik: editIcerik.trim() || null } : l);
        editingLesson = null;
      }
    } finally { savingEdit = false; }
  }

  // ── Notifications ───────────────────────────────────────────────────────────
  async function markRead(id) {
    try {
      await authFetch(apiUrl + '/notifications/' + id + '/read', { method: 'PATCH' });
      notifications = notifications.map(n => n.id === id ? { ...n, goruldu: true } : n);
    } catch {}
  }

  // ── AI Chat ─────────────────────────────────────────────────────────────────
  async function sendAiMessage() {
    if (!aiInput.trim()) return;
    const msg = aiInput.trim();
    aiMessages = [...aiMessages, { role: 'user', content: msg }];
    aiInput = '';
    aiLoading = true;

    try {
      const res  = await authFetch(apiUrl + '/teacher/ai', {
        method: 'POST',
        body: JSON.stringify({ message: msg }),
      });
      const data = await res.json();
      aiMessages = [...aiMessages, { role: 'assistant', content: data.cevap || $t.error }];
    } catch {
      aiMessages = [...aiMessages, { role: 'assistant', content: $t.serverError }];
    } finally {
      aiLoading = false;
      setTimeout(scrollAiToBottom, 50);
    }
  }

  function scrollAiToBottom() {
    const box = document.querySelector('.ai-messages');
    if (box) box.scrollTop = box.scrollHeight;
  }

  function copyCode() {
    const kod = stats.hoca_kodu || '';
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(kod);
    } else {
      // HTTP fallback
      const el = document.createElement('textarea');
      el.value = kod;
      el.style.position = 'fixed';
      el.style.opacity = '0';
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
    }
    copySuccess = true;
    setTimeout(() => copySuccess = false, 2000);
  }

  function handleAiKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendAiMessage(); }
  }

  onMount(() => {
    loadAll();
    const interval = setInterval(loadStats, 5000);
    return () => clearInterval(interval);
  });
</script>

<div class="page">
  <nav class="nav">
    <div class="nav-left">
      <span class="logo">◎ AiTech</span>
      {#if stats.hoca_kodu}
        <button class="code-btn" onclick={copyCode} title={$t.enterCode}>
          {#if copySuccess}{$t.copied}{:else}{$t.copyCodeButtonPrefix} {stats.hoca_kodu}{/if}
        </button>
      {/if}
    </div>
    <div class="nav-right">
      <div class="stat-pill">👨‍🎓 {stats.ogrenci_sayisi} {$t.students}</div>
      <div class="stat-pill">📚 {stats.ders_sayisi} {$t.lessons}</div>
      <span class="role-badge">{$t.roleTeacher}</span>
      <span class="user-name">{user?.ad} {user?.soyad}</span>
      <LanguageSelector />
      <button class="logout-btn" onclick={handleLogout}>{$t.logout}</button>
    </div>
  </nav>

  <div class="layout">
    <!-- LEFT: Main content -->
    <main class="main-content">
      <div class="tabs">
        <button class="tab-btn" class:active={activeTab === 'lessons'} onclick={() => activeTab = 'lessons'}>
          📚 {$t.lessons} {#if lessons.length}<span class="count">{lessons.length}</span>{/if}
        </button>
        <button class="tab-btn" class:active={activeTab === 'students'} onclick={() => activeTab = 'students'}>
          👨‍🎓 {$t.teacherDashboardStudents} {#if students.length}<span class="count">{students.length}</span>{/if}
        </button>
        <button class="tab-btn" class:active={activeTab === 'attention'} onclick={() => activeTab = 'attention'}>
          ⚠️ {$t.attention} {#if attentionList.length}<span class="count warn">{attentionList.length}</span>{/if}
        </button>
        <button class="tab-btn" class:active={activeTab === 'notifs'} onclick={() => { activeTab = 'notifs'; }}>
          🔔 {$t.notifications} {#if unreadCount}<span class="count alert">{unreadCount}</span>{/if}
        </button>
      </div>

      <div class="content">
        <!-- LESSONS TAB -->
        {#if activeTab === 'lessons'}
          <div class="section-header">
            <h2>{$t.teacherDashboardAllLessons}</h2>
            <button class="add-btn" onclick={() => showAddLesson = !showAddLesson}>
              {showAddLesson ? $t.teacherDashboardAddLessonClose : $t.teacherDashboardAddLesson}
            </button>
          </div>

          {#if showAddLesson}
            <div class="add-form">
              <input type="text" placeholder={$t.teacherDashboardLessonTopicPlaceholder} bind:value={newLessonTema} />
              <textarea placeholder={$t.teacherDashboardLessonContentPlaceholder} bind:value={newLessonIcerik}></textarea>
              <button class="btn-save" onclick={addLesson} disabled={!newLessonTema.trim() || savingLesson}>
                {savingLesson ? $t.teacherDashboardLessonSaving : $t.teacherDashboardLessonSave}
              </button>
            </div>
          {/if}

          {#if loadingData}
            <div class="empty">{$t.loading}</div>
          {:else if lessons.length === 0}
            <div class="empty">{$t.teacherDashboardNoLessons}</div>
          {:else}
            <div class="cards">
              {#each lessons as lesson, i}
                <div class="card" style="animation-delay:{i*0.04}s">
                  <div class="card-header">
                    <div class="card-info">
                      <h3>{lesson.tema}</h3>
                      {#if lesson.icerik}
                        <p class="card-desc">{lesson.icerik}</p>
                      {/if}
                      <div class="card-meta">
                        <span class="date">{new Date(lesson.olusturma_tarihi).toLocaleDateString()}</span>
                        <span class="soru-count">💬 {lesson.toplam_soru} {$t.questions}</span>
                        {#if lesson.anlamadi_yuzde >= 15}
                          <span class="warn-badge">⚠️ %{lesson.anlamadi_yuzde} {$t.notUnderstood}</span>
                        {/if}
                      </div>
                    </div>
                    <div class="card-actions">
                      <button class="edit-btn" onclick={() => startEdit(lesson)} title={$t.edit}>✏️</button>
                      {#if confirmDelete === lesson.id}
                        <div class="confirm-inline">
                          <span>{$t.teacherDashboardDeleteConfirm}</span>
                          <button class="btn-yes" onclick={() => deleteLesson(lesson.id)}>{$t.teacherDashboardDeleteYes}</button>
                          <button class="btn-no" onclick={() => confirmDelete = null}>{$t.teacherDashboardDeleteNo}</button>
                        </div>
                      {:else}
                        <button class="del-btn" onclick={() => confirmDelete = lesson.id} title={$t.delete}>🗑️</button>
                      {/if}
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          {/if}

        <!-- ATTENTION TAB -->
        {:else if activeTab === 'attention'}
          {#if breakdown}
            <!-- BREAKDOWN: per-student detail for one lesson -->
            <div class="section-header">
              <div>
                <button class="back-btn" onclick={() => { breakdown = null; selectedNotif = null; }}>← {$t.back}</button>
                <h2 style="margin-top:8px">{breakdown.tema}</h2>
              </div>
            </div>

            {#if breakdown.ogrenciler.length === 0}
              <div class="empty">{$t.noData}</div>
            {:else}
              <!-- Summary bar -->
              {@const topAnlamadi = breakdown.ogrenciler.filter(o => o.anlamadi > 0).length}
              {@const topAnladi   = breakdown.ogrenciler.filter(o => o.anlamadi === 0 && o.anladi > 0).length}
              <div class="summary-bar">
                <div class="sum-item red">
                  <span class="sum-num">{topAnlamadi}</span>
                  <span class="sum-label">{$t.notUnderstood}</span>
                </div>
                <div class="sum-item green">
                  <span class="sum-num">{topAnladi}</span>
                  <span class="sum-label">{$t.understood}</span>
                </div>
                <div class="sum-item gray">
                  <span class="sum-num">{breakdown.ogrenciler.length}</span>
                  <span class="sum-label">{$t.history}</span>
                </div>
              </div>

              <!-- Per-student rows -->
              <div class="student-rows">
                {#each breakdown.ogrenciler as ogr}
                  <div class="student-row" class:expanded={expandedStudent === ogr.ogrenci_id}>
                    <button class="student-header" onclick={() => expandedStudent = expandedStudent === ogr.ogrenci_id ? null : ogr.ogrenci_id}>
                      <div class="stu-left">
                        <div class="stu-avatar" class:red={ogr.anlamadi > 0} class:green={ogr.anlamadi === 0 && ogr.anladi > 0}>
                          {ogr.ad[0]}{ogr.soyad[0]}
                        </div>
                        <div class="stu-info">
                          <span class="stu-name">{ogr.ad} {ogr.soyad}</span>
                          <span class="stu-meta">{ogr.toplam_soru} {$t.questions} {$t.history}</span>
                        </div>
                      </div>
                      <div class="stu-right">
                        {#if ogr.anlamadi > 0}
                          <span class="badge-red">✗ {ogr.anlamadi} {$t.notUnderstood}</span>
                        {/if}
                        {#if ogr.anladi > 0}
                          <span class="badge-green">✓ {ogr.anladi} {$t.understood}</span>
                        {/if}
                        <span class="chevron">{expandedStudent === ogr.ogrenci_id ? '▲' : '▼'}</span>
                      </div>
                    </button>

                    {#if expandedStudent === ogr.ogrenci_id}
                      <div class="stu-questions">
                        {#each ogr.sorular as s}
                          <div class="stu-q" class:q-anlamadi={s.anladi_mi === false} class:q-anladi={s.anladi_mi === true}>
                            <div class="q-text">💬 {s.soru}</div>
                            <div class="q-meta">
                              {#if s.anladi_mi === true}
                                <span class="tag green">✓ {$t.understood}</span>
                              {:else if s.anladi_mi === false}
                                <span class="tag red">✗ {$t.notUnderstood}</span>
                              {:else}
                                <span class="tag gray">— {$t.loading}</span>
                              {/if}
                              {#if s.ai_tahmin}
                                <span class="tag ai">🤖 {$t.aiAssistant}</span>
                              {/if}
                              <span class="q-time">{new Date(s.timestamp).toLocaleString('tr-TR')}</span>
                            </div>
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}

          {:else}
            <!-- LESSON LIST for attention tab -->
            <h2>{$t.teacherDashboardAttentionTitle}</h2>
            <p class="hint">{$t.teacherDashboardAttentionHint}</p>

            {#if loadingData}
              <div class="empty">{$t.loading}</div>
            {:else if lessons.length === 0}
              <div class="empty">{$t.teacherDashboardNoAttentionLessons}</div>
            {:else}
              <div class="attention-lessons">
                {#each lessons as lesson}
                  <button class="att-lesson-card" class:has-warn={lesson.anlamadi_yuzde >= 15} onclick={() => loadBreakdown(lesson.id)}>
                    <div class="att-left">
                      <h3>{lesson.tema}</h3>
                      <div class="att-meta">
                        <span>💬 {lesson.toplam_soru} {$t.questions}</span>
                      </div>
                    </div>
                    <div class="att-right">
                      {#if lesson.anlamadi_yuzde >= 15}
                        <div class="att-percent warn">%{lesson.anlamadi_yuzde}<span>{$t.notUnderstood}</span></div>
                      {:else if lesson.anlamadi_yuzde > 0}
                        <div class="att-percent ok">%{lesson.anlamadi_yuzde}<span>{$t.notUnderstood}</span></div>
                      {:else}
                        <div class="att-percent none">—</div>
                      {/if}
                      <span class="att-arrow">→</span>
                    </div>
                  </button>
                {/each}
              </div>
            {/if}
          {/if}

        <!-- NOTIFICATIONS TAB -->
        {:else if activeTab === 'notifs'}
          <h2>{$t.notifications}</h2>
          <p class="hint">{$t.history}</p>

          {#if notifications.length === 0}
            <div class="empty">{$t.teacherDashboardNoNotifications}</div>
          {:else}
            <div class="notif-cards">
              {#each notifications as notif}
                <div class="notif-card" class:unread={!notif.goruldu} class:urgent={notif.yuzde >= 30}>
                  <div class="notif-main">
                    <span class="notif-konu">{notif.konu}</span>
                    <span class="notif-desc">%{notif.yuzde} {$t.students} {$t.notUnderstood}</span>
                    <span class="notif-time">{new Date(notif.timestamp).toLocaleString()}</span>
                  </div>
                  {#if !notif.goruldu}
                    <button class="btn-okudum" onclick={() => markRead(notif.id)}>{$t.understood}</button>
                  {:else}
                    <span class="read-label">{$t.copyCodeSuccess}</span>
                  {/if}
                </div>
              {/each}
            </div>
          {/if}
        {/if}

        {#if activeTab === 'students'}
          <h2>{$t.teacherDashboardStudents}</h2>
          <p class="hint">{$t.history}</p>

          {#if loadingData}
            <div class="empty">{$t.loading}</div>
          {:else if students.length === 0}
            <div class="empty">{$t.teacherDashboardNoStudents}</div>
          {:else}
            <div class="search-bar">
              <input
                type="text"
                placeholder={$t.searchStudent}
                bind:value={studentSearch}
              />
            </div>
            <div class="student-cards">
              {#each filteredStudents as student}
                <div class="student-card">
                  <div class="student-info">
                    <div class="student-avatar">
                      {student.ad[0]}{student.soyad[0]}
                    </div>
                    <div class="student-details">
                      <span class="student-name">{student.ad} {student.soyad}</span>
                      <span class="student-meta">{student.telefon || ''}</span>
                      <div class="student-stats">
                        <span class="stat-item">💬 {student.toplam_soru} {$t.teacherDashboardTotalQuestions}</span>
                        {#if student.anlamadi_sayi > 0}
                          <span class="stat-item warn">⚠️ {student.anlamadi_sayi} {$t.teacherDashboardNotUnderstood}</span>
                        {/if}
                      </div>
                      {#if student.kayit_tarihi}
                        <span class="student-date">{new Date(student.kayit_tarihi).toLocaleDateString()}</span>
                      {/if}
                    </div>
                  </div>
                  <div class="student-actions">
                    {#if confirmDeleteStudent === student.id}
                      <div class="confirm-inline">
                        <span>{$t.teacherDashboardStudentDeleteConfirm}</span>
                        <button class="btn-yes" onclick={() => deleteStudent(student.id)}>{$t.teacherDashboardStudentDeleteYes}</button>
                        <button class="btn-no" onclick={() => confirmDeleteStudent = null}>{$t.teacherDashboardStudentDeleteNo}</button>
                      </div>
                    {:else}
                      <button class="del-btn" onclick={() => confirmDeleteStudent = student.id} title={$t.delete}>🗑️</button>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        {/if}
      </div>

      {#if editingLesson}
        <div class="modal-overlay" onclick={() => editingLesson = null}>
          <div class="modal" onclick={(e) => e.stopPropagation()}>
            <h3>{$t.teacherDashboardEditLesson}</h3>
            <input type="text" placeholder={$t.teacherDashboardLessonTopicPlaceholder} bind:value={editTema} />
            <textarea placeholder={$t.teacherDashboardLessonContentPlaceholder} bind:value={editIcerik}></textarea>
            <div class="modal-actions">
              <button class="btn-cancel" onclick={() => editingLesson = null}>{$t.cancel}</button>
              <button class="btn-save" onclick={saveEdit} disabled={!editTema.trim() || savingEdit}>
                {savingEdit ? $t.teacherDashboardLessonSaving : $t.teacherDashboardLessonSave}
              </button>
            </div>
          </div>
        </div>
      {/if}
    </main>

    <!-- RIGHT: AI Panel -->
    <aside class="ai-sidebar">
      <div class="ai-header">
        <div class="ai-status">
          <span class="status-dot"></span>
          <span class="status-text">{$t.aiAssistant}</span>
        </div>
        <p class="ai-hint">{$t.aiSupportDesc}</p>
      </div>

      <div class="ai-messages" id="ai-messages-box">
        {#each aiMessages as msg}
          <div class="msg {msg.role}">{msg.content}</div>
        {/each}
        {#if aiLoading}
          <div class="msg assistant typing">
            <span></span><span></span><span></span>
          </div>
        {/if}
      </div>

      <div class="ai-form">
        <textarea
          placeholder={$t.typeMessage}
          bind:value={aiInput}
          onkeydown={handleAiKey}
          rows="1"
        ></textarea>
        <button onclick={sendAiMessage} disabled={aiLoading || !aiInput.trim()}>↑</button>
      </div>
    </aside>
  </div>
</div>

<style>
  .page { background:#050507; color:#fff; min-height:100vh; }

  .nav { display:flex; justify-content:space-between; align-items:center; padding:14px 24px; position:fixed; top:0; left:0; right:0; z-index:100; background:rgba(5,5,7,.97); backdrop-filter:blur(20px); border-bottom:1px solid rgba(255,255,255,.04); gap:12px; flex-wrap:wrap; }
  .nav-left { display:flex; align-items:center; gap:12px; }
  .logo { font-size:20px; font-weight:700; background:linear-gradient(135deg,#fff,#94a3b8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  .code-btn { background:rgba(59,130,246,.12); border:1px solid rgba(59,130,246,.3); padding:7px 14px; border-radius:8px; color:#60a5fa; font-size:13px; font-weight:600; font-family:monospace; letter-spacing:1px; cursor:pointer; transition:all .2s; }
  .code-btn:hover { background:rgba(59,130,246,.2); }

  .nav-right { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
  .stat-pill { background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.06); padding:5px 12px; border-radius:20px; font-size:12px; color:#a1a1aa; }
  .role-badge { padding:4px 10px; background:rgba(59,130,246,.15); border:1px solid rgba(59,130,246,.3); border-radius:20px; font-size:11px; color:#60a5fa; }
  .user-name { font-size:14px; color:#71717a; }
  .logout-btn { background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); padding:8px 14px; border-radius:8px; color:#71717a; font-size:13px; cursor:pointer; transition:all .2s; }
  .logout-btn:hover { color:#fff; background:rgba(255,255,255,.1); }

  .layout { display:grid; grid-template-columns:1fr 320px; padding-top:65px; min-height:100vh; }

  .main-content { padding:24px 28px; overflow-y:auto; }

  .tabs { display:flex; gap:8px; margin-bottom:24px; flex-wrap:wrap; }
  .tab-btn { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.06); border-radius:10px; padding:10px 18px; color:#71717a; font-size:14px; display:flex; align-items:center; gap:8px; cursor:pointer; transition:all .2s; }
  .tab-btn:hover { background:rgba(255,255,255,.08); color:#fff; }
  .tab-btn.active { background:rgba(59,130,246,.12); border-color:rgba(59,130,246,.3); color:#60a5fa; }
  .count { background:rgba(255,255,255,.1); padding:2px 8px; border-radius:10px; font-size:11px; }
  .count.warn { background:rgba(245,158,11,.15); color:#f59e0b; }
  .count.alert { background:rgba(239,68,68,.15); color:#ef4444; }

  .content h2 { font-size:22px; margin-bottom:12px; }
  .hint { font-size:13px; color:#52525b; margin-bottom:20px; }
  .empty { color:#52525b; font-size:14px; padding:40px 0; text-align:center; }

  .section-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; }
  .section-header h2 { margin-bottom:0; }
  .add-btn { background:linear-gradient(135deg,#3b82f6,#2563eb); padding:10px 18px; border-radius:10px; color:#fff; font-size:13px; font-weight:600; border:none; cursor:pointer; transition:all .2s; }
  .add-btn:hover { transform:translateY(-2px); box-shadow:0 8px 24px rgba(59,130,246,.3); }

  .add-form { background:rgba(20,20,24,.8); border:1px solid rgba(255,255,255,.06); border-radius:14px; padding:20px; margin-bottom:20px; animation:fadeIn .3s ease; }
  @keyframes fadeIn { from { opacity:0; transform:translateY(-8px); } to { opacity:1; transform:translateY(0); } }
  .add-form input, .add-form textarea { width:100%; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); border-radius:10px; padding:12px 14px; font-size:14px; color:#fff; margin-bottom:10px; transition:border .2s; box-sizing:border-box; resize:vertical; font-family:inherit; }
  .add-form input:focus, .add-form textarea:focus { border-color:rgba(59,130,246,.5); outline:none; }
  .add-form input::placeholder, .add-form textarea::placeholder { color:#3f3f46; }
  .add-form textarea { min-height:80px; }
  .btn-save { width:100%; background:linear-gradient(135deg,#3b82f6,#2563eb); padding:12px; border-radius:10px; color:#fff; font-weight:600; border:none; cursor:pointer; transition:all .2s; }
  .btn-save:hover:not(:disabled) { transform:translateY(-2px); }
  .btn-save:disabled { opacity:.5; cursor:not-allowed; }

  .cards { display:grid; gap:12px; }
  .card { background:rgba(20,20,24,.7); border:1px solid rgba(255,255,255,.05); border-radius:14px; padding:16px 20px; transition:all .3s; animation:slideIn .4s ease both; }
  @keyframes slideIn { from { opacity:0; transform:translateX(-10px); } to { opacity:1; transform:translateX(0); } }
  .card:hover { border-color:rgba(255,255,255,.1); transform:translateX(4px); }
  .card-header { display:flex; justify-content:space-between; align-items:flex-start; }
  .card-info { flex:1; }
  .card-info h3 { font-size:15px; margin-bottom:4px; }
  .card-desc { font-size:12px; color:#71717a; margin-bottom:6px; }
  .card-meta { display:flex; gap:12px; flex-wrap:wrap; }
  .date { font-size:11px; color:#52525b; }
  .soru-count { font-size:11px; color:#71717a; }
  .warn-badge { font-size:11px; color:#f59e0b; background:rgba(245,158,11,.1); padding:2px 8px; border-radius:10px; }

  .card-actions { flex-shrink:0; margin-left:12px; display:flex; gap:8px; align-items:center; }
  .edit-btn { background:none; border:none; font-size:16px; cursor:pointer; opacity:.5; transition:opacity .2s; }
  .edit-btn:hover { opacity:1; }
  .del-btn { background:none; border:none; font-size:16px; cursor:pointer; opacity:.5; transition:opacity .2s; }
  .del-btn:hover { opacity:1; }
  .confirm-inline { display:flex; align-items:center; gap:8px; background:rgba(239,68,68,.1); border:1px solid rgba(239,68,68,.3); border-radius:10px; padding:6px 10px; }
  .confirm-inline span { font-size:12px; color:#f87171; white-space:nowrap; }
  .btn-yes { background:#ef4444; border:none; padding:4px 10px; border-radius:6px; color:#fff; font-size:12px; cursor:pointer; }
  .btn-no { background:rgba(255,255,255,.1); border:none; padding:4px 10px; border-radius:6px; color:#fff; font-size:12px; cursor:pointer; }

  /* Attention tab — lesson list */
  .attention-lessons { display:grid; gap:10px; }
  .att-lesson-card { background:rgba(20,20,24,.7); border:1px solid rgba(255,255,255,.05); border-radius:14px; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; transition:all .2s; width:100%; text-align:left; }
  .att-lesson-card:hover { border-color:rgba(255,255,255,.12); transform:translateX(4px); }
  .att-lesson-card.has-warn { border-color:rgba(245,158,11,.25); background:rgba(245,158,11,.04); }
  .att-lesson-card.has-warn:hover { background:rgba(245,158,11,.08); }
  .att-left h3 { font-size:15px; margin-bottom:4px; }
  .att-meta { font-size:12px; color:#52525b; }
  .att-right { display:flex; align-items:center; gap:12px; }
  .att-percent { display:flex; flex-direction:column; align-items:flex-end; font-size:22px; font-weight:700; line-height:1.1; }
  .att-percent span { font-size:10px; font-weight:400; }
  .att-percent.warn { color:#f59e0b; }
  .att-percent.ok { color:#60a5fa; }
  .att-percent.none { color:#3f3f46; font-size:18px; }
  .att-arrow { color:#3f3f46; font-size:16px; }

  /* Breakdown detail */
  .back-btn { background:none; border:none; color:#60a5fa; font-size:13px; cursor:pointer; }
  .summary-bar { display:flex; gap:12px; margin-bottom:20px; flex-wrap:wrap; }
  .sum-item { background:rgba(20,20,24,.8); border-radius:12px; padding:14px 20px; display:flex; flex-direction:column; gap:4px; flex:1; min-width:100px; }
  .sum-num { font-size:28px; font-weight:700; }
  .sum-label { font-size:12px; color:#71717a; }
  .sum-item.red .sum-num { color:#f87171; }
  .sum-item.green .sum-num { color:#22c55e; }
  .sum-item.gray .sum-num { color:#a1a1aa; }

  .student-rows { display:grid; gap:8px; }
  .student-row { background:rgba(20,20,24,.7); border:1px solid rgba(255,255,255,.05); border-radius:14px; overflow:hidden; transition:border-color .2s; }
  .student-row.expanded { border-color:rgba(255,255,255,.1); }
  .student-header { width:100%; background:none; border:none; padding:14px 18px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; gap:12px; }
  .student-header:hover { background:rgba(255,255,255,.03); }
  .stu-left { display:flex; align-items:center; gap:12px; }
  .stu-avatar { width:40px; height:40px; border-radius:50%; background:rgba(255,255,255,.06); display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:600; flex-shrink:0; }
  .stu-avatar.red { background:rgba(239,68,68,.12); color:#f87171; }
  .stu-avatar.green { background:rgba(34,197,94,.12); color:#22c55e; }
  .stu-info { display:flex; flex-direction:column; gap:2px; text-align:left; }
  .stu-name { font-size:14px; font-weight:500; }
  .stu-meta { font-size:12px; color:#52525b; }
  .stu-right { display:flex; align-items:center; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
  .badge-red { background:rgba(239,68,68,.12); border:1px solid rgba(239,68,68,.25); color:#f87171; padding:4px 10px; border-radius:20px; font-size:12px; white-space:nowrap; }
  .badge-green { background:rgba(34,197,94,.1); border:1px solid rgba(34,197,94,.25); color:#22c55e; padding:4px 10px; border-radius:20px; font-size:12px; white-space:nowrap; }
  .chevron { color:#52525b; font-size:11px; flex-shrink:0; }

  .stu-questions { padding:0 18px 14px; display:grid; gap:8px; }
  .stu-q { background:rgba(255,255,255,.03); border-radius:10px; padding:12px 14px; border-left:3px solid rgba(255,255,255,.08); }
  .stu-q.q-anlamadi { border-left-color:#ef4444; }
  .stu-q.q-anladi { border-left-color:#22c55e; }
  .q-text { font-size:13px; color:#d4d4d8; margin-bottom:8px; line-height:1.5; }
  .q-meta { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
  .tag { padding:3px 10px; border-radius:20px; font-size:11px; font-weight:500; }
  .tag.green { background:rgba(34,197,94,.1); color:#22c55e; }
  .tag.red { background:rgba(239,68,68,.1); color:#f87171; }
  .tag.gray { background:rgba(255,255,255,.05); color:#71717a; }
  .tag.ai { background:rgba(139,92,246,.1); color:#a78bfa; border:1px solid rgba(139,92,246,.2); }
  .q-time { font-size:11px; color:#52525b; }

  .notif-cards { display:grid; gap:10px; }
  .notif-card { background:rgba(20,20,24,.6); border:1px solid rgba(255,255,255,.05); border-radius:12px; padding:14px 18px; display:flex; justify-content:space-between; align-items:center; transition:all .2s; }
  .notif-card.unread { border-color:rgba(245,158,11,.25); }
  .notif-card.urgent { background:rgba(239,68,68,.04); border-color:rgba(239,68,68,.25); }
  .notif-main { display:flex; flex-direction:column; gap:3px; }
  .notif-konu { font-size:14px; font-weight:500; }
  .notif-desc { font-size:13px; color:#f59e0b; }
  .notif-time { font-size:11px; color:#52525b; }
  .btn-okudum { background:rgba(34,197,94,.12); border:1px solid rgba(34,197,94,.3); padding:6px 12px; border-radius:6px; color:#22c55e; font-size:12px; cursor:pointer; transition:all .2s; flex-shrink:0; }
  .btn-okudum:hover { background:rgba(34,197,94,.2); }
  .read-label { color:#22c55e; font-size:16px; flex-shrink:0; }

  /* Student cards */
  .student-cards { display:grid; gap:10px; }
  .search-bar { margin-bottom:16px; }
  .search-bar input {
    width:100%;
    background:rgba(255,255,255,.05);
    border:1px solid rgba(255,255,255,.08);
    border-radius:10px;
    padding:12px 14px;
    font-size:14px;
    color:#fff;
    transition:border .2s;
  }
  .search-bar input:focus { border-color:rgba(59,130,246,.5); outline:none; }
  .search-bar input::placeholder { color:#52525b; }
  .student-card { background:rgba(20,20,24,.7); border:1px solid rgba(255,255,255,.05); border-radius:14px; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; transition:all .2s; }
  .student-card:hover { border-color:rgba(255,255,255,.1); }
  .student-info { display:flex; align-items:center; gap:14px; flex:1; }
  .student-avatar { width:44px; height:44px; border-radius:50%; background:rgba(59,130,246,.12); color:#60a5fa; display:flex; align-items:center; justify-content:center; font-size:14px; font-weight:600; flex-shrink:0; }
  .student-details { display:flex; flex-direction:column; gap:4px; }
  .student-name { font-size:15px; font-weight:500; }
  .student-meta { font-size:12px; color:#52525b; }
  .student-stats { display:flex; gap:10px; flex-wrap:wrap; }
  .stat-item { font-size:12px; color:#71717a; }
  .stat-item.warn { color:#f59e0b; }
  .student-date { font-size:11px; color:#52525b; }
  .student-actions { flex-shrink:0; }
  .del-btn { background:none; border:none; font-size:16px; cursor:pointer; opacity:.5; transition:opacity .2s; }
  .del-btn:hover { opacity:1; }

  /* AI Sidebar */
  .ai-sidebar { background:rgba(8,8,12,.98); border-left:1px solid rgba(255,255,255,.04); position:fixed; right:0; top:65px; bottom:0; width:320px; display:flex; flex-direction:column; }

  .ai-header { padding:16px 20px; border-bottom:1px solid rgba(255,255,255,.05); flex-shrink:0; }
  .ai-status { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
  .status-dot { width:8px; height:8px; background:#22c55e; border-radius:50%; animation:pulse 2s infinite; }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.4; } }
  .status-text { font-size:14px; font-weight:600; color:#fff; }
  .ai-hint { font-size:12px; color:#52525b; }

  .ai-messages { flex:1; overflow-y:auto; padding:16px 16px 8px; display:flex; flex-direction:column; gap:12px; }
  .msg { max-width:92%; padding:12px 14px; border-radius:14px; font-size:13px; line-height:1.55; white-space:pre-wrap; word-break:break-word; }
  .msg.user { align-self:flex-end; background:linear-gradient(135deg,#3b82f6,#2563eb); }
  .msg.assistant { align-self:flex-start; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.06); }
  .msg.typing { display:flex; gap:5px; padding:14px 18px; }
  .msg.typing span { width:7px; height:7px; background:#60a5fa; border-radius:50%; animation:typing 1.4s infinite; }
  .msg.typing span:nth-child(2) { animation-delay:.2s; }
  .msg.typing span:nth-child(3) { animation-delay:.4s; }
  @keyframes typing { 0%,60%,100% { transform:translateY(0); opacity:.5; } 30% { transform:translateY(-8px); opacity:1; } }

  .ai-form { padding:12px 16px 16px; border-top:1px solid rgba(255,255,255,.05); display:flex; gap:10px; flex-shrink:0; }
  .ai-form textarea { flex:1; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); border-radius:10px; padding:10px 14px; font-size:13px; color:#fff; resize:none; font-family:inherit; line-height:1.4; transition:border .2s; }
  .ai-form textarea:focus { border-color:rgba(59,130,246,.5); outline:none; }
  .ai-form textarea::placeholder { color:#3f3f46; }
  .ai-form button { background:linear-gradient(135deg,#3b82f6,#2563eb); width:42px; border-radius:10px; color:#fff; font-size:18px; border:none; cursor:pointer; transition:all .2s; flex-shrink:0; }
  .ai-form button:hover:not(:disabled) { transform:scale(1.05); }
  .ai-form button:disabled { opacity:.5; cursor:not-allowed; }

  @media (max-width:900px) {
    .layout { grid-template-columns:1fr; }
    .ai-sidebar { position:static; width:auto; border-left:none; border-top:1px solid rgba(255,255,255,.04); min-height:400px; }
  }

  .modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,.7); display:flex; align-items:center; justify-content:center; z-index:200; }
  .modal { background:rgba(20,20,24,.95); border:1px solid rgba(255,255,255,.1); border-radius:16px; padding:24px; width:90%; max-width:420px; animation:modalIn .2s ease; }
  @keyframes modalIn { from { opacity:0; transform:scale(.95); } to { opacity:1; transform:scale(1); } }
  .modal h3 { margin-bottom:16px; font-size:18px; }
  .modal input, .modal textarea { width:100%; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.1); border-radius:10px; padding:12px; color:#fff; margin-bottom:12px; font-size:14px; box-sizing:border-box; resize:vertical; }
  .modal input:focus, .modal textarea:focus { border-color:rgba(59,130,246,.5); outline:none; }
  .modal input::placeholder, .modal textarea::placeholder { color:#52525b; }
  .modal-actions { display:flex; gap:12px; justify-content:flex-end; }
  .modal .btn-cancel { background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.1); padding:10px 18px; border-radius:10px; color:#a1a1aa; cursor:pointer; }
  .modal .btn-cancel:hover { background:rgba(255,255,255,.1); }
  .modal .btn-save { background:linear-gradient(135deg,#3b82f6,#2563eb); border:none; padding:10px 20px; border-radius:10px; color:#fff; font-weight:600; cursor:pointer; }
  .modal .btn-save:hover:not(:disabled) { transform:translateY(-2px); }
  .modal .btn-save:disabled { opacity:.5; cursor:not-allowed; }
</style>
