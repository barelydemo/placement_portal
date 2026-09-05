/** Login — one form for every role; the backend response decides the redirect. */
window.PPA = window.PPA || {};
window.PPA.components = window.PPA.components || {};

window.PPA.components.LoginForm = {
  setup() {
    const { ref } = Vue;
    const store = window.PPA.store;

    const form = ref({ email: "", password: "" });
    const error = ref("");
    const submitting = ref(false);

    async function submit() {
      error.value = "";
      submitting.value = true;
      try {
        const user = await store.login({ ...form.value });
        window.location.hash = store.homeFor(user.role);
      } catch (err) {
        error.value = err.message;
      } finally {
        submitting.value = false;
      }
    }

    return { form, error, submitting, submit };
  },
  template: `
    <div class="row justify-content-center">
      <div class="col-12 col-md-6 col-lg-5">
        <div class="card shadow-sm">
          <div class="card-body p-4">
            <h1 class="h4 mb-1">Sign in</h1>
            <p class="text-muted small mb-4">Admin, company and student accounts all sign in here.</p>

            <div v-if="error" class="alert alert-danger py-2" role="alert">{{ error }}</div>

            <form @submit.prevent="submit" novalidate="false">
              <div class="mb-3">
                <label class="form-label" for="login-email">Email</label>
                <input id="login-email" v-model.trim="form.email" type="email"
                       class="form-control" required autocomplete="email" />
              </div>
              <div class="mb-3">
                <label class="form-label" for="login-password">Password</label>
                <input id="login-password" v-model="form.password" type="password"
                       class="form-control" required minlength="8" autocomplete="current-password" />
              </div>
              <button class="btn btn-primary w-100" type="submit" :disabled="submitting">
                {{ submitting ? 'Signing in…' : 'Sign in' }}
              </button>
            </form>

            <p class="text-center small mt-3 mb-0">
              No account? <a href="#/register">Register as student or company</a>
            </p>
          </div>
        </div>
      </div>
    </div>
  `,
};
