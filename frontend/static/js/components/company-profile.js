/** Company dashboard — approval status card + profile edit form. */
window.PPA = window.PPA || {};
window.PPA.components = window.PPA.components || {};

window.PPA.components.CompanyDashboard = {
  setup() {
    const { ref, reactive, onMounted, computed } = Vue;
    const store = window.PPA.store;

    const company = ref(null);
    const loading = ref(true);
    const error = ref("");
    const success = ref("");
    const editing = ref(false);
    const saving = ref(false);

    const form = reactive({ company_name: "", hr_contact: "", website: "" });

    const statusClass = computed(() => {
      const status = company.value && company.value.approval_status;
      if (status === "Approved") return "text-bg-success";
      if (status === "Rejected") return "text-bg-danger";
      return "text-bg-warning";
    });

    async function load() {
      loading.value = true;
      error.value = "";
      try {
        const data = await store.api("/api/company/profile");
        company.value = data.company;
      } catch (err) {
        error.value = err.message;
      } finally {
        loading.value = false;
      }
    }

    function startEdit() {
      form.company_name = company.value.company_name || "";
      form.hr_contact = company.value.hr_contact || "";
      form.website = company.value.website || "";
      success.value = "";
      error.value = "";
      editing.value = true;
    }

    async function save() {
      saving.value = true;
      error.value = "";
      success.value = "";
      try {
        const data = await store.api("/api/company/profile", { method: "PUT", body: { ...form } });
        company.value = data.company;
        success.value = data.message;
        editing.value = false;
        // Keep the navbar name in sync with the renamed company.
        if (store.state.user) store.state.user.name = data.company.company_name;
      } catch (err) {
        error.value = err.message;
      } finally {
        saving.value = false;
      }
    }

    onMounted(load);

    return { company, loading, error, success, editing, saving, form, statusClass, startEdit, save };
  },
  template: `
    <div class="row justify-content-center">
      <div class="col-12 col-lg-8">

        <div v-if="loading" class="text-muted">Loading profile…</div>
        <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
        <div v-if="success" class="alert alert-success py-2">{{ success }}</div>

        <div v-if="company" class="card shadow-sm mb-4">
          <div class="card-body p-4">
            <div class="d-flex justify-content-between align-items-start mb-3">
              <div>
                <h1 class="h4 mb-1">{{ company.company_name }}</h1>
                <p class="text-muted small mb-0">{{ company.email }}</p>
              </div>
              <span class="badge fs-6" :class="statusClass">{{ company.approval_status }}</span>
            </div>

            <div v-if="company.approval_status === 'Pending'" class="alert alert-warning py-2 small">
              Your registration is awaiting admin approval. You will be able to post placement
              drives once approved.
            </div>
            <div v-else-if="company.approval_status === 'Rejected'" class="alert alert-danger py-2 small">
              Your registration was rejected.
              <span v-if="company.rejection_reason"><strong>Reason:</strong> {{ company.rejection_reason }}</span>
            </div>
            <div v-else class="alert alert-success py-2 small">
              Approved — you can post placement drives.
            </div>

            <dl class="row small mb-0">
              <dt class="col-sm-3">HR contact</dt>
              <dd class="col-sm-9">{{ company.hr_contact || '—' }}</dd>
              <dt class="col-sm-3">Website</dt>
              <dd class="col-sm-9">
                <a v-if="company.website" :href="company.website" target="_blank" rel="noopener">{{ company.website }}</a>
                <span v-else>—</span>
              </dd>
              <dt class="col-sm-3">Account</dt>
              <dd class="col-sm-9">
                <span class="badge" :class="company.is_active ? 'text-bg-secondary' : 'text-bg-danger'">
                  {{ company.is_active ? 'Active' : 'Deactivated' }}
                </span>
              </dd>
            </dl>

            <button v-if="!editing" class="btn btn-outline-primary btn-sm mt-3" @click="startEdit">
              Edit profile
            </button>
          </div>
        </div>

        <div v-if="editing" class="card shadow-sm">
          <div class="card-body p-4">
            <h2 class="h5 mb-3">Edit company profile</h2>
            <div v-if="company && company.approval_status !== 'Pending'" class="alert alert-warning py-2 small">
              Saving changes sends your profile back to <strong>Pending</strong> for admin re-approval.
            </div>
            <form @submit.prevent="save">
              <div class="mb-3">
                <label class="form-label" for="e-name">Company name</label>
                <input id="e-name" v-model.trim="form.company_name" class="form-control" required maxlength="120" />
              </div>
              <div class="mb-3">
                <label class="form-label" for="e-hr">HR contact</label>
                <input id="e-hr" v-model.trim="form.hr_contact" class="form-control" required maxlength="120" />
              </div>
              <div class="mb-3">
                <label class="form-label" for="e-web">Website <span class="text-muted">(optional)</span></label>
                <input id="e-web" v-model.trim="form.website" class="form-control" placeholder="example.com" />
              </div>
              <button class="btn btn-primary" type="submit" :disabled="saving">
                {{ saving ? 'Saving…' : 'Save changes' }}
              </button>
              <button class="btn btn-link" type="button" @click="editing = false">Cancel</button>
            </form>
          </div>
        </div>

      </div>
    </div>
  `,
};
