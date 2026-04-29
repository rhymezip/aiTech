<script>
  import { onMount } from 'svelte';
  import { apiUrl, authFetch } from '../stores/auth.js';
import LanguageSelector from '../components/LanguageSelector.svelte';
  import { t } from '../stores/i18n.js';

  let { handleLogout = () => {}, user = {} } = $props();

  let teachers        = $state([]);
  let filteredTeachers = $state([]);
  let selectedTeacher = $state(null);
  let lessons         = $state([]);
  let selectedLesson  = $state(null);
  let loadingTeachers = $state(true);
  let loadingLessons  = $state(false);

  let searchQuery = $state('');

  $effect(() => {
    if (searchQuery.trim() === '') {
      filteredTeachers = teachers;
    } else {
      const q = searchQuery.toLowerCase();
      filteredTeachers = teachers.filter(t => 
        t.ad.toLowerCase().includes(q) || t.soyad.toLowerCase().includes(q)
      );
    }
  });

  // Chat
  let chatMessages = $state([]);
  let chatInput    = $state('');
  let chatLoading  = $state(false);
  let lastSoruId   = $state(null);     // used for anladım/anlamadım
  let feedbackGiven = $state(false);   // whether user already rated this answer

  // History
  let showHistory  = $state(false);
  let history      = $state([]);
  let loadingHistory = $state(false);

  function getHistoryToggleText() {
    const prevLabel = $t.prevSoru;
    if (showHistory) return $t.historyHide;
    if (history.length === 0) return $t.historyShowNone;
    return `▼ ${prevLabel} (${history.length})`;
  }

  // Add teacher
  let showAddTeacher = $state(false);
  let addTeacherKod  = $state('');
  let addTeacherErr  = $state('');
  let addTeacherOk   = $state('');
  let addingTeacher  = $state(false);

  async function addTeacher() {
    addTeacherErr = ''; addTeacherOk = '';
    if (!addTeacherKod.trim()) { addTeacherErr = $t.enterCode; return; }
    addingTeacher = true;
    try {
      const res  = await authFetch(apiUrl + '/students/add-teacher', {
        method: 'POST',
        body: JSON.stringify({ hoca_kodu: addTeacherKod.trim().toUpperCase() }),
      });
      const data = await res.json();
      if (res.ok) {
        addTeacherOk  = `${data.hoca.ad} ${data.hoca.soyad} eklendi!`;
        addTeacherKod = '';
        await loadTeachers();
        setTimeout(() => { showAddTeacher = false; addTeacherOk = ''; }, 1500);
      } else {
        addTeacherErr = data.detail || $t.error;
      }
    } catch { addTeacherErr = $t.serverError; }
    finally { addingTeacher = false; }
  }

  // Remove teacher
  let removingTeacher = $state(null);
  let showRemoveConfirm = $state(false);
  let removeTeacherErr = $state('');
  let removeTeacherOk = $state('');

  function confirmRemoveTeacher(t) {
    removingTeacher = t;
    showRemoveConfirm = true;
    removeTeacherErr = '';
    removeTeacherOk = '';
  }

  async function removeTeacher() {
    if (!removingTeacher) return;
    try {
      const res = await authFetch(apiUrl + '/students/teacher/' + removingTeacher.id, {
        method: 'DELETE',
      });
      const data = await res.json();
      if (res.ok) {
        removeTeacherOk = $t.teacherRemoved;
        setTimeout(() => {
          showRemoveConfirm = false;
          removingTeacher = null;
          loadTeachers();
        }, 1000);
      } else {
        removeTeacherErr = data.detail || $t.error;
      }
    } catch { removeTeacherErr = $t.serverError; }
  }

  function cancelRemove() {
    showRemoveConfirm = false;
    removingTeacher = null;
    removeTeacherErr = '';
  }

  // ── Data loading ────────────────────────────────────────────────────────────
  async function loadTeachers() {
    loadingTeachers = true;
    try {
      const res  = await authFetch(apiUrl + '/students/teachers');
      const data = await res.json();
      if (data.teachers) {
        teachers = data.teachers;
        filteredTeachers = data.teachers;
      }
    } finally { loadingTeachers = false; }
  }

  async function selectTeacher(t) {
    selectedTeacher = t;
    selectedLesson  = null;
    chatMessages    = [];
    showHistory     = false;
    history         = [];
    loadingLessons  = true;
    try {
      const res  = await authFetch(apiUrl + '/students/lessons/' + t.id);
      const data = await res.json();
      if (data.lessons) lessons = data.lessons;
    } finally { loadingLessons = false; }
  }

  function selectLesson(l) {
    selectedLesson = l;
    feedbackGiven  = false;
    lastSoruId     = null;
    showHistory    = false;
    const greetHello = user?.ad ? `${user.ad}, ` : '';
    chatMessages   = [
      { role: 'assistant', content: `${greetHello}"${l.tema}" ${$t.aboutTopic} ${$t.aiAssistant}. ${$t.enterQuestion} 🎓` }
    ];
    loadHistory(l.id);
  }

  async function loadHistory(dersId) {
    loadingHistory = true;
    try {
      const res  = await authFetch(apiUrl + '/students/history/' + dersId);
      const data = await res.json();
      if (data.history) {
        history = data.history;
        if (history.length > 0) {
          showHistory = true;
        }
        for (let i = 0; i < history.length; i++) {
          history[i].soru_no = i + 1;
        }
      }
    } finally { loadingHistory = false; }
  }

  function back() {
    if (selectedLesson) {
      selectedLesson = null;
      chatMessages   = [];
      lastSoruId     = null;
      feedbackGiven  = false;
    } else if (selectedTeacher) {
      selectedTeacher = null;
      lessons         = [];
    }
  }

  // ── Chat ────────────────────────────────────────────────────────────────────
  async function sendChat() {
    if (!chatInput.trim() || chatLoading) return;
    const q = chatInput.trim();
    chatMessages  = [...chatMessages, { role: 'user', content: q }];
    chatInput     = '';
    chatLoading   = true;
    lastSoruId    = null;
    feedbackGiven = false;

    try {
      const res  = await authFetch(apiUrl + '/students/ask', {
        method: 'POST',
        body: JSON.stringify({ ders_id: selectedLesson.id, soru: q }),
      });
      const data = await res.json();
      chatMessages = [...chatMessages, { role: 'assistant', content: data.cevap || $t.error }];
      lastSoruId   = data.soru_id || null;
    } catch {
      chatMessages = [...chatMessages, { role: 'assistant', content: $t.serverError }];
    } finally {
      chatLoading = false;
      setTimeout(scrollChatBottom, 50);
    }
  }

  async function sendFeedback(anladi) {
    if (!lastSoruId || feedbackGiven) return;
    feedbackGiven = true;
    try {
      await authFetch(apiUrl + '/students/anladi', {
        method: 'POST',
        body: JSON.stringify({ soru_id: lastSoruId, anladi }),
      });
      const label = anladi ? $t.copyCodeSuccess + ' ' + $t.understood : '✗ ' + $t.notUnderstood;
      chatMessages = [...chatMessages, { role: 'system-info', content: label }];
    } catch { feedbackGiven = false; }
    setTimeout(scrollChatBottom, 50);
  }

  function handleChatKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
  }

  function scrollChatBottom() {
    const box = document.querySelector('.chat-messages');
    if (box) box.scrollTop = box.scrollHeight;
  }

  onMount(() => { loadTeachers(); });
</script>

<div class="page">
  <nav class="nav">
    <div class="nav-left">
      {#if selectedTeacher || selectedLesson}
        <button class="back-btn-nav" onclick={back}>← {$t.back}</button>
      {/if}
      <span class="logo">◎ AiTech</span>
      {#if selectedLesson}
        <span class="breadcrumb">/ {selectedLesson.tema}</span>
      {:else if selectedTeacher}
        <span class="breadcrumb">/ {selectedTeacher.ad} {selectedTeacher.soyad}</span>
      {/if}
    </div>
    <div class="nav-right">
      <span class="role-badge">{$t.roleStudent}</span>
      <span class="user-name">{user?.ad} {user?.soyad}</span>
      <LanguageSelector />
      <button class="logout-btn" onclick={handleLogout}>{$t.logout}</button>
    </div>
  </nav>

  <div class="main-content">
    <!-- Remove teacher confirmation modal -->
    {#if showRemoveConfirm}
      <div class="modal-overlay">
        <div class="modal">
          <p>{$t.removeTeacherConfirm}</p>
          {#if removeTeacherErr}<p class="modal-err">{removeTeacherErr}</p>{/if}
          {#if removeTeacherOk}<p class="modal-ok">{removeTeacherOk}</p>{/if}
          <div class="modal-btns">
            <button class="modal-btn cancel" onclick={cancelRemove}>{$t.removeTeacherNo}</button>
            <button class="modal-btn confirm" onclick={removeTeacher}>{$t.removeTeacherYes}</button>
          </div>
        </div>
      </div>
    {/if}

    <!-- TEACHER LIST -->
    {#if !selectedTeacher}
      <div class="screen">
        <div class="screen-header">
          <h2>{$t.studentDashboardTitleTeachers}</h2>
          <button class="add-teacher-btn" onclick={() => { showAddTeacher = !showAddTeacher; addTeacherErr = ''; addTeacherOk = ''; }}>
            {showAddTeacher ? $t.teacherDashboardAddLessonClose : $t.studentDashboardAddTeacher}
          </button>
        </div>

        {#if showAddTeacher}
          <div class="add-teacher-box">
            <p>{$t.studentDashboardAddTeacherPrompt}</p>
            <div class="add-teacher-row">
              <input
                type="text"
                placeholder={$t.studentDashboardAddTeacherInputPlaceholder}
                bind:value={addTeacherKod}
                style="text-transform:uppercase"
                onkeydown={(e) => e.key === 'Enter' && addTeacher()}
                maxlength="8"
              />
              <button onclick={addTeacher} disabled={addingTeacher || !addTeacherKod.trim()}>
                {addingTeacher ? $t.loading : $t.studentDashboardAddTeacherButton}
              </button>
            </div>
            {#if addTeacherErr}<p class="add-err">{addTeacherErr}</p>{/if}
            {#if addTeacherOk}<p class="add-ok">✓ {addTeacherOk}</p>{/if}
          </div>
        {/if}

        {#if loadingTeachers}
          <div class="empty">{$t.studentDashboardLoading}</div>
        {:else if teachers.length === 0}
          <div class="empty">{$t.studentDashboardNoTeachers}</div>
        {:else}
          <div class="search-bar">
            <input
              type="text"
              placeholder={$t.searchTeacher}
              bind:value={searchQuery}
            />
          </div>
          <div class="list">
            {#each filteredTeachers as teacher}
              <div class="teacher-card">
                <div class="card" role="button" tabindex="0" onclick={() => selectTeacher(teacher)} onkeydown={(e) => e.key === 'Enter' && selectTeacher(teacher)}>
                  <div class="avatar">{teacher.ad[0]}{teacher.soyad[0]}</div>
                  <div class="info">
                    <div class="name">{teacher.ad} {teacher.soyad}</div>
                    <div class="meta">📚 {teacher.ders_sayisi} {$t.lessons}</div>
                  </div>
                  <span class="arrow-icon">→</span>
                </div>
                <button class="remove-teacher-btn" onclick={(e) => { e.stopPropagation(); confirmRemoveTeacher(teacher); }}>×</button>
              </div>
            {/each}
          </div>
        {/if}
      </div>

    <!-- LESSON LIST -->
    {:else if !selectedLesson}
      <div class="screen">
        <h2>📚 {selectedTeacher.ad} {selectedTeacher.soyad} — {$t.lessons}</h2>
        {#if loadingLessons}
          <div class="empty">{$t.loading}</div>
        {:else if lessons.length === 0}
          <div class="empty">{$t.studentDashboardNoLessons}</div>
        {:else}
          <div class="list">
            {#each lessons as lesson}
              <button class="card" onclick={() => selectLesson(lesson)}>
                <div class="lesson-icon">📖</div>
                <div class="info">
                  <div class="name">{lesson.tema}</div>
                  {#if lesson.icerik}
                    <div class="meta">{lesson.icerik.slice(0, 80)}{lesson.icerik.length > 80 ? '…' : ''}</div>
                  {/if}
                  <div class="date">{new Date(lesson.olusturma_tarihi).toLocaleDateString('tr-TR')}</div>
                </div>
                <span class="arrow-icon">→</span>
              </button>
            {/each}
          </div>
        {/if}
      </div>

    <!-- CHAT VIEW -->
    {:else}
      <div class="chat-layout">
        <!-- Lesson info panel -->
        <div class="lesson-panel">
          <h2>{selectedLesson.tema}</h2>
          {#if selectedLesson.icerik}
            <p class="lesson-icerik">{selectedLesson.icerik}</p>
          {/if}

{#if history.length > 0}
              <div class="history-total">{$t.prevCountToplam} ({history.length})</div>
              <button class="hist-toggle" onclick={() => showHistory = !showHistory}>
                {getHistoryToggleText()}
              </button>
            {#if showHistory}
              <div class="history-list">
                {#each history as h}
                  <div class="hist-item">
                    <div class="hist-header">
                      <span class="hist-no">#{h.soru_no}</span>
                    </div>
                    <div class="hist-q">Sen: {h.soru}</div>
                    <div class="hist-a">AI: {h.cevap}</div>
                    {#if h.anladi_mi !== null}
                      <div class="hist-f" class:green={h.anladi_mi} class:red={!h.anladi_mi}>
                        {h.anladi_mi ? $t.understood : $t.notUnderstood}
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}
          {/if}
        </div>

        <!-- Chat -->
        <div class="chat-box">
          <div class="chat-messages" id="chat-messages">
            {#each chatMessages as msg}
              {#if msg.role === 'system-info'}
                <div class="msg-info">{msg.content}</div>
              {:else}
                <div class="msg {msg.role}">{msg.content}</div>
              {/if}
            {/each}
            {#if chatLoading}
              <div class="msg assistant typing">
                <span></span><span></span><span></span>
              </div>
            {/if}
          </div>

          <!-- Anladım/Anlamadım buttons -->
          {#if lastSoruId && !feedbackGiven && !chatLoading}
            <div class="feedback-bar">
              <span class="feedback-label">{$t.confirm}</span>
              <button class="fb-btn anladi" onclick={() => sendFeedback(true)}>{$t.understood}</button>
              <button class="fb-btn anlamadi" onclick={() => sendFeedback(false)}>{$t.notUnderstood}</button>
            </div>
          {/if}

          <div class="chat-form">
            <textarea
              placeholder={$t.enterQuestion}
              bind:value={chatInput}
              onkeydown={handleChatKey}
              rows="1"
              disabled={chatLoading}
            ></textarea>
            <button onclick={sendChat} disabled={chatLoading || !chatInput.trim()}>↑</button>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .page { background:#050507; color:#fff; height:100vh; overflow:hidden; display:flex; flex-direction:column; }

  .nav { display:flex; justify-content:space-between; align-items:center; padding:12px 24px; position:fixed; top:0; left:0; right:0; z-index:100; background:rgba(5,5,7,.97); backdrop-filter:blur(20px); border-bottom:1px solid rgba(255,255,255,.04); }
  .nav-left { display:flex; align-items:center; gap:10px; overflow:hidden; }
  .back-btn-nav { background:none; border:none; color:#60a5fa; font-size:14px; cursor:pointer; flex-shrink:0; }
  .logo { font-size:19px; font-weight:700; background:linear-gradient(135deg,#fff,#94a3b8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; flex-shrink:0; }
  .breadcrumb { font-size:14px; color:#52525b; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .nav-right { display:flex; align-items:center; gap:10px; flex-shrink:0; }
  .role-badge { padding:4px 10px; background:rgba(34,197,94,.12); border:1px solid rgba(34,197,94,.3); border-radius:20px; font-size:11px; color:#22c55e; }
  .user-name { font-size:14px; color:#71717a; }
  .logout-btn { background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); padding:7px 13px; border-radius:8px; color:#71717a; font-size:13px; cursor:pointer; transition:all .2s; }
  .logout-btn:hover { color:#fff; }

  .main-content { margin-top:57px; flex:1; overflow:hidden; display:flex; flex-direction:column; }

  /* Teacher / Lesson list screens */
  .screen { padding:28px 28px; overflow-y:auto; height:100%; box-sizing:border-box; }
  h2 { font-size:22px; margin-bottom:20px; }
  .empty { color:#52525b; font-size:14px; padding:40px 0; text-align:center; line-height:1.7; }

  .list { display:grid; gap:12px; max-width:600px; }
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
  .teacher-card { position:relative; display:block; }
  .teacher-card .card { display:flex; align-items:center; gap:14px; }
  .teacher-card .remove-teacher-btn { position:absolute; right:40px; top:50%; transform:translateY(-50%); }
  .card { background:rgba(20,20,24,.7); border:1px solid rgba(255,255,255,.05); border-radius:14px; padding:16px 20px; display:flex; align-items:center; gap:14px; cursor:pointer; transition:all .2s; width:100%; text-align:left; }
  .card:hover { border-color:rgba(255,255,255,.12); transform:translateX(4px); background:rgba(26,26,30,.8); }
  .avatar { width:44px; height:44px; border-radius:50%; background:rgba(59,130,246,.15); color:#60a5fa; display:flex; align-items:center; justify-content:center; font-weight:600; font-size:14px; flex-shrink:0; }
  .lesson-icon { font-size:28px; flex-shrink:0; }
  .info { flex:1; min-width:0; }
  .name { font-size:15px; font-weight:500; margin-bottom:4px; }
  .meta { font-size:12px; color:#71717a; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .date { font-size:11px; color:#52525b; margin-top:4px; }
  .arrow-icon { color:#3f3f46; flex-shrink:0; }

  /* Chat layout */
  .chat-layout { display:grid; grid-template-columns:300px 1fr; height:100%; overflow:hidden; }

  .lesson-panel { background:rgba(10,10,14,.7); border-right:1px solid rgba(255,255,255,.05); padding:20px; overflow-y:auto; display:flex; flex-direction:column; gap:12px; }
  .lesson-panel h2 { font-size:17px; margin-bottom:0; }
  .lesson-icerik { font-size:13px; color:#a1a1aa; line-height:1.7; }

  .hist-toggle { background:none; border:1px solid rgba(255,255,255,.08); border-radius:8px; padding:8px 14px; color:#71717a; font-size:12px; cursor:pointer; text-align:left; width:100%; transition:all .2s; }
  .hist-toggle:hover { color:#fff; border-color:rgba(255,255,255,.15); }
  .history-total { font-size:12px; color:#71717a; margin-bottom:8px; }
  .hist-header { display:flex; justify-content:flex-end; margin-bottom:4px; }
  .hist-no { font-size:11px; color:#52525b; background:rgba(255,255,255,.05); padding:2px 6px; border-radius:4px; }
  .history-list { display:flex; flex-direction:column; gap:10px; }
  .hist-item { background:rgba(255,255,255,.03); border-radius:10px; padding:10px 12px; }
  .hist-q { font-size:12px; color:#a1a1aa; margin-bottom:6px; }
  .hist-a { font-size:12px; color:#71717a; line-height:1.5; }
  .hist-f { font-size:11px; margin-top:6px; }
  .hist-f.green { color:#22c55e; }
  .hist-f.red { color:#f87171; }

  .chat-box { display:flex; flex-direction:column; overflow:hidden; }

  .chat-messages { flex:1; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:12px; }
  .msg { max-width:90%; padding:12px 16px; border-radius:14px; font-size:14px; line-height:1.55; white-space:pre-wrap; word-break:break-word; }
  .msg.user { align-self:flex-end; background:linear-gradient(135deg,#3b82f6,#2563eb); }
  .msg.assistant { align-self:flex-start; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.06); }
  .msg.typing { display:flex; gap:5px; padding:14px 20px; }
  .msg.typing span { width:7px; height:7px; background:#60a5fa; border-radius:50%; animation:typing 1.4s infinite; }
  .msg.typing span:nth-child(2) { animation-delay:.2s; }
  .msg.typing span:nth-child(3) { animation-delay:.4s; }
  @keyframes typing { 0%,60%,100% { transform:translateY(0); opacity:.5; } 30% { transform:translateY(-8px); opacity:1; } }
  .msg-info { align-self:center; font-size:12px; color:#52525b; background:rgba(255,255,255,.04); padding:6px 14px; border-radius:20px; }

  /* Feedback bar */
  .feedback-bar { display:flex; align-items:center; gap:10px; padding:10px 20px; background:rgba(20,20,24,.8); border-top:1px solid rgba(255,255,255,.05); flex-shrink:0; }
  .feedback-label { font-size:13px; color:#71717a; flex:1; }
  .fb-btn { padding:8px 18px; border-radius:8px; font-size:13px; font-weight:600; cursor:pointer; border:1px solid; transition:all .2s; }
  .fb-btn.anladi { background:rgba(34,197,94,.12); border-color:rgba(34,197,94,.3); color:#22c55e; }
  .fb-btn.anladi:hover { background:rgba(34,197,94,.22); }
  .fb-btn.anlamadi { background:rgba(239,68,68,.08); border-color:rgba(239,68,68,.3); color:#f87171; }
  .fb-btn.anlamadi:hover { background:rgba(239,68,68,.18); }

  .chat-form { padding:12px 20px 16px; border-top:1px solid rgba(255,255,255,.05); display:flex; gap:10px; flex-shrink:0; }
  .chat-form textarea { flex:1; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); border-radius:10px; padding:12px 14px; font-size:14px; color:#fff; resize:none; font-family:inherit; transition:border .2s; }
  .chat-form textarea:focus { border-color:rgba(59,130,246,.5); outline:none; }
  .chat-form textarea::placeholder { color:#3f3f46; }
  .chat-form textarea:disabled { opacity:.6; }
  .chat-form button { background:linear-gradient(135deg,#3b82f6,#2563eb); width:46px; border-radius:10px; color:#fff; font-size:18px; border:none; cursor:pointer; flex-shrink:0; transition:all .2s; }
  .chat-form button:hover:not(:disabled) { transform:scale(1.05); }
  .chat-form button:disabled { opacity:.5; cursor:not-allowed; }

  .screen-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; }
  .screen-header h2 { margin-bottom:0; }
  .add-teacher-btn { background:linear-gradient(135deg,#3b82f6,#2563eb); padding:10px 16px; border-radius:10px; color:#fff; font-size:13px; font-weight:600; border:none; cursor:pointer; transition:all .2s; flex-shrink:0; }
  .add-teacher-btn:hover { transform:translateY(-2px); box-shadow:0 8px 20px rgba(59,130,246,.3); }

  .add-teacher-box { background:rgba(20,20,24,.8); border:1px solid rgba(59,130,246,.2); border-radius:14px; padding:20px; margin-bottom:20px; animation:fadeIn .3s ease; }
  @keyframes fadeIn { from { opacity:0; transform:translateY(-8px); } to { opacity:1; transform:translateY(0); } }
  .add-teacher-box p { font-size:14px; color:#a1a1aa; margin-bottom:12px; }
  .add-teacher-row { display:flex; gap:10px; }
  .add-teacher-row input { flex:1; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); border-radius:10px; padding:12px 14px; font-size:15px; color:#fff; font-family:monospace; letter-spacing:2px; transition:border .2s; }
  .add-teacher-row input:focus { border-color:rgba(59,130,246,.5); outline:none; }
  .add-teacher-row input::placeholder { color:#3f3f46; letter-spacing:0; font-family:inherit; }
  .add-teacher-row button { background:linear-gradient(135deg,#3b82f6,#2563eb); padding:12px 20px; border-radius:10px; color:#fff; font-weight:600; border:none; cursor:pointer; transition:all .2s; flex-shrink:0; }
  .add-teacher-row button:hover:not(:disabled) { transform:translateY(-2px); }
  .add-teacher-row button:disabled { opacity:.5; cursor:not-allowed; }
  .add-err { color:#f87171; font-size:13px; margin-top:10px; }
  .add-ok  { color:#22c55e; font-size:13px; margin-top:10px; }

  @media (max-width:700px) {
    .chat-layout { grid-template-columns:1fr; grid-template-rows:auto 1fr; }
    .lesson-panel { border-right:none; border-bottom:1px solid rgba(255,255,255,.05); max-height:200px; }
  }

  .remove-teacher-btn {
    background:rgba(239,68,68,.1);
    border:1px solid rgba(239,68,68,.3);
    color:#f87171;
    width:28px;
    height:28px;
    border-radius:50%;
    font-size:18px;
    cursor:pointer;
    flex-shrink:0;
    display:flex;
    align-items:center;
    justify-content:center;
    transition:all .2s;
  }
  .remove-teacher-btn:hover {
    background:rgba(239,68,68,.2);
    transform:scale(1.1);
  }

  .modal-overlay {
    position:fixed;
    top:0; left:0; right:0; bottom:0;
    background:rgba(0,0,0,.7);
    display:flex;
    align-items:center;
    justify-content:center;
    z-index:200;
  }
  .modal {
    background:rgba(20,20,24,.95);
    border:1px solid rgba(255,255,255,.1);
    border-radius:16px;
    padding:24px;
    max-width:400px;
    text-align:center;
  }
  .modal p { font-size:15px; margin-bottom:20px; color:#e4e4e7; }
  .modal-btns { display:flex; gap:12px; justify-content:center; }
  .modal-btn {
    padding:10px 20px;
    border-radius:10px;
    font-size:14px;
    font-weight:600;
    cursor:pointer;
    border:1px solid;
    transition:all .2s;
  }
  .modal-btn.cancel {
    background:rgba(255,255,255,.05);
    border-color:rgba(255,255,255,.1);
    color:#a1a1aa;
  }
  .modal-btn.cancel:hover { color:#fff; }
  .modal-btn.confirm {
    background:rgba(239,68,68,.15);
    border-color:rgba(239,68,68,.4);
    color:#f87171;
  }
  .modal-btn.confirm:hover { background:rgba(239,68,68,.25); }
  .modal-err { color:#f87171; font-size:13px; margin-bottom:10px; }
  .modal-ok { color:#22c55e; font-size:13px; margin-bottom:10px; }
</style>
