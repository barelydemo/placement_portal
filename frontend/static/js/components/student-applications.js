/** Student's applications — current and past (placement history), with filters. */
window.PPA = window.PPA || {};
window.PPA.components = window.PPA.components || {};

window.PPA.components.StudentApplications = {
  setup() {
    const { ref, computed, onMounted, onUnmounted } = Vue;
    const store = window.PPA.store;

    const applications = ref([]);
    const loading = ref(true);
    const error = ref("");
    const statusFilter = ref("");

    // --- Async CSV export (Celery) ---
    const exportState = ref("idle"); // idle | working | ready | failed
    const exportMessage = ref("");
    const downloadUrl = ref("");
    let pollTimer = null;

    async function load() {
      loading.value = true;
      error.value = "";
      const query = statusFilter.value ? `?status=${encodeURIComponent(statusFilter.value)}` : "";
      try {
        const data = await store.api(`/api/student/applications${query}`);
        applications.value = data.applications;
      } catch (err) {
        error.value = err.message;
      } finally {
        loading.value = false;
      }
    }

    function badgeClass(status) {
      if (status === "Selected") return "text-bg-success";
      if (status === "Shortlisted") return "text-bg-info";
      if (status === "Rejected") return "text-bg-danger";
      return "text-bg-primary";
    }

    function formatDate(iso) {
      return iso ? new Date(iso).toLocaleString() : "—";
    }

    const summary = computed(() => {
      const counts = { Applied: 0, Shortlisted: 0, Selected: 0, Rejected: 0 };
      applications.value.forEach((item) => {
        if (counts[item.status] !== undefined) counts[item.status] += 1;
      });
      return counts;
    });

    /** Kick off the export, then poll until the worker finishes. */
    async function startExport() {
      exportState.value = "working";
      exportMessage.value = "Preparing your export…";
      downloadUrl.value = "";
      try {
        const data = await store.api("/api/student/applications/export", { method: "POST" });
        pollTask(data.task_id, data.download_url);
      } catch (err) {
        exportState.value = "failed";
        exportMessage.value = err.message;
      }
    }

    function pollTask(taskId, url) {
      let attempts = 0;
      clearInterval(pollTimer);
      pollTimer = setInterval(async () => {
        attempts += 1;
        try {
          const status = await store.api(`/api/tasks/${taskId}/status`);
          if (status.successful) {
            clearInterval(pollTimer);
            exportState.value = "ready";
            const rows = status.result ? status.result.row_count : 0;
            exportMessage.value = `Your export is ready (${rows} application(s)).`;
            downloadUrl.value = url;
          } else if (status.ready) {
            clearInterval(pollTimer);
            exportState.value = "failed";
            exportMessage.value = "The export failed. Please try again.";
          } else if (attempts > 20) {
            clearInterval(pollTimer);
            exportState.value = "failed";
            exportMessage.value =
              "Still queued after 60s — is the Celery worker running?";
          }
        } catch (err) {
          clearInterval(pollTimer);
          exportState.value = "failed";
          exportMessage.value = err.message;
        }
      }, 3000);
    }

    /** Download through fetch so the Authorization header is sent. */
    async function downloadExport() {
      try {
        const response = await fetch(downloadUrl.value, {
          headers: { Authorization: `Bearer ${store.state.token}` },
        });
        if (!response.ok) throw new Error("Download failed.");
        const blob = await response.blob();
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "my_applications.csv";
        link.click();
        URL.revokeObjectURL(link.href);
      } catch (err) {
        exportState.value = "failed";
        exportMessage.value = err.message;
      }
    }

    onMounted(load);
    onUnmounted(() => clearInterval(pollTimer));

    return {
      applications, loading, error, statusFilter, load, badgeClass, formatDate, summary,
      exportState, exportMessage, downloadUrl, startExport, downloadExport,
    };
  },
  template: `
    <div>
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h1 class="h4 mb-1">My applications</h1>
          <p class="text-muted small mb-0">Your current applications and placement history.</p>
        </div>
        <div class="d-flex gap-2">
          <button class="btn btn-outline-secondary btn-sm" :disabled="exportState === 'working'"
                  @click="startExport">
            <span v-if="exportState === 'working'" class="spinner-border spinner-border-sm me-1"
                  role="status" aria-hidden="true"></span>
            {{ exportState === 'working' ? 'Exporting…' : 'Export my applications' }}
          </button>
          <a class="btn btn-outline-primary btn-sm" href="#/student">Browse drives</a>
        </div>
      </div>

      <div v-if="exportState !== 'idle'" class="alert py-2 d-flex align-items-center gap-2"
           :class="exportState === 'ready' ? 'alert-success' : (exportState === 'failed' ? 'alert-danger' : 'alert-info')">
        <span>{{ exportMessage }}</span>
        <button v-if="exportState === 'ready'" class="btn btn-sm btn-success ms-auto"
                @click="downloadExport">Download CSV</button>
      </div>

      <div class="row g-2 mb-3">
        <div class="col-6 col-md-3" v-for="(count, label) in summary" :key="label">
          <div class="card text-center shadow-sm">
            <div class="card-body py-2">
              <div class="h5 mb-0">{{ count }}</div>
              <div class="small text-muted">{{ label }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="card shadow-sm mb-3">
        <div class="card-body py-2">
          <label class="form-label small mb-1" for="a-status">Filter by status</label>
          <select id="a-status" v-model="statusFilter" class="form-select" @change="load">
            <option value="">All applications</option>
            <option value="Applied">Applied</option>
            <option value="Shortlisted">Shortlisted</option>
            <option value="Selected">Selected</option>
            <option value="Rejected">Rejected</option>
          </select>
        </div>
      </div>

      <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
      <div v-if="loading" class="text-muted">Loading applications…</div>
      <div v-else-if="!applications.length" class="alert alert-info">
        No applications yet. Browse the open drives to apply.
      </div>

      <div v-else class="card shadow-sm">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Role</th><th>Company</th><th>Applied on</th>
                <th>Interview</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in applications" :key="item.id">
                <td class="fw-semibold">{{ item.drive ? item.drive.job_title : '—' }}</td>
                <td class="small">{{ item.drive ? item.drive.company_name : '—' }}</td>
                <td class="small">{{ formatDate(item.applied_at) }}</td>
                <td class="small">
                  <span v-if="item.interview_datetime">{{ formatDate(item.interview_datetime) }}</span>
                  <span v-else class="text-muted">Not scheduled</span>
                </td>
                <td><span class="badge" :class="badgeClass(item.status)">{{ item.status }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `,
};
