/** Student profile — academic details (drive eligibility) + resume upload. */
window.PPA = window.PPA || {};
window.PPA.components = window.PPA.components || {};

window.PPA.components.StudentProfile = {
  setup() {
    const { ref, reactive, onMounted } = Vue;
    const store = window.PPA.store;

    const student = ref(null);
    const loading = ref(true);
    const error = ref("");
    const notice = ref("");
    const saving = ref(false);
    const uploading = ref(false);
    const resumeInput = ref(null);

    const form = reactive({
      name: "",
      branch: "",
      cgpa: "",
      graduation_year: "",
      phone: "",
    });

    function fillForm(data) {
      form.name = data.name || "";
      form.branch = data.branch || "";
      form.cgpa = data.cgpa !== null && data.cgpa !== undefined ? data.cgpa : "";
      form.graduation_year = data.graduation_year || "";
      form.phone = data.phone || "";
    }

    async function load() {
      loading.value = true;
      error.value = "";
      try {
        const data = await store.api("/api/student/profile");
        student.value = data.student;
        fillForm(data.student);
      } catch (err) {
        error.value = err.message;
      } finally {
        loading.value = false;
      }
    }

    async function save() {
      saving.value = true;
      error.value = "";
      notice.value = "";
      try {
        const data = await store.api("/api/student/profile", { method: "PUT", body: { ...form } });
        student.value = data.student;
        notice.value = data.message + " Your drive eligibility has been updated.";
        if (store.state.user) store.state.user.name = data.student.name;
      } catch (err) {
        error.value = err.message;
      } finally {
        saving.value = false;
      }
    }

    /** Resume upload uses FormData, so no JSON Content-Type here. */
    async function uploadResume(event) {
      const file = event.target.files[0];
      if (!file) return;

      uploading.value = true;
      error.value = "";
      notice.value = "";
      const body = new FormData();
      body.append("resume", file);

      try {
        const response = await fetch("/api/student/resume", {
          method: "POST",
          headers: { Authorization: `Bearer ${store.state.token}` },
          body,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Upload failed.");
        student.value = data.student;
        notice.value = data.message;
      } catch (err) {
        error.value = err.message;
      } finally {
        uploading.value = false;
        if (resumeInput.value) resumeInput.value.value = "";
      }
    }

    async function downloadResume() {
      try {
        const response = await fetch("/api/student/resume/download", {
          headers: { Authorization: `Bearer ${store.state.token}` },
        });
        if (!response.ok) throw new Error("Could not download the resume.");
        const blob = await response.blob();
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = student.value.resume_name || "resume";
        link.click();
        URL.revokeObjectURL(link.href);
      } catch (err) {
        error.value = err.message;
      }
    }

    function formatDate(iso) {
      return iso ? new Date(iso).toLocaleString() : "—";
    }

    onMounted(load);

    return {
      student, loading, error, notice, saving, uploading, form, resumeInput,
      save, uploadResume, downloadResume, formatDate,
    };
  },
  template: `
    <div class="row justify-content-center g-4">
      <div class="col-12 col-lg-7">
        <div class="card shadow-sm h-100">
          <div class="card-body p-4">
            <h1 class="h4 mb-1">My profile</h1>
            <p class="text-muted small mb-4">
              Branch, CGPA and graduation year decide which drives you are eligible for.
            </p>

            <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
            <div v-if="notice" class="alert alert-success py-2">{{ notice }}</div>
            <div v-if="loading" class="text-muted">Loading profile…</div>

            <form v-else @submit.prevent="save">
              <div class="mb-3">
                <label class="form-label" for="p-name">Full name</label>
                <input id="p-name" v-model.trim="form.name" class="form-control"
                       required maxlength="120" />
              </div>
              <div class="mb-3">
                <label class="form-label" for="p-email">Email</label>
                <input id="p-email" class="form-control" :value="student ? student.email : ''"
                       disabled readonly />
                <div class="form-text">Contact the placement cell to change your email.</div>
              </div>
              <div class="row">
                <div class="col-md-4 mb-3">
                  <label class="form-label" for="p-branch">Branch</label>
                  <input id="p-branch" v-model.trim="form.branch" class="form-control"
                         placeholder="e.g. CSE" maxlength="100" />
                </div>
                <div class="col-md-4 mb-3">
                  <label class="form-label" for="p-cgpa">CGPA</label>
                  <input id="p-cgpa" v-model="form.cgpa" type="number" step="0.01"
                         min="0" max="10" class="form-control" placeholder="0 – 10" />
                </div>
                <div class="col-md-4 mb-3">
                  <label class="form-label" for="p-year">Graduation year</label>
                  <input id="p-year" v-model="form.graduation_year" type="number"
                         min="1990" max="2100" class="form-control" placeholder="e.g. 2027" />
                </div>
              </div>
              <div class="mb-3">
                <label class="form-label" for="p-phone">Phone <span class="text-muted">(optional)</span></label>
                <input id="p-phone" v-model.trim="form.phone" class="form-control" maxlength="20" />
              </div>
              <button class="btn btn-primary" type="submit" :disabled="saving">
                {{ saving ? 'Saving…' : 'Save profile' }}
              </button>
            </form>
          </div>
        </div>
      </div>

      <div class="col-12 col-lg-5">
        <div class="card shadow-sm h-100">
          <div class="card-body p-4">
            <h2 class="h5 mb-1">Resume</h2>
            <p class="text-muted small mb-4">
              PDF or Word document, up to 5 MB. Companies see this with your application.
            </p>

            <div v-if="student && student.has_resume" class="alert alert-success py-2 small">
              <div><strong>{{ student.resume_name }}</strong></div>
              <div class="text-muted">Uploaded {{ formatDate(student.resume_uploaded_at) }}</div>
            </div>
            <div v-else class="alert alert-warning py-2 small">
              No resume uploaded yet.
            </div>

            <label class="form-label" for="p-resume">
              {{ student && student.has_resume ? 'Replace resume' : 'Upload resume' }}
            </label>
            <input id="p-resume" ref="resumeInput" type="file" class="form-control"
                   accept=".pdf,.doc,.docx" :disabled="uploading" @change="uploadResume" />
            <div class="form-text mb-3">Accepted formats: .pdf, .doc, .docx</div>

            <div v-if="uploading" class="text-muted small mb-2">
              <span class="spinner-border spinner-border-sm me-1"></span> Uploading…
            </div>

            <button v-if="student && student.has_resume" class="btn btn-outline-primary btn-sm"
                    @click="downloadResume">Download my resume</button>
          </div>
        </div>
      </div>
    </div>
  `,
};
