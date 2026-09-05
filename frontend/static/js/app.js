/**
 * Root Vue application — Phase 1.
 *
 * Routing is a small hash-based view switcher written in plain Vue on purpose:
 * PROJECT_CONTEXT limits the stack to Flask + Vue + Bootstrap, so vue-router is
 * not pulled in as an extra dependency.
 */
const { createApp, computed, ref, onMounted, watch } = Vue;
const store = window.PPA.store;
const components = window.PPA.components;

const ROUTES = {
  "/login": { component: "LoginForm", public: true },
  "/register": { component: "RegisterForm", public: true },
  "/admin": { component: "AdminStats", role: "admin" },
  "/admin/companies": { component: "AdminCompanies", role: "admin" },
  "/admin/students": { component: "AdminStudents", role: "admin" },
  "/admin/drives": { component: "AdminDrives", role: "admin" },
  "/company": { component: "CompanyDashboard", role: "company" },
  "/company/drives": { component: "CompanyDrives", role: "company" },
  "/student": { component: "StudentDrives", role: "student" },
  "/student/applications": { component: "StudentApplications", role: "student" },
  "/student/profile": { component: "StudentProfile", role: "student" },
};

/** Sub-navigation shown for each role. */
const NAV_LINKS = {
  admin: [
    { href: "#/admin", label: "Overview" },
    { href: "#/admin/companies", label: "Companies" },
    { href: "#/admin/students", label: "Students" },
    { href: "#/admin/drives", label: "Drives" },
  ],
  company: [
    { href: "#/company", label: "Profile" },
    { href: "#/company/drives", label: "My drives" },
  ],
  student: [
    { href: "#/student", label: "Browse drives" },
    { href: "#/student/applications", label: "My applications" },
    { href: "#/student/profile", label: "My profile" },
  ],
};

createApp({
  components: {
    LoginForm: components.LoginForm,
    RegisterForm: components.RegisterForm,
    AdminStats: components.AdminStats,
    AdminCompanies: components.AdminCompanies,
    AdminStudents: components.AdminStudents,
    AdminDrives: components.AdminDrives,
    CompanyDashboard: components.CompanyDashboard,
    CompanyDrives: components.CompanyDrives,
    StudentDrives: components.StudentDrives,
    StudentApplications: components.StudentApplications,
    StudentProfile: components.StudentProfile,
  },
  setup() {
    const path = ref(window.location.hash.slice(1) || "/login");
    const state = store.state;

    function syncPath() {
      path.value = window.location.hash.slice(1) || "/login";
    }

    /** Send the user somewhere they are actually allowed to be. */
    function guard() {
      const route = ROUTES[path.value];
      if (!route) {
        window.location.hash = state.user ? store.homeFor(state.user.role) : "#/login";
        return;
      }
      if (route.public) {
        // A restored session should not sit on the login form.
        if (state.user && path.value === "/login") {
          window.location.hash = store.homeFor(state.user.role);
        }
        return;
      }
      if (!state.user) {
        window.location.hash = "#/login";
        return;
      }
      if (route.role && route.role !== state.user.role) {
        window.location.hash = store.homeFor(state.user.role);
      }
    }

    const currentComponent = computed(() => {
      const route = ROUTES[path.value];
      if (!route) return null;
      if (!route.public && !state.user) return null;
      if (route.role && state.user && route.role !== state.user.role) return null;
      return route.component;
    });

    onMounted(async () => {
      window.addEventListener("hashchange", () => {
        syncPath();
        guard();
      });
      // Restore a stored session (if any) before deciding which view to show,
      // so a refresh on a dashboard route stays put instead of bouncing to login.
      await store.checkSession();
      guard();
    });

    watch(() => state.user, guard);

    async function handleLogout() {
      await store.logout();
      window.location.hash = "#/login";
    }

    const navLinks = computed(() =>
      state.user ? NAV_LINKS[state.user.role] || [] : []
    );

    // Collapsed menu state on mobile; closes after any navigation.
    const menuOpen = ref(false);
    watch(path, () => (menuOpen.value = false));

    return { state, path, currentComponent, handleLogout, navLinks, menuOpen };
  },
  template: `
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
      <div class="container">
        <a class="navbar-brand fw-bold" href="#/login">PPA</a>

        <button class="navbar-toggler" type="button" @click="menuOpen = !menuOpen"
                :aria-expanded="menuOpen" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>

        <div class="collapse navbar-collapse" :class="{ show: menuOpen }">
          <ul v-if="navLinks.length" class="navbar-nav me-auto">
            <li v-for="link in navLinks" :key="link.href" class="nav-item">
              <a class="nav-link" :class="{ active: path === link.href.slice(1) }" :href="link.href">
                {{ link.label }}
              </a>
            </li>
          </ul>
          <span v-else class="navbar-text text-white-50 small me-auto">
            Placement Portal Application
          </span>

          <div class="d-flex flex-wrap align-items-center gap-2 py-2 py-lg-0">
            <span v-if="state.user" class="text-white small">
              {{ state.user.name }}
              <span class="badge text-bg-secondary">{{ state.user.role }}</span>
            </span>
            <button v-if="state.user" class="btn btn-sm btn-outline-light" @click="handleLogout">
              Log out
            </button>
            <template v-else>
              <a class="btn btn-sm btn-outline-light" href="#/login">Sign in</a>
              <a class="btn btn-sm btn-primary" href="#/register">Register</a>
            </template>
          </div>
        </div>
      </div>
    </nav>

    <main class="container py-5">
      <div v-if="state.booting" class="text-center text-muted py-5">Loading…</div>
      <component v-else-if="currentComponent" :is="currentComponent" />
      <div v-else class="text-center text-muted py-5">Redirecting…</div>
    </main>
  `,
}).mount("#app");
