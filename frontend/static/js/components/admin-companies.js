/** Admin dashboard — company list with status filter, search and row actions. */
window.PPA = window.PPA || {};
window.PPA.components = window.PPA.components || {};

window.PPA.components.AdminCompanies = {
  setup() {
    const { ref, onMounted } = Vue;
    const store = window.PPA.store;

    const companies = ref([]);
    const loading = ref(true);
    const error = ref("");
    const notice = ref("");
    const statusFilter = ref("");
    const search = ref("");
    const busyId = ref(null);
    const rejectingId = ref(null);
    const rejectReason = ref("");

    async function load() {
      loading.value = true;
      error.value = "";
      const params = new URLSearchParams();
      if (statusFilter.value) params.set("status", statusFilter.value);
      if (search.value.trim()) params.set("search", search.value.trim());
      const query = params.toString();
      try {
        const data = await store.api(`/api/admin/companies${query ? "?" + query : ""}`);
        companies.value = data.companies;
      } catch (err) {
        error.value = err.message;
      } finally {
        loading.value = false;
      }
    }

    function badgeClass(status) {
      if (status === "Approved") return "text-bg-success";
      if (status === "Rejected") return "text-bg-danger";
      return "text-bg-warning";
    }

    async function act(company, path, body, confirmText) {
      if (confirmText && !window.confirm(confirmText)) return;
      busyId.value = company.id;
      error.value = "";
      notice.value = "";
      try {
        const data = await store.api(`/api/admin/companies/${company.id}/${path}`, {
          method: "PUT",
          body: body || null,
        });
        notice.value = data.message;
        rejectingId.value = null;
        rejectReason.value = "";
        await load();
      } catch (err) {
        error.value = err.message;
      } finally {
        busyId.value = null;
      }
    }

    function approve(company) {
      act(company, "approve", null, `Approve ${company.company_name}?`);
    }

    function startReject(company) {
      rejectingId.value = company.id;
      rejectReason.value = "";
    }

    function confirmReject(company) {
      act(company, "reject", { reason: rejectReason.value });
    }

    function toggleActive(company) {
      const action = company.is_active ? "Deactivate" : "Reinstate";
      const warning = company.is_active
        ? `Deactivate ${company.company_name}? They will no longer be able to log in.`
        : `Reinstate ${company.company_name}? They will be able to log in again.`;
      act(company, "deactivate", { is_active: !company.is_active }, warning);
    }

    onMounted(load);

    return {
      companies, loading, error, notice, statusFilter, search, busyId,
      rejectingId, rejectReason, load, badgeClass, approve, startReject,
      confirmReject, toggleActive,
    };
  },
  template: `
    <div>
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h1 class="h4 mb-1">Registered companies</h1>
          <p class="text-muted small mb-0">Approve, reject or blacklist company accounts.</p>
        </div>
        <span class="badge text-bg-dark">{{ companies.length }} shown</span>
      </div>

      <div class="card shadow-sm mb-3">
        <div class="card-body">
          <form class="row g-2 align-items-end" @submit.prevent="load">
            <div class="col-md-4">
              <label class="form-label small mb-1" for="f-status">Status</label>
              <select id="f-status" v-model="statusFilter" class="form-select" @change="load">
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label small mb-1" for="f-search">Search by company name or email</label>
              <input id="f-search" v-model="search" class="form-control" placeholder="e.g. Acme" />
            </div>
            <div class="col-md-2 d-grid">
              <button class="btn btn-primary" type="submit">Search</button>
            </div>
          </form>
        </div>
      </div>

      <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
      <div v-if="notice" class="alert alert-success py-2">{{ notice }}</div>
      <div v-if="loading" class="text-muted">Loading companies…</div>

      <div v-else-if="!companies.length" class="alert alert-info">
        No companies match this filter.
      </div>

      <div v-else class="card shadow-sm">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Company</th>
                <th>HR contact</th>
                <th>Status</th>
                <th>Account</th>
                <th class="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="company in companies" :key="company.id">
                <tr>
                  <td>
                    <div class="fw-semibold">{{ company.company_name }}</div>
                    <div class="small text-muted">{{ company.email }}</div>
                    <a v-if="company.website" class="small" :href="company.website"
                       target="_blank" rel="noopener">{{ company.website }}</a>
                  </td>
                  <td class="small">{{ company.hr_contact || '—' }}</td>
                  <td>
                    <span class="badge" :class="badgeClass(company.approval_status)">
                      {{ company.approval_status }}
                    </span>
                    <div v-if="company.rejection_reason" class="small text-muted mt-1">
                      {{ company.rejection_reason }}
                    </div>
                  </td>
                  <td>
                    <span class="badge" :class="company.is_active ? 'text-bg-secondary' : 'text-bg-danger'">
                      {{ company.is_active ? 'Active' : 'Deactivated' }}
                    </span>
                  </td>
                  <td class="text-end text-nowrap">
                    <button class="btn btn-sm btn-success me-1" :disabled="busyId === company.id
                            || company.approval_status === 'Approved'" @click="approve(company)">
                      Approve
                    </button>
                    <button class="btn btn-sm btn-outline-danger me-1" :disabled="busyId === company.id
                            || company.approval_status === 'Rejected'" @click="startReject(company)">
                      Reject
                    </button>
                    <button class="btn btn-sm" :class="company.is_active ? 'btn-outline-dark' : 'btn-outline-secondary'"
                            :disabled="busyId === company.id" @click="toggleActive(company)">
                      {{ company.is_active ? 'Deactivate' : 'Reinstate' }}
                    </button>
                  </td>
                </tr>
                <tr v-if="rejectingId === company.id" class="table-light">
                  <td colspan="5">
                    <div class="d-flex gap-2 align-items-center">
                      <input v-model.trim="rejectReason" class="form-control form-control-sm"
                             maxlength="500" placeholder="Reason for rejection (optional)" />
                      <button class="btn btn-sm btn-danger text-nowrap" @click="confirmReject(company)">
                        Confirm reject
                      </button>
                      <button class="btn btn-sm btn-link" @click="rejectingId = null">Cancel</button>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `,
};
