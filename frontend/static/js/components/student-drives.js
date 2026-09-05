/** Student drive browsing — search, eligibility filters, detail modal. */
window.PPA = window.PPA || {};
window.PPA.components = window.PPA.components || {};

window.PPA.components.StudentDrives = {
  setup() {
    const { ref, onMounted } = Vue;
    const store = window.PPA.store;

    const drives = ref([]);
    const loading = ref(true);
    const error = ref("");
    const search = ref("");
    const branch = ref("");
    const cgpa = ref("");
    const eligibleOnly = ref(false);
    const selected = ref(null);
    const notice = ref("");
    const applyingId = ref(null);

    async function load() {
      loading.value = true;
      error.value = "";
      const params = new URLSearchParams();
      if (search.value.trim()) params.set("search", search.value.trim());
      if (branch.value.trim()) params.set("branch", branch.value.trim());
      if (cgpa.value !== "") params.set("cgpa", cgpa.value);
      if (eligibleOnly.value) params.set("eligible_only", "true");
      const query = params.toString();
      try {
        const data = await store.api(`/api/student/drives${query ? "?" + query : ""}`);
        drives.value = data.drives;
      } catch (err) {
        error.value = err.message;
      } finally {
        loading.value = false;
      }
    }

    function reset() {
      search.value = "";
      branch.value = "";
      cgpa.value = "";
      eligibleOnly.value = false;
      load();
    }

    async function openDetail(drive) {
      try {
        const data = await store.api(`/api/drives/${drive.id}`);
        selected.value = data.drive;
      } catch (err) {
        error.value = err.message;
      }
    }

    function formatDate(iso) {
      return iso ? new Date(iso).toLocaleString() : "—";
    }

    /** Why the Apply button is disabled, or "" when it is clickable. */
    function applyBlockedReason(drive) {
      if (drive.has_applied) return "You have already applied to this drive.";
      if (!drive.is_eligible) return "You do not meet the eligibility criteria.";
      return "";
    }

    async function apply(drive) {
      applyingId.value = drive.id;
      error.value = "";
      notice.value = "";
      try {
        const data = await store.api("/api/student/applications", {
          method: "POST",
          body: { drive_id: drive.id },
        });
        notice.value = data.message;
        drive.has_applied = true;
        if (selected.value && selected.value.id === drive.id) selected.value.has_applied = true;
      } catch (err) {
        error.value = err.message;
      } finally {
        applyingId.value = null;
      }
    }

    onMounted(load);

    return {
      drives, loading, error, notice, search, branch, cgpa, eligibleOnly, selected,
      applyingId, load, reset, openDetail, formatDate, apply, applyBlockedReason,
    };
  },
  template: `
    <div>
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h1 class="h4 mb-1">Placement drives</h1>
          <p class="text-muted small mb-0">Approved drives that are still accepting applications.</p>
        </div>
        <span class="badge text-bg-success">{{ drives.length }} open</span>
      </div>

      <div class="card shadow-sm mb-4">
        <div class="card-body">
          <form class="row g-2 align-items-end" @submit.prevent="load">
            <div class="col-md-4">
              <label class="form-label small mb-1" for="s-search">Keyword</label>
              <input id="s-search" v-model="search" class="form-control" placeholder="role, company, skill" />
            </div>
            <div class="col-md-3">
              <label class="form-label small mb-1" for="s-branch">Branch</label>
              <input id="s-branch" v-model="branch" class="form-control" placeholder="e.g. CSE" />
            </div>
            <div class="col-md-2">
              <label class="form-label small mb-1" for="s-cgpa">My CGPA</label>
              <input id="s-cgpa" v-model="cgpa" type="number" step="0.01" min="0" max="10"
                     class="form-control" placeholder="8.0" />
            </div>
            <div class="col-md-3 d-flex gap-2">
              <button class="btn btn-primary flex-grow-1" type="submit">Search</button>
              <button class="btn btn-outline-secondary" type="button" @click="reset">Reset</button>
            </div>
            <div class="col-12">
              <div class="form-check">
                <input id="s-elig" v-model="eligibleOnly" class="form-check-input" type="checkbox" @change="load" />
                <label class="form-check-label small" for="s-elig">
                  Only show drives I am eligible for
                </label>
              </div>
            </div>
          </form>
        </div>
      </div>

      <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
      <div v-if="notice" class="alert alert-success py-2">
        {{ notice }} <a href="#/student/applications" class="alert-link">View my applications</a>
      </div>
      <div v-if="loading" class="text-muted">Loading drives…</div>
      <div v-else-if="!drives.length" class="alert alert-info">
        No open drives match your filters right now.
      </div>

      <div v-else class="row g-3">
        <div v-for="drive in drives" :key="drive.id" class="col-12 col-lg-6">
          <div class="card h-100 shadow-sm">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start">
                <div>
                  <h2 class="h5 mb-1">{{ drive.job_title }}</h2>
                  <p class="text-muted small mb-2">{{ drive.company_name }}</p>
                </div>
                <span class="badge" :class="drive.is_eligible ? 'text-bg-success' : 'text-bg-secondary'">
                  {{ drive.is_eligible ? 'Eligible' : 'Not eligible' }}
                </span>
              </div>

              <p class="small mb-3">{{ drive.job_description.slice(0, 130) }}<span
                 v-if="drive.job_description.length > 130">…</span></p>

              <ul class="list-unstyled small mb-3">
                <li><strong>Branches:</strong>
                  {{ drive.eligible_branches.length ? drive.eligible_branches.join(', ') : 'All' }}</li>
                <li><strong>Min CGPA:</strong> {{ drive.min_cgpa !== null ? drive.min_cgpa : 'No bar' }}</li>
                <li><strong>Batches:</strong>
                  {{ drive.eligible_years.length ? drive.eligible_years.join(', ') : 'All' }}</li>
                <li><strong>Deadline:</strong> {{ formatDate(drive.application_deadline) }}</li>
              </ul>

              <div v-if="!drive.is_eligible && drive.ineligibility_reasons.length"
                   class="alert alert-warning py-1 px-2 small mb-3">
                <div v-for="reason in drive.ineligibility_reasons" :key="reason">{{ reason }}</div>
              </div>

              <div class="d-flex align-items-center gap-2">
                <button class="btn btn-sm btn-outline-primary" @click="openDetail(drive)">View details</button>
                <button class="btn btn-sm btn-primary" :disabled="!!applyBlockedReason(drive) || applyingId === drive.id"
                        :title="applyBlockedReason(drive)" @click="apply(drive)">
                  {{ drive.has_applied ? 'Applied' : (applyingId === drive.id ? 'Applying…' : 'Apply') }}
                </button>
                <span v-if="applyBlockedReason(drive)" class="small text-muted">
                  {{ applyBlockedReason(drive) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Detail modal (plain Vue, shown when a drive is selected) -->
      <div v-if="selected" class="modal d-block" tabindex="-1" style="background: rgba(0,0,0,.5)"
           @click.self="selected = null">
        <div class="modal-dialog modal-lg modal-dialog-scrollable">
          <div class="modal-content">
            <div class="modal-header">
              <div>
                <h5 class="modal-title">{{ selected.job_title }}</h5>
                <div class="text-muted small">{{ selected.company_name }}</div>
              </div>
              <button type="button" class="btn-close" @click="selected = null"></button>
            </div>
            <div class="modal-body">
              <span class="badge mb-3" :class="selected.is_eligible ? 'text-bg-success' : 'text-bg-secondary'">
                {{ selected.is_eligible ? 'You are eligible' : 'You are not eligible' }}
              </span>
              <div v-if="selected.ineligibility_reasons && selected.ineligibility_reasons.length"
                   class="alert alert-warning py-2 small">
                <div v-for="reason in selected.ineligibility_reasons" :key="reason">{{ reason }}</div>
              </div>

              <h6>Job description</h6>
              <p class="small" style="white-space: pre-wrap">{{ selected.job_description }}</p>

              <h6>Eligibility</h6>
              <dl class="row small">
                <dt class="col-sm-4">Branches</dt>
                <dd class="col-sm-8">{{ selected.eligible_branches.length ? selected.eligible_branches.join(', ') : 'All branches' }}</dd>
                <dt class="col-sm-4">Minimum CGPA</dt>
                <dd class="col-sm-8">{{ selected.min_cgpa !== null ? selected.min_cgpa : 'No bar' }}</dd>
                <dt class="col-sm-4">Graduation years</dt>
                <dd class="col-sm-8">{{ selected.eligible_years.length ? selected.eligible_years.join(', ') : 'All batches' }}</dd>
                <dt class="col-sm-4">Deadline</dt>
                <dd class="col-sm-8">{{ formatDate(selected.application_deadline) }}</dd>
              </dl>
            </div>
            <div class="modal-footer">
              <span v-if="applyBlockedReason(selected)" class="small text-muted me-auto">
                {{ applyBlockedReason(selected) }}
              </span>
              <button class="btn btn-secondary" @click="selected = null">Close</button>
              <button class="btn btn-primary" :disabled="!!applyBlockedReason(selected) || applyingId === selected.id"
                      @click="apply(selected)">
                {{ selected.has_applied ? 'Applied' : 'Apply' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
};
