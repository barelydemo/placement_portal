/** Registration — Student / Company toggle with different fields per role. */
window.PPA = window.PPA || {};
window.PPA.components = window.PPA.components || {};

window.PPA.components.RegisterForm = {
  setup() {
    const { ref, reactive } = Vue;
    const store = window.PPA.store;

    const role = ref("student");
    const error = ref("");
    const success = ref("");
    const submitting = ref(false);

    const student = reactive({
      name: "",
      email: "",
      password: "",
      branch: "",
      cgpa: "",
      graduation_year: "",
      phone: "",
    });

    const company = reactive({
      company_name: "",
      email: "",
      password: "",
      hr_contact: "",
      website: "",
    });

    async function submit() {
      error.value = "";
      success.value = "";
      submitting.value = true;
      const payload =
        role.value === "student" ? { role: "student", ...student } : { role: "company", ...company };
      try {
        const data = await store.register(payload);
        success.value = data.message;
      } catch (err) {
        error.value = err.message;
      } finally {
        submitting.value = false;
      }
    }

    return { role, student, company, error, success, submitting, submit };
  },
  template: `
    <div class="row justify-content-center">
      <div class="col-12 col-md-8 col-lg-6">
        <div class="card shadow-sm">
          <div class="card-body p-4">
            <h1 class="h4 mb-1">Create an account</h1>
            <p class="text-muted small mb-3">
              Companies require admin approval before they can post placement drives.
            </p>

            <div class="btn-group w-100 mb-4" role="group" aria-label="Account type">
              <input type="radio" class="btn-check" id="role-student" value="student" v-model="role" />
              <label class="btn btn-outline-primary" for="role-student">Student</label>
              <input type="radio" class="btn-check" id="role-company" value="company" v-model="role" />
              <label class="btn btn-outline-primary" for="role-company">Company</label>
            </div>

            <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
            <div v-if="success" class="alert alert-success py-2">
              {{ success }} <a href="#/login" class="alert-link">Go to sign in</a>
            </div>

            <form @submit.prevent="submit">
              <!-- Student fields -->
              <template v-if="role === 'student'">
                <div class="mb-3">
                  <label class="form-label" for="s-name">Full name</label>
                  <input id="s-name" v-model.trim="student.name" class="form-control" required maxlength="120" />
                </div>
                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label" for="s-email">Email</label>
                    <input id="s-email" v-model.trim="student.email" type="email" class="form-control" required />
                  </div>
                  <div class="col-md-6 mb-3">
                    <label class="form-label" for="s-password">Password</label>
                    <input id="s-password" v-model="student.password" type="password"
                           class="form-control" required minlength="8" />
                    <div class="form-text">Minimum 8 characters.</div>
                  </div>
                </div>
                <div class="row">
                  <div class="col-md-4 mb-3">
                    <label class="form-label" for="s-branch">Branch</label>
                    <input id="s-branch" v-model.trim="student.branch" class="form-control" placeholder="e.g. CSE" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label" for="s-cgpa">CGPA</label>
                    <input id="s-cgpa" v-model="student.cgpa" type="number" step="0.01" min="0" max="10"
                           class="form-control" placeholder="0 – 10" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label" for="s-year">Graduation year</label>
                    <input id="s-year" v-model="student.graduation_year" type="number" min="1990" max="2100"
                           class="form-control" placeholder="e.g. 2027" />
                  </div>
                </div>
                <div class="mb-3">
                  <label class="form-label" for="s-phone">Phone <span class="text-muted">(optional)</span></label>
                  <input id="s-phone" v-model.trim="student.phone" class="form-control" maxlength="20" />
                </div>
              </template>

              <!-- Company fields -->
              <template v-else>
                <div class="mb-3">
                  <label class="form-label" for="c-name">Company name</label>
                  <input id="c-name" v-model.trim="company.company_name" class="form-control" required maxlength="120" />
                </div>
                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label" for="c-email">Work email</label>
                    <input id="c-email" v-model.trim="company.email" type="email" class="form-control" required />
                  </div>
                  <div class="col-md-6 mb-3">
                    <label class="form-label" for="c-password">Password</label>
                    <input id="c-password" v-model="company.password" type="password"
                           class="form-control" required minlength="8" />
                    <div class="form-text">Minimum 8 characters.</div>
                  </div>
                </div>
                <div class="mb-3">
                  <label class="form-label" for="c-hr">HR contact</label>
                  <input id="c-hr" v-model.trim="company.hr_contact" class="form-control"
                         placeholder="Name / phone of HR contact" />
                </div>
                <div class="mb-3">
                  <label class="form-label" for="c-website">Website <span class="text-muted">(optional)</span></label>
                  <input id="c-website" v-model.trim="company.website" class="form-control" placeholder="example.com" />
                </div>
              </template>

              <button class="btn btn-primary w-100" type="submit" :disabled="submitting">
                {{ submitting ? 'Creating account…' : 'Register' }}
              </button>
            </form>

            <p class="text-center small mt-3 mb-0">
              Already registered? <a href="#/login">Sign in</a>
            </p>
          </div>
        </div>
      </div>
    </div>
  `,
};
