<script>
  import { onMount } from 'svelte';
import { initI18n } from './stores/i18n.js';
  import { user, initAuth, clearAuth } from './stores/auth.js';
  import Login from './components/Login.svelte';
  import Register from './components/Register.svelte';
  import TeacherDashboard from './components/TeacherDashboard.svelte';
  import StudentDashboard from './components/StudentDashboard.svelte';

  let currentPage = $state('login');
  let currentUser = $state(null);

  const unsub = user.subscribe(v => { currentUser = v; });

  function goToLogin() {
    currentPage = 'login';
    window.location.hash = '';
  }

  function handleLogout() {
    clearAuth();
    currentUser = null;
    currentPage = 'login';
    window.location.hash = '';
  }

  onMount(() => {
    initAuth();
    initI18n(); // initialize language from localStorage / browser

    // After initAuth, subscribe gives us the value
    const u = currentUser;
    if (u) {
      currentPage = u.role === 'teacher' ? 'teacher' : 'student';
    }

    function handleHashChange() {
      const h = window.location.hash.slice(1);
      if (!currentUser) {
        if (h === 'register') currentPage = 'register';
        else currentPage = 'login';
      }
    }

    window.addEventListener('hashchange', handleHashChange);
    handleHashChange();
    return () => {
      window.removeEventListener('hashchange', handleHashChange);
      unsub();
    };
  });

  // React to user changes (login / logout)
  $effect(() => {
    if (currentUser) {
      currentPage = currentUser.role === 'teacher' ? 'teacher' : 'student';
    }
  });
</script>

{#if currentUser === null}
  {#if currentPage === 'register'}
    <Register {goToLogin} />
  {:else}
    <Login />
  {/if}
{:else if currentUser.role === 'teacher'}
  <TeacherDashboard {handleLogout} user={currentUser} />
{:else}
  <StudentDashboard {handleLogout} user={currentUser} />
{/if}
