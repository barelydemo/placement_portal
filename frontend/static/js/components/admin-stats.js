/** Admin dashboard home — portal statistics (served from Redis cache). */
window.PPA = window.PPA || {};
window.PPA.components = window.PPA.components || {};

window.PPA.components.AdminStats = {
  setup() {
    const { ref, onMounted } = Vue;
    const store = window.PPA.store;

    const stats = ref(null);
    const cached = ref(false);
    const loading = ref(true);
    const error = ref("");
    const jobNotice = ref("");
    const jobBusy = ref("");

    /** Queue a background job and report the outcome (Celery). */
    async function triggerJob(path, label) {
      jobBusy.value = label;
      jobNotice.value = "";
      error.value = "";
      try {
        const data = await store.api(path, { method: "POST" });
        jobNotice.value = `${data.message} (task ${data.task_id.slice(0, 8)}…)`;
      } catch (err) {
        error.value = err.message;
      } finally {
        jobBusy.value = "";
      }
    }

    async function load() {
      loading.value = true;
      error.value = "";
      try {
        const data = await store.api("/api/admin/stats");
        stats.value = data.stats;
        cached.value = data.cached;
      } catch (err) {
        error.value = err.message;
      } finally {
        loading.value = false;
      }
    }

    onMounted(load);

    return { stats, cached, loading, error, load, jobNotice, jobBusy, triggerJob };
  },
  template: `
    <div>
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h1 class="h4 mb-1">Placement cell overview</h1>
          <p class="text-muted small mb-0">Live counts across the portal.</p>
        </div>
        <div class="d-flex align-items-center gap-2">
          <span class="badge" :class="cached ? 'text-bg-info' : 'text-bg-secondary'">
            {{ cached ? 'from cache' : 'fresh' }}
          </span>
          <button class="btn btn-sm btn-outline-primary" @click="load">Refresh</button>
        </div>
      </div>

      <div class="card shadow-sm mb-4">
        <div class="card-body d-flex flex-wrap align-items-center gap-2">
          <div class="me-auto">
            <div class="fw-semibold">Background jobs</div>
            <div class="small text-muted">
              Normally run on Celery beat — trigger them now for a demo.
            </div>
          </div>
          <button class="btn btn-sm btn-outline-dark" :disabled="jobBusy !== ''"
                  @click="triggerJob('/api/admin/reports/monthly/trigger', 'report')">
            {{ jobBusy === 'report' ? 'Queueing…' : 'Trigger monthly report' }}
          </button>
          <button class="btn btn-sm btn-outline-dark" :disabled="jobBusy !== ''"
                  @click="triggerJob('/api/admin/reminders/trigger', 'reminders')">
            {{ jobBusy === 'reminders' ? 'Queueing…' : 'Send daily reminders' }}
          </button>
        </div>
      </div>

      <div v-if="jobNotice" class="alert alert-success py-2">{{ jobNotice }}</div>
      <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
      <div v-if="loading" class="text-muted">Loading stats…</div>

      <div v-else-if="stats">
        <div class="row g-3 mb-4">
          <div class="col-6 col-lg-3">
            <div class="card shadow-sm h-100">
              <div class="card-body">
                <div class="text-muted small">Students</div>
                <div class="display-6 fw-bold">{{ stats.students.total }}</div>
                <div class="small text-muted">
                  {{ stats.students.active }} active · {{ stats.students.deactivated }} blacklisted
                </div>
              </div>
            </div>
          </div>
          <div class="col-6 col-lg-3">
            <div class="card shadow-sm h-100">
              <div class="card-body">
                <div class="text-muted small">Companies</div>
                <div class="display-6 fw-bold">{{ stats.companies.total }}</div>
                <div class="small text-muted">
                  {{ stats.companies.approved }} approved · {{ stats.companies.pending }} pending
                </div>
              </div>
            </div>
          </div>
          <div class="col-6 col-lg-3">
            <div class="card shadow-sm h-100">
              <div class="card-body">
                <div class="text-muted small">Drives</div>
                <div class="display-6 fw-bold">{{ stats.drives.total }}</div>
                <div class="small text-muted">
                  {{ stats.drives.approved }} approved · {{ stats.drives.pending }} pending
                </div>
              </div>
            </div>
          </div>
          <div class="col-6 col-lg-3">
            <div class="card shadow-sm h-100">
              <div class="card-body">
                <div class="text-muted small">Applications</div>
                <div class="display-6 fw-bold">{{ stats.applications.total }}</div>
                <div class="small text-muted">{{ stats.applications.selected }} selected</div>
              </div>
            </div>
          </div>
        </div>

        <div class="row g-3">
          <div class="col-12 col-lg-6">
            <div class="card shadow-sm h-100">
              <div class="card-body">
                <h2 class="h6 mb-3">Awaiting your approval</h2>
                <div class="d-flex align-items-center justify-content-between mb-2">
                  <span>Companies pending</span>
                  <a href="#/admin/companies" class="badge text-bg-warning text-decoration-none">
                    {{ stats.companies.pending }}
                  </a>
                </div>
                <div class="d-flex align-items-center justify-content-between">
                  <span>Drives pending</span>
                  <a href="#/admin/drives" class="badge text-bg-warning text-decoration-none">
                    {{ stats.drives.pending }}
                  </a>
                </div>
                <hr />
                <div class="d-flex align-items-center justify-content-between">
                  <strong>Total pending actions</strong>
                  <span class="badge text-bg-dark">{{ stats.pending_approvals }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="col-12 col-lg-6">
            <div class="card shadow-sm h-100">
              <div class="card-body">
                <h2 class="h6 mb-3">Applications by status</h2>
                <div v-for="(count, label) in stats.applications.by_status" :key="label"
                     class="d-flex align-items-center justify-content-between mb-2">
                  <span>{{ label }}</span>
                  <span class="badge text-bg-secondary">{{ count }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
};
