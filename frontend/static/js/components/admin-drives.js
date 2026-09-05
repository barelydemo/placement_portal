/** Admin drive approval queue — filter, search, approve/reject. */
window.PPA = window.PPA || {};
window.PPA.components = window.PPA.components || {};

window.PPA.components.AdminDrives = {
  setup() {
    const { ref, onMounted } = Vue;
    const store = window.PPA.store;

    const drives = ref([]);
    const loading = ref(true);
    const error = ref("");
    const notice = ref("");
    const statusFilter = ref("pending");
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
        const data = await store.api(`/api/admin/drives${query ? "?" + query : ""}`);
        drives.value = data.drives;
      } catch (err) {
        error.value = err.message;
      } finally {
        loading.value = false;
      }
    }

    async function act(drive, path, body, confirmText) {
      if (confirmText && !window.confirm(confirmText)) return;
      busyId.value = drive.id;
      error.value = "";
      notice.value = "";
      try {
        const data = await store.api(`/api/admin/drives/${drive.id}/${path}`, {
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

    function badgeClass(status) {
      if (status === "Approved") return "text-bg-success";
      if (status === "Rejected") return "text-bg-danger";
      if (status === "Closed") return "text-bg-secondary";
      return "text-bg-warning";
    }

    function formatDate(iso) {
      return iso ? new Date(iso).toLocaleString() : "—";
    }

    onMounted(load);

    return {
      drives, loading, error, notice, statusFilter, search, busyId,
      rejectingId, rejectReason, load, badgeClass, formatDate,
      approve: (drive) => act(drive, "approve", null, `Approve "${drive.job_title}"?`),
      startReject: (drive) => { rejectingId.value = drive.id; rejectReason.value = ""; },
      confirmReject: (drive) => act(drive, "reject", { reason: rejectReason.value }),
    };
  },
  template: `
    <div>
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h1 class="h4 mb-1">Placement drive queue</h1>
          <p class="text-muted small mb-0">Approved drives become visible to students.</p>
        </div>
        <span class="badge text-bg-dark">{{ drives.length }} shown</span>
      </div>

      <div class="card shadow-sm mb-3">
        <div class="card-body">
          <form class="row g-2 align-items-end" @submit.prevent="load">
            <div class="col-md-4">
              <label class="form-label small mb-1" for="dq-status">Status</label>
              <select id="dq-status" v-model="statusFilter" class="form-select" @change="load">
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label small mb-1" for="dq-search">Search job title or company</label>
              <input id="dq-search" v-model="search" class="form-control" placeholder="e.g. Engineer" />
            </div>
            <div class="col-md-2 d-grid">
              <button class="btn btn-primary" type="submit">Search</button>
            </div>
          </form>
        </div>
      </div>

      <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
      <div v-if="notice" class="alert alert-success py-2">{{ notice }}</div>
      <div v-if="loading" class="text-muted">Loading drives…</div>
      <div v-else-if="!drives.length" class="alert alert-info">No drives match this filter.</div>

      <div v-else class="card shadow-sm">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Drive</th><th>Eligibility</th><th>Deadline</th>
                <th>Status</th><th class="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="drive in drives" :key="drive.id">
                <tr>
                  <td>
                    <div class="fw-semibold">{{ drive.job_title }}</div>
                    <div class="small text-muted">{{ drive.company_name }}</div>
                  </td>
                  <td class="small">
                    <div v-if="drive.eligible_branches.length">{{ drive.eligible_branches.join(', ') }}</div>
                    <div v-else class="text-muted">All branches</div>
                    <div v-if="drive.min_cgpa !== null">CGPA ≥ {{ drive.min_cgpa }}</div>
                    <div v-if="drive.eligible_years.length">{{ drive.eligible_years.join(', ') }}</div>
                  </td>
                  <td class="small">
                    {{ formatDate(drive.application_deadline) }}
                    <span v-if="drive.is_past_deadline" class="badge text-bg-secondary">passed</span>
                  </td>
                  <td>
                    <span class="badge" :class="badgeClass(drive.status)">{{ drive.status }}</span>
                    <div v-if="drive.rejection_reason" class="small text-muted mt-1">{{ drive.rejection_reason }}</div>
                  </td>
                  <td class="text-end text-nowrap">
                    <button class="btn btn-sm btn-success me-1"
                            :disabled="busyId === drive.id || drive.status === 'Approved'"
                            @click="approve(drive)">Approve</button>
                    <button class="btn btn-sm btn-outline-danger"
                            :disabled="busyId === drive.id || drive.status === 'Rejected'"
                            @click="startReject(drive)">Reject</button>
                  </td>
                </tr>
                <tr v-if="rejectingId === drive.id" class="table-light">
                  <td colspan="5">
                    <div class="d-flex gap-2 align-items-center">
                      <input v-model.trim="rejectReason" class="form-control form-control-sm"
                             maxlength="500" placeholder="Reason for rejection (optional)" />
                      <button class="btn btn-sm btn-danger text-nowrap" @click="confirmReject(drive)">
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
