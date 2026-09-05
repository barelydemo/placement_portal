/** Company drives — create form (gated on approval) + list with status/counts. */
window.PPA = window.PPA || {};
window.PPA.components = window.PPA.components || {};

window.PPA.components.CompanyDrives = {
  setup() {
    const { ref, reactive, onMounted, computed } = Vue;
    const store = window.PPA.store;

    const drives = ref([]);
    const company = ref(null);
    const loading = ref(true);
    const error = ref("");
    const notice = ref("");
    const showForm = ref(false);
    const saving = ref(false);

    const openDriveId = ref(null);
    const applicants = ref([]);
    const applicantsLoading = ref(false);
    const savingId = ref(null);

    const blank = {
      job_title: "",
      job_description: "",
      eligible_branches: "",
      min_cgpa: "",
      eligible_years: "",
      application_deadline: "",
    };
    const form = reactive({ ...blank });

    const isApproved = computed(
      () => company.value && company.value.approval_status === "Approved"
    );

    async function load() {
      loading.value = true;
      error.value = "";
      try {
        const [profileData, driveData] = await Promise.all([
          store.api("/api/company/profile"),
          store.api("/api/company/drives"),
        ]);
        company.value = profileData.company;
        drives.value = driveData.drives;
      } catch (err) {
        error.value = err.message;
      } finally {
        loading.value = false;
      }
    }

    async function submit() {
      saving.value = true;
      error.value = "";
      notice.value = "";
      try {
        const data = await store.api("/api/company/drives", { method: "POST", body: { ...form } });
        notice.value = data.message;
        Object.assign(form, blank);
        showForm.value = false;
        await load();
      } catch (err) {
        error.value = err.message;
      } finally {
        saving.value = false;
      }
    }

    async function close(drive) {
      if (!window.confirm(`Close "${drive.job_title}"? Students will no longer see it.`)) return;
      error.value = "";
      notice.value = "";
      try {
        const data = await store.api(`/api/company/drives/${drive.id}/close`, { method: "PUT" });
        notice.value = data.message;
        await load();
      } catch (err) {
        error.value = err.message;
      }
    }

    function badgeClass(status) {
      if (status === "Approved") return "text-bg-success";
      if (status === "Rejected") return "text-bg-danger";
      if (status === "Closed") return "text-bg-secondary";
      return "text-bg-warning";
    }

    function formatDate(iso) {
      if (!iso) return "—";
      return new Date(iso).toLocaleString();
    }

    /** Expand/collapse the applicant panel for a drive. */
    async function toggleApplicants(drive) {
      if (openDriveId.value === drive.id) {
        openDriveId.value = null;
        return;
      }
      openDriveId.value = drive.id;
      applicants.value = [];
      applicantsLoading.value = true;
      error.value = "";
      try {
        const data = await store.api(`/api/company/drives/${drive.id}/applications`);
        // Local edit buffers so a dropdown change doesn't post until "Save".
        applicants.value = data.applications.map((item) => ({
          ...item,
          draftStatus: item.status,
          draftInterview: item.interview_datetime ? item.interview_datetime.slice(0, 16) : "",
        }));
      } catch (err) {
        error.value = err.message;
      } finally {
        applicantsLoading.value = false;
      }
    }

    async function saveApplicant(item) {
      savingId.value = item.id;
      error.value = "";
      notice.value = "";
      try {
        const data = await store.api(`/api/company/applications/${item.id}/status`, {
          method: "PUT",
          body: {
            status: item.draftStatus,
            interview_datetime: item.draftInterview || null,
          },
        });
        notice.value = data.message;
        item.status = data.application.status;
        item.interview_datetime = data.application.interview_datetime;
      } catch (err) {
        error.value = err.message;
      } finally {
        savingId.value = null;
      }
    }

    /** Fetch a protected file/document and hand it to the browser. */
    async function fetchAsBlob(url) {
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${store.state.token}` },
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "Request failed.");
      }
      return response.blob();
    }

    async function downloadResume(item) {
      error.value = "";
      try {
        const blob = await fetchAsBlob(`/api/company/applications/${item.id}/resume`);
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `resume_${item.student ? item.student.name : item.id}`;
        link.click();
        URL.revokeObjectURL(link.href);
      } catch (err) {
        error.value = err.message;
      }
    }

    async function openOfferLetter(item) {
      error.value = "";
      try {
        const params = new URLSearchParams();
        const ctc = window.prompt("Annual CTC for the offer letter (optional):", "");
        if (ctc) params.set("ctc", ctc);
        const joining = window.prompt("Date of joining (optional):", "");
        if (joining) params.set("joining_date", joining);

        const query = params.toString();
        const blob = await fetchAsBlob(
          `/api/company/applications/${item.id}/offer-letter${query ? "?" + query : ""}`
        );
        // Open in a new tab so the company can review and print to PDF.
        const url = URL.createObjectURL(blob);
        window.open(url, "_blank");
      } catch (err) {
        error.value = err.message;
      }
    }

    function statusBadge(status) {
      if (status === "Selected") return "text-bg-success";
      if (status === "Shortlisted") return "text-bg-info";
      if (status === "Rejected") return "text-bg-danger";
      return "text-bg-primary";
    }

    onMounted(load);

    return {
      drives, company, loading, error, notice, showForm, saving, form,
      isApproved, submit, close, badgeClass, formatDate,
      openDriveId, applicants, applicantsLoading, savingId,
      toggleApplicants, saveApplicant, statusBadge, downloadResume, openOfferLetter,
    };
  },
  template: `
    <div>
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h1 class="h4 mb-1">My placement drives</h1>
          <p class="text-muted small mb-0">Drives go live to students only after admin approval.</p>
        </div>
        <button v-if="isApproved" class="btn btn-primary" @click="showForm = !showForm">
          {{ showForm ? 'Cancel' : 'Create drive' }}
        </button>
      </div>

      <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
      <div v-if="notice" class="alert alert-success py-2">{{ notice }}</div>

      <div v-if="company && !isApproved" class="alert alert-warning">
        <strong>You cannot post drives yet.</strong>
        Your company is currently <strong>{{ company.approval_status }}</strong>.
        <span v-if="company.approval_status === 'Pending'">An admin must approve your company first.</span>
        <span v-else-if="company.rejection_reason">Reason: {{ company.rejection_reason }}</span>
      </div>

      <div v-if="showForm && isApproved" class="card shadow-sm mb-4">
        <div class="card-body p-4">
          <h2 class="h5 mb-3">New placement drive</h2>
          <form @submit.prevent="submit">
            <div class="mb-3">
              <label class="form-label" for="d-title">Job title</label>
              <input id="d-title" v-model.trim="form.job_title" class="form-control" required maxlength="200" />
            </div>
            <div class="mb-3">
              <label class="form-label" for="d-desc">Job description</label>
              <textarea id="d-desc" v-model.trim="form.job_description" class="form-control"
                        rows="4" required maxlength="5000"></textarea>
            </div>
            <div class="row">
              <div class="col-md-4 mb-3">
                <label class="form-label" for="d-branch">Eligible branches</label>
                <input id="d-branch" v-model.trim="form.eligible_branches" class="form-control"
                       placeholder="CSE, ECE (blank = all)" />
              </div>
              <div class="col-md-4 mb-3">
                <label class="form-label" for="d-cgpa">Minimum CGPA</label>
                <input id="d-cgpa" v-model="form.min_cgpa" type="number" step="0.01" min="0" max="10"
                       class="form-control" placeholder="blank = no bar" />
              </div>
              <div class="col-md-4 mb-3">
                <label class="form-label" for="d-years">Eligible years</label>
                <input id="d-years" v-model.trim="form.eligible_years" class="form-control"
                       placeholder="2026, 2027 (blank = all)" />
              </div>
            </div>
            <div class="mb-3">
              <label class="form-label" for="d-deadline">Application deadline</label>
              <input id="d-deadline" v-model="form.application_deadline" type="date" class="form-control" required />
              <div class="form-text">Applications close at the end of this day.</div>
            </div>
            <button class="btn btn-primary" type="submit" :disabled="saving">
              {{ saving ? 'Submitting…' : 'Submit for approval' }}
            </button>
          </form>
        </div>
      </div>

      <div v-if="loading" class="text-muted">Loading drives…</div>
      <div v-else-if="!drives.length" class="alert alert-info">
        You have not created any drives yet.
      </div>

      <div v-else class="card shadow-sm">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Job title</th><th>Eligibility</th><th>Deadline</th>
                <th>Status</th><th>Applicants</th><th class="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="drive in drives" :key="drive.id">
              <tr>
                <td>
                  <div class="fw-semibold">{{ drive.job_title }}</div>
                  <div class="small text-muted">{{ drive.job_description.slice(0, 70) }}…</div>
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
                <td><span class="badge text-bg-light text-dark">{{ drive.applicant_count }}</span></td>
                <td class="text-end text-nowrap">
                  <button class="btn btn-sm btn-outline-primary me-1" @click="toggleApplicants(drive)">
                    {{ openDriveId === drive.id ? 'Hide' : 'Applicants' }}
                  </button>
                  <button v-if="drive.status !== 'Closed'" class="btn btn-sm btn-outline-dark"
                          @click="close(drive)">Close</button>
                </td>
              </tr>

              <tr v-if="openDriveId === drive.id" class="table-light">
                <td colspan="6">
                  <div v-if="applicantsLoading" class="text-muted small">Loading applicants…</div>
                  <div v-else-if="!applicants.length" class="text-muted small">
                    No students have applied to this drive yet.
                  </div>
                  <table v-else class="table table-sm align-middle mb-0">
                    <thead>
                      <tr>
                        <th>Student</th><th>Branch / CGPA / Year</th><th>Applied</th>
                        <th>Status</th><th>Interview</th><th></th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="item in applicants" :key="item.id">
                        <td>
                          <div class="fw-semibold">{{ item.student ? item.student.name : '—' }}</div>
                          <div class="small text-muted">{{ item.student ? item.student.email : '' }}</div>
                        </td>
                        <td class="small">
                          {{ item.student && item.student.branch ? item.student.branch : '—' }} /
                          {{ item.student && item.student.cgpa !== null ? item.student.cgpa : '—' }} /
                          {{ item.student && item.student.graduation_year ? item.student.graduation_year : '—' }}
                        </td>
                        <td class="small">{{ formatDate(item.applied_at) }}</td>
                        <td>
                          <span class="badge mb-1" :class="statusBadge(item.status)">{{ item.status }}</span>
                          <select v-model="item.draftStatus" class="form-select form-select-sm">
                            <option value="Applied">Applied</option>
                            <option value="Shortlisted">Shortlisted</option>
                            <option value="Selected">Selected</option>
                            <option value="Rejected">Rejected</option>
                          </select>
                        </td>
                        <td>
                          <input v-model="item.draftInterview" type="datetime-local"
                                 class="form-control form-control-sm" />
                        </td>
                        <td class="text-nowrap">
                          <button class="btn btn-sm btn-primary mb-1" :disabled="savingId === item.id"
                                  @click="saveApplicant(item)">
                            {{ savingId === item.id ? 'Saving…' : 'Save' }}
                          </button>
                          <button class="btn btn-sm btn-outline-secondary mb-1"
                                  @click="downloadResume(item)">Resume</button>
                          <button v-if="item.status === 'Selected'"
                                  class="btn btn-sm btn-outline-success mb-1"
                                  @click="openOfferLetter(item)">Offer letter</button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
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
