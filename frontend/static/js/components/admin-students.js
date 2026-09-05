/** Admin students table — search by name/email/branch, blacklist/reinstate. */
window.PPA = window.PPA || {};
window.PPA.components = window.PPA.components || {};

window.PPA.components.AdminStudents = {
  setup() {
    const { ref, onMounted } = Vue;
    const store = window.PPA.store;

    const students = ref([]);
    const loading = ref(true);
    const error = ref("");
    const notice = ref("");
    const search = ref("");
    const activeFilter = ref("");
    const busyId = ref(null);

    async function load() {
      loading.value = true;
      error.value = "";
      const params = new URLSearchParams();
      if (search.value.trim()) params.set("search", search.value.trim());
      if (activeFilter.value !== "") params.set("active", activeFilter.value);
      const query = params.toString();
      try {
        const data = await store.api(`/api/admin/students${query ? "?" + query : ""}`);
        students.value = data.students;
      } catch (err) {
        error.value = err.message;
      } finally {
        loading.value = false;
      }
    }

    async function toggleActive(student) {
      const warning = student.is_active
        ? `Blacklist ${student.name}? They will no longer be able to log in.`
        : `Reinstate ${student.name}? They will be able to log in again.`;
      if (!window.confirm(warning)) return;

      busyId.value = student.id;
      error.value = "";
      notice.value = "";
      try {
        const data = await store.api(`/api/admin/students/${student.id}/deactivate`, {
          method: "PUT",
          body: { is_active: !student.is_active },
        });
        notice.value = data.message;
        await load();
      } catch (err) {
        error.value = err.message;
      } finally {
        busyId.value = null;
      }
    }

    onMounted(load);

    return { students, loading, error, notice, search, activeFilter, busyId, load, toggleActive };
  },
  template: `
    <div>
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h1 class="h4 mb-1">Registered students</h1>
          <p class="text-muted small mb-0">Search the student body and manage access.</p>
        </div>
        <span class="badge text-bg-dark">{{ students.length }} shown</span>
      </div>

      <div class="card shadow-sm mb-3">
        <div class="card-body">
          <form class="row g-2 align-items-end" @submit.prevent="load">
            <div class="col-md-6">
              <label class="form-label small mb-1" for="st-search">Search by name, email or branch</label>
              <input id="st-search" v-model="search" class="form-control" placeholder="e.g. CSE or priya" />
            </div>
            <div class="col-md-4">
              <label class="form-label small mb-1" for="st-active">Account state</label>
              <select id="st-active" v-model="activeFilter" class="form-select" @change="load">
                <option value="">All students</option>
                <option value="true">Active only</option>
                <option value="false">Blacklisted only</option>
              </select>
            </div>
            <div class="col-md-2 d-grid">
              <button class="btn btn-primary" type="submit">Search</button>
            </div>
          </form>
        </div>
      </div>

      <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
      <div v-if="notice" class="alert alert-success py-2">{{ notice }}</div>
      <div v-if="loading" class="text-muted">Loading students…</div>
      <div v-else-if="!students.length" class="alert alert-info">No students match this search.</div>

      <div v-else class="card shadow-sm">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Student</th><th>Branch</th><th>CGPA</th><th>Batch</th>
                <th>Applications</th><th>Account</th><th class="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="student in students" :key="student.id">
                <td>
                  <div class="fw-semibold">{{ student.name }}</div>
                  <div class="small text-muted">{{ student.email }}</div>
                </td>
                <td class="small">{{ student.branch || '—' }}</td>
                <td class="small">{{ student.cgpa !== null ? student.cgpa : '—' }}</td>
                <td class="small">{{ student.graduation_year || '—' }}</td>
                <td><span class="badge text-bg-light text-dark">{{ student.applications_count }}</span></td>
                <td>
                  <span class="badge" :class="student.is_active ? 'text-bg-secondary' : 'text-bg-danger'">
                    {{ student.is_active ? 'Active' : 'Blacklisted' }}
                  </span>
                </td>
                <td class="text-end">
                  <button class="btn btn-sm" :class="student.is_active ? 'btn-outline-dark' : 'btn-outline-secondary'"
                          :disabled="busyId === student.id" @click="toggleActive(student)">
                    {{ student.is_active ? 'Blacklist' : 'Reinstate' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `,
};
