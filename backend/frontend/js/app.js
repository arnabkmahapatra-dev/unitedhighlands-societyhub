// SocietyHub SPA logic.
(() => {
  "use strict";

  // ---------- Helpers ----------
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const money = (n) =>
    "₹" +
    Number(n || 0).toLocaleString("en-IN", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });

  const fmtDate = (s) => {
    const d = new Date(s + (s.endsWith("Z") ? "" : "Z"));
    return d.toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  function alertBox(target, msg, type = "danger") {
    const el = $(target);
    if (!el) return;
    el.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show" role="alert">
      ${esc(msg)}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>`;
    if (type === "success") setTimeout(() => (el.innerHTML = ""), 4000);
  }

  const modalEl = $("#app-modal");
  const modal = new bootstrap.Modal(modalEl);
  function showModal(title, bodyHtml, footerHtml = "") {
    $("#app-modal-content").innerHTML = `
      <div class="modal-header">
        <h5 class="modal-title">${esc(title)}</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">${bodyHtml}</div>
      ${footerHtml ? `<div class="modal-footer">${footerHtml}</div>` : ""}`;
    modal.show();
  }

  // ---------- Auth view ----------
  const authView = $("#auth-view");
  const appView = $("#app-view");

  function switchAuthTab(tab) {
    $$("#authTabs .nav-link").forEach((b) =>
      b.classList.toggle("active", b.dataset.authTab === tab)
    );
    $("#login-form").classList.toggle("d-none", tab !== "login");
    $("#otp-login-form").classList.add("d-none");
    $("#signup-form").classList.toggle("d-none", tab !== "signup");
    $("#alert-box").innerHTML = "";
  }

  $$("#authTabs .nav-link").forEach((btn) =>
    btn.addEventListener("click", () => switchAuthTab(btn.dataset.authTab))
  );

  $("#show-otp-login").addEventListener("click", (e) => {
    e.preventDefault();
    $("#login-form").classList.add("d-none");
    $("#otp-login-form").classList.remove("d-none");
  });
  $("#show-password-login").addEventListener("click", (e) => {
    e.preventDefault();
    $("#otp-login-form").classList.add("d-none");
    $("#login-form").classList.remove("d-none");
  });

  // Toggle flat field + note by signup role
  function updateSignupRole() {
    const role = $("#signup-form [name=role]:checked").value;
    $("#flat-field").classList.toggle("d-none", role !== "member");
    $("#flat-field [name=flat_no]").required = role === "member";
    $("#signup-note").textContent =
      role === "manager"
        ? "Manager accounts require approval by IT Support before you can log in."
        : "Only one registration is allowed per flat.";
  }
  $$("#signup-form [name=role]").forEach((r) =>
    r.addEventListener("change", updateSignupRole)
  );

  // Send OTP buttons
  $$("[data-send-otp]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      const form = btn.closest("form");
      const mobile = form.querySelector("[name=mobile]").value.trim();
      if (!mobile) return alertBox("#alert-box", "Enter your mobile number first.");
      btn.disabled = true;
      const original = btn.textContent;
      btn.textContent = "Sending...";
      try {
        await API.post("/auth/request-otp", { mobile, purpose: btn.dataset.sendOtp });
        alertBox("#alert-box", "OTP sent. Check your SMS (or server console in dev).", "success");
        let s = 30;
        const t = setInterval(() => {
          btn.textContent = `Resend (${s}s)`;
          if (s-- <= 0) {
            clearInterval(t);
            btn.disabled = false;
            btn.textContent = original;
          }
        }, 1000);
      } catch (err) {
        alertBox("#alert-box", err.message);
        btn.disabled = false;
        btn.textContent = original;
      }
    })
  );

  // Password login
  $("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    try {
      const data = await API.post("/auth/login", {
        mobile: f.mobile.value.trim(),
        password: f.password.value,
      });
      API.setSession(data.access_token, data.user);
      enterApp();
    } catch (err) {
      alertBox("#alert-box", err.message);
    }
  });

  // OTP login
  $("#otp-login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    try {
      const data = await API.post("/auth/login-otp", {
        mobile: f.mobile.value.trim(),
        otp: f.otp.value.trim(),
      });
      API.setSession(data.access_token, data.user);
      enterApp();
    } catch (err) {
      alertBox("#alert-box", err.message);
    }
  });

  // Signup
  $("#signup-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    const role = f.role.value;
    const payload = {
      name: f.name.value.trim(),
      mobile: f.mobile.value.trim(),
      password: f.password.value,
    };
    if (CONFIG.require_otp) payload.otp = f.otp.value.trim();
    try {
      if (role === "manager") {
        await API.post("/auth/signup/manager", payload);
        alertBox(
          "#alert-box",
          "Account created! Please wait for IT Support to approve your account, then log in.",
          "success"
        );
        f.reset();
        updateSignupRole();
        switchAuthTab("login");
      } else {
        payload.flat_no = f.flat_no.value.trim();
        const data = await API.post("/auth/signup/member", payload);
        API.setSession(data.access_token, data.user);
        enterApp();
      }
    } catch (err) {
      alertBox("#alert-box", err.message);
    }
  });

  // ---------- Navigation config ----------
  const NAV = {
    it_support: [
      ["dashboard", "Dashboard", "speedometer2"],
      ["transactions", "Transactions", "cash-stack"],
      ["broadcasts", "Broadcasts", "megaphone"],
      ["departments", "Departments", "diagram-3"],
      ["users", "Users", "people"],
    ],
    manager: [
      ["dashboard", "Dashboard", "speedometer2"],
      ["transactions", "Transactions", "cash-stack"],
      ["broadcasts", "Broadcasts", "megaphone"],
      ["mydepts", "My Departments", "diagram-3"],
    ],
    member: [
      ["dashboard", "Dashboard", "speedometer2"],
      ["transactions", "Transactions", "cash-stack"],
      ["broadcasts", "Broadcasts", "megaphone"],
    ],
  };

  let ME = null;
  const state = { departments: [], myDeptIds: [] };

  function buildNav() {
    const menu = $("#nav-menu");
    menu.innerHTML = "";
    (NAV[ME.role] || []).forEach(([key, label, icon]) => {
      const li = document.createElement("li");
      li.className = "nav-item";
      li.innerHTML = `<a class="nav-link" data-page="${key}"><i class="bi bi-${icon} me-2"></i><span>${label}</span></a>`;
      menu.appendChild(li);
    });
    $$("#nav-menu .nav-link").forEach((a) =>
      a.addEventListener("click", () => navigate(a.dataset.page))
    );
  }

  function navigate(page) {
    $$("#nav-menu .nav-link").forEach((a) =>
      a.classList.toggle("active", a.dataset.page === page)
    );
    $("#page-alert").innerHTML = "";
    const fn = PAGES[page];
    if (fn) fn();
  }

  const roleLabel = { it_support: "IT Support", manager: "Manager", member: "Member" };
  const canWrite = () => ME.role === "it_support" || ME.role === "manager";

  async function enterApp() {
    try {
      ME = await API.get("/auth/me");
    } catch (_) {
      ME = API.getUser();
    }
    if (!ME) return showAuth();
    API.setSession(null, ME);
    authView.classList.add("d-none");
    appView.classList.remove("d-none");
    $("#user-badge").innerHTML = `<i class="bi bi-person-circle me-1"></i>${esc(
      ME.name
    )} · ${roleLabel[ME.role]}${ME.flat_no ? " · " + esc(ME.flat_no) : ""}`;
    buildNav();
    try {
      state.departments = await API.get("/departments");
    } catch (_) {
      state.departments = [];
    }
    await loadMyDepartments();
    navigate("dashboard");
  }

  function showAuth() {
    appView.classList.add("d-none");
    authView.classList.remove("d-none");
  }

  $("#logout-btn").addEventListener("click", () => {
    API.clear();
    ME = null;
    location.reload();
  });

  // ---------- Pages ----------
  const content = () => $("#page-content");

  const PAGES = {
    async dashboard() {
      content().innerHTML = `<div class="text-muted">Loading…</div>`;
      const d = await API.get("/dashboard/summary");
      const stat = (cls, icon, label, val) => `
        <div class="col-6 col-lg-3">
          <div class="card stat-card ${cls} p-3 h-100">
            <div class="d-flex justify-content-between align-items-center">
              <div>
                <div class="small opacity-75">${label}</div>
                <div class="h4 mb-0 fw-bold">${val}</div>
              </div>
              <i class="bi bi-${icon} fs-2 opacity-50"></i>
            </div>
          </div>
        </div>`;

      const deptRows = d.departments
        .map(
          (dp) => `
        <tr>
          <td><span class="dept-icon me-2"><i class="bi bi-${esc(
            dp.icon || "folder"
          )}"></i></span>${esc(dp.name)}</td>
          <td class="text-success text-end">${money(dp.total_credit)}</td>
          <td class="text-danger text-end">${money(dp.total_debit)}</td>
          <td class="text-end fw-semibold ${
            dp.balance >= 0 ? "text-success" : "text-danger"
          }">${money(dp.balance)}</td>
        </tr>`
        )
        .join("");

      content().innerHTML = `
        <h4 class="mb-3">Dashboard</h4>
        <div class="row g-3 mb-4">
          ${stat("stat-credit", "arrow-down-circle", "Total Credit", money(d.total_credit))}
          ${stat("stat-debit", "arrow-up-circle", "Total Debit", money(d.total_debit))}
          ${stat("stat-balance", "wallet2", "Net Balance", money(d.balance))}
          ${stat("stat-depts", "diagram-3", "Departments", d.department_count)}
        </div>
        <div class="row g-3">
          <div class="col-lg-7">
            <div class="card p-3">
              <h6 class="mb-3">Department-wise Summary</h6>
              <div class="table-responsive">
                <table class="table table-sm align-middle mb-0">
                  <thead><tr>
                    <th>Department</th><th class="text-end">Credit</th>
                    <th class="text-end">Debit</th><th class="text-end">Balance</th>
                  </tr></thead>
                  <tbody>${deptRows || `<tr><td colspan="4" class="text-muted">No data</td></tr>`}</tbody>
                </table>
              </div>
            </div>
          </div>
          <div class="col-lg-5">
            <div class="card p-3 mb-3">
              <h6 class="mb-3">Latest Broadcasts</h6>
              ${
                d.recent_broadcasts.length
                  ? d.recent_broadcasts
                      .map(
                        (b) => `<div class="border-bottom pb-2 mb-2">
                          <div class="fw-semibold">${esc(b.title)}</div>
                          <div class="small text-muted">${esc(b.message)}</div>
                          <div class="small text-secondary">— ${esc(
                            b.created_by_name
                          )}, ${fmtDate(b.created_at)}</div>
                        </div>`
                      )
                      .join("")
                  : `<div class="text-muted small">No broadcasts yet.</div>`
              }
            </div>
            <div class="card p-3">
              <h6 class="mb-3">Recent Transactions</h6>
              ${
                d.recent_transactions.length
                  ? d.recent_transactions
                      .map(
                        (t) => `<div class="d-flex justify-content-between border-bottom py-1">
                          <span class="small">${esc(t.title)} <span class="text-muted">· ${esc(
                          t.department_name
                        )}</span></span>
                          <span class="small fw-semibold ${
                            t.type === "credit" ? "text-success" : "text-danger"
                          }">${t.type === "credit" ? "+" : "-"}${money(t.amount)}</span>
                        </div>`
                      )
                      .join("")
                  : `<div class="text-muted small">No transactions yet.</div>`
              }
            </div>
          </div>
        </div>`;
    },

    async transactions() {
      const deptOptions = state.departments
        .map((d) => `<option value="${d.id}">${esc(d.name)}</option>`)
        .join("");
      content().innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
          <h4 class="mb-0">Transactions</h4>
          ${
            canWrite()
              ? `<button class="btn btn-primary btn-sm" id="add-txn"><i class="bi bi-plus-lg"></i> Add Entry</button>`
              : ""
          }
        </div>
        <div class="card p-3 mb-3">
          <div class="row g-2">
            <div class="col-sm-5">
              <select class="form-select form-select-sm" id="filter-dept">
                <option value="">All departments</option>${deptOptions}
              </select>
            </div>
            <div class="col-sm-4">
              <select class="form-select form-select-sm" id="filter-type">
                <option value="">All types</option>
                <option value="credit">Credit</option>
                <option value="debit">Debit</option>
              </select>
            </div>
          </div>
        </div>
        <div class="card p-0"><div class="table-responsive"><table class="table align-middle mb-0">
          <thead><tr>
            <th>Date</th><th>Department</th><th>Type</th><th>Item / Source</th>
            <th class="text-end">Amount</th><th>By</th><th></th>
          </tr></thead>
          <tbody id="txn-rows"><tr><td colspan="7" class="text-muted p-3">Loading…</td></tr></tbody>
        </table></div></div>`;

      if (canWrite()) $("#add-txn").addEventListener("click", openTxnModal);
      $("#filter-dept").addEventListener("change", loadTxns);
      $("#filter-type").addEventListener("change", loadTxns);
      loadTxns();
    },

    async broadcasts() {
      content().innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h4 class="mb-0">Broadcasts</h4>
          ${
            canWrite()
              ? `<button class="btn btn-primary btn-sm" id="add-bc"><i class="bi bi-megaphone"></i> New Broadcast</button>`
              : ""
          }
        </div>
        <div id="bc-list" class="text-muted">Loading…</div>`;
      if (canWrite()) $("#add-bc").addEventListener("click", openBroadcastModal);
      loadBroadcasts();
    },

    async mydepts() {
      const mine = state.departments.filter((d) => state.myDeptIds.includes(d.id));
      content().innerHTML = `
        <h4 class="mb-3">My Departments</h4>
        ${
          mine.length
            ? `<div class="row g-3">${mine
                .map(
                  (d) => `<div class="col-md-4"><div class="card p-3 h-100">
                    <div class="d-flex align-items-center mb-2">
                      <span class="dept-icon me-2"><i class="bi bi-${esc(
                        d.icon || "folder"
                      )}"></i></span>
                      <strong>${esc(d.name)}</strong>
                    </div>
                    <div class="small text-muted">${esc(d.description || "")}</div>
                  </div></div>`
                )
                .join("")}</div>`
            : `<div class="alert alert-info">You have not been assigned to any department yet. Please contact IT Support.</div>`
        }`;
    },

    async departments() {
      content().innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h4 class="mb-0">Departments</h4>
          <button class="btn btn-primary btn-sm" id="add-dept"><i class="bi bi-plus-lg"></i> Add Department</button>
        </div>
        <div id="dept-list" class="row g-3">Loading…</div>`;
      $("#add-dept").addEventListener("click", () => openDeptModal());
      loadDepts();
    },

    async users() {
      content().innerHTML = `
        <h4 class="mb-3">Users</h4>
        <ul class="nav nav-tabs mb-3" id="user-tabs">
          <li class="nav-item"><button class="nav-link active" data-utab="pending">Pending Managers</button></li>
          <li class="nav-item"><button class="nav-link" data-utab="managers">Managers</button></li>
          <li class="nav-item"><button class="nav-link" data-utab="members">Members</button></li>
        </ul>
        <div id="users-body" class="text-muted">Loading…</div>`;
      $$("#user-tabs .nav-link").forEach((b) =>
        b.addEventListener("click", () => {
          $$("#user-tabs .nav-link").forEach((x) => x.classList.remove("active"));
          b.classList.add("active");
          loadUsers(b.dataset.utab);
        })
      );
      loadUsers("pending");
    },
  };

  // ---------- Transactions logic ----------
  async function loadTxns() {
    const dept = $("#filter-dept")?.value;
    const type = $("#filter-type")?.value;
    let q = [];
    if (dept) q.push("department_id=" + dept);
    if (type) q.push("type=" + type);
    const rows = await API.get("/transactions" + (q.length ? "?" + q.join("&") : ""));
    const tbody = $("#txn-rows");
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-muted p-3">No transactions found.</td></tr>`;
      return;
    }
    tbody.innerHTML = rows
      .map((t) => {
        const canDelete =
          ME.role === "it_support" || (ME.role === "manager" && t.created_by_id === ME.id);
        return `<tr>
          <td class="small">${fmtDate(t.created_at)}</td>
          <td>${esc(t.department_name)}</td>
          <td><span class="badge ${
            t.type === "credit" ? "bg-success" : "bg-danger"
          }">${t.type}</span></td>
          <td>${esc(t.title)}${
          t.source ? `<div class="small text-muted">Source: ${esc(t.source)}</div>` : ""
        }${t.comment ? `<div class="small text-secondary">${esc(t.comment)}</div>` : ""}</td>
          <td class="text-end fw-semibold ${
            t.type === "credit" ? "text-success" : "text-danger"
          }">${money(t.amount)}</td>
          <td class="small">${esc(t.created_by_name)}</td>
          <td class="text-end">${
            canDelete
              ? `<button class="btn btn-sm btn-outline-danger" data-del-txn="${t.id}"><i class="bi bi-trash"></i></button>`
              : ""
          }</td>
        </tr>`;
      })
      .join("");
    $$("[data-del-txn]").forEach((b) =>
      b.addEventListener("click", async () => {
        if (!confirm("Delete this transaction?")) return;
        try {
          await API.del("/transactions/" + b.dataset.delTxn);
          loadTxns();
        } catch (e) {
          alertBox("#page-alert", e.message);
        }
      })
    );
  }

  function openTxnModal() {
    const depts =
      ME.role === "manager"
        ? state.departments.filter((d) => state.myDeptIds.includes(d.id))
        : state.departments;
    if (!depts.length) {
      return alertBox(
        "#page-alert",
        "No departments available. " +
          (ME.role === "manager" ? "Ask IT Support to assign you a department." : "Create a department first.")
      );
    }
    const opts = depts.map((d) => `<option value="${d.id}">${esc(d.name)}</option>`).join("");
    showModal(
      "Add Transaction",
      `<form id="txn-form">
        <div id="txn-alert"></div>
        <div class="mb-3">
          <label class="form-label">Type</label>
          <div class="btn-group w-100">
            <input type="radio" class="btn-check" name="type" id="t-debit" value="debit" checked>
            <label class="btn btn-outline-danger" for="t-debit">Debit (Expense)</label>
            <input type="radio" class="btn-check" name="type" id="t-credit" value="credit">
            <label class="btn btn-outline-success" for="t-credit">Credit (Income)</label>
          </div>
        </div>
        <div class="mb-3">
          <label class="form-label">Department</label>
          <select class="form-select" name="department_id" required>${opts}</select>
        </div>
        <div class="mb-3">
          <label class="form-label">Item / Purpose</label>
          <input class="form-control" name="title" required placeholder="e.g. Security salary, Diesel purchase">
        </div>
        <div class="mb-3">
          <label class="form-label">Amount (₹)</label>
          <input type="number" step="0.01" min="0.01" class="form-control" name="amount" required>
        </div>
        <div class="mb-3" id="source-field">
          <label class="form-label">Source of money <span class="text-muted small">(for credit)</span></label>
          <input class="form-control" name="source" placeholder="e.g. Maintenance collection, Interest">
        </div>
        <div class="mb-3">
          <label class="form-label">Comment</label>
          <textarea class="form-control" name="comment" rows="2"></textarea>
        </div>
      </form>`,
      `<button class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
       <button class="btn btn-primary" id="save-txn">Save</button>`
    );

    const toggleSource = () => {
      const isCredit = $("#txn-form [name=type]:checked").value === "credit";
      $("#source-field").classList.toggle("d-none", !isCredit);
    };
    $$("#txn-form [name=type]").forEach((r) => r.addEventListener("change", toggleSource));
    toggleSource();

    $("#save-txn").addEventListener("click", async () => {
      const f = $("#txn-form");
      const payload = {
        department_id: Number(f.department_id.value),
        type: f.type.value,
        title: f.title.value.trim(),
        amount: Number(f.amount.value),
        source: f.source.value.trim() || null,
        comment: f.comment.value.trim() || null,
      };
      if (!payload.title || !(payload.amount > 0))
        return alertBox("#txn-alert", "Please enter a valid item and amount.");
      try {
        await API.post("/transactions", payload);
        modal.hide();
        loadTxns();
        alertBox("#page-alert", "Transaction added.", "success");
      } catch (e) {
        alertBox("#txn-alert", e.message);
      }
    });
  }

  // ---------- Broadcasts logic ----------
  async function loadBroadcasts() {
    const list = await API.get("/broadcasts");
    const el = $("#bc-list");
    if (!list.length) {
      el.innerHTML = `<div class="alert alert-info">No broadcasts yet.</div>`;
      return;
    }
    el.innerHTML = list
      .map((b) => {
        const canDelete =
          ME.role === "it_support" || (ME.role === "manager" && b.created_by_id === ME.id);
        return `<div class="card p-3 mb-2">
          <div class="d-flex justify-content-between">
            <h6 class="mb-1"><i class="bi bi-megaphone text-primary me-1"></i>${esc(b.title)}</h6>
            ${
              canDelete
                ? `<button class="btn btn-sm btn-outline-danger" data-del-bc="${b.id}"><i class="bi bi-trash"></i></button>`
                : ""
            }
          </div>
          <p class="mb-1">${esc(b.message)}</p>
          <div class="small text-secondary">— ${esc(b.created_by_name)}, ${fmtDate(
          b.created_at
        )}</div>
        </div>`;
      })
      .join("");
    $$("[data-del-bc]").forEach((btn) =>
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this broadcast?")) return;
        await API.del("/broadcasts/" + btn.dataset.delBc);
        loadBroadcasts();
      })
    );
  }

  function openBroadcastModal() {
    showModal(
      "New Broadcast",
      `<form id="bc-form">
        <div id="bc-alert"></div>
        <div class="mb-3"><label class="form-label">Title</label>
          <input class="form-control" name="title" required></div>
        <div class="mb-3"><label class="form-label">Message</label>
          <textarea class="form-control" name="message" rows="4" required></textarea></div>
      </form>`,
      `<button class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
       <button class="btn btn-primary" id="save-bc">Publish</button>`
    );
    $("#save-bc").addEventListener("click", async () => {
      const f = $("#bc-form");
      try {
        await API.post("/broadcasts", {
          title: f.title.value.trim(),
          message: f.message.value.trim(),
        });
        modal.hide();
        loadBroadcasts();
        alertBox("#page-alert", "Broadcast published.", "success");
      } catch (e) {
        alertBox("#bc-alert", e.message);
      }
    });
  }

  // ---------- Departments logic (IT) ----------
  async function loadDepts() {
    const list = await API.get("/departments?include_inactive=true");
    state.departments = list.filter((d) => d.is_active);
    $("#dept-list").innerHTML = list
      .map(
        (d) => `<div class="col-md-4 col-lg-3">
          <div class="card p-3 h-100 ${d.is_active ? "" : "opacity-50"}">
            <div class="d-flex align-items-center mb-2">
              <span class="dept-icon me-2"><i class="bi bi-${esc(d.icon || "folder")}"></i></span>
              <strong>${esc(d.name)}</strong>
            </div>
            <div class="small text-muted flex-grow-1">${esc(d.description || "")}</div>
            <div class="mt-2 d-flex gap-1">
              <button class="btn btn-sm btn-outline-secondary" data-edit-dept='${JSON.stringify(
                d
              ).replace(/'/g, "&#39;")}'><i class="bi bi-pencil"></i></button>
              ${
                d.is_active
                  ? `<button class="btn btn-sm btn-outline-danger" data-deact-dept="${d.id}"><i class="bi bi-x-circle"></i></button>`
                  : `<span class="badge bg-secondary align-self-center">Inactive</span>`
              }
            </div>
          </div></div>`
      )
      .join("");
    $$("[data-edit-dept]").forEach((b) =>
      b.addEventListener("click", () => openDeptModal(JSON.parse(b.dataset.editDept)))
    );
    $$("[data-deact-dept]").forEach((b) =>
      b.addEventListener("click", async () => {
        if (!confirm("Deactivate this department?")) return;
        await API.del("/departments/" + b.dataset.deactDept);
        loadDepts();
      })
    );
  }

  function openDeptModal(dept = null) {
    const isEdit = !!dept;
    showModal(
      isEdit ? "Edit Department" : "Add Department",
      `<form id="dept-form">
        <div id="dept-alert"></div>
        <div class="mb-3"><label class="form-label">Name</label>
          <input class="form-control" name="name" required value="${esc(dept?.name || "")}"></div>
        <div class="mb-3"><label class="form-label">Description</label>
          <input class="form-control" name="description" value="${esc(dept?.description || "")}"></div>
        <div class="mb-3"><label class="form-label">Icon <span class="text-muted small">(Bootstrap Icon name)</span></label>
          <input class="form-control" name="icon" value="${esc(
            dept?.icon || "folder"
          )}" placeholder="e.g. shield-check"></div>
      </form>`,
      `<button class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
       <button class="btn btn-primary" id="save-dept">Save</button>`
    );
    $("#save-dept").addEventListener("click", async () => {
      const f = $("#dept-form");
      const payload = {
        name: f.name.value.trim(),
        description: f.description.value.trim() || null,
        icon: f.icon.value.trim() || null,
      };
      try {
        if (isEdit) await API.put("/departments/" + dept.id, payload);
        else await API.post("/departments", payload);
        modal.hide();
        loadDepts();
        alertBox("#page-alert", "Department saved.", "success");
      } catch (e) {
        alertBox("#dept-alert", e.message);
      }
    });
  }

  // ---------- Users logic (IT) ----------
  async function loadUsers(tab) {
    let path;
    if (tab === "pending") path = "/users?role=manager&pending=true";
    else if (tab === "managers") path = "/users?role=manager";
    else path = "/users?role=member";
    const users = await API.get(path);
    const body = $("#users-body");
    if (!users.length) {
      body.innerHTML = `<div class="alert alert-info">No users found.</div>`;
      return;
    }
    body.innerHTML = `<div class="card p-0"><div class="table-responsive"><table class="table align-middle mb-0">
      <thead><tr><th>Name</th><th>Mobile</th>${
        tab === "members" ? "<th>Flat</th>" : "<th>Departments</th>"
      }<th>Status</th><th></th></tr></thead>
      <tbody>${users
        .map((u) => {
          const status = !u.is_active
            ? `<span class="badge bg-secondary">Inactive</span>`
            : u.is_approved
            ? `<span class="badge bg-success">Active</span>`
            : `<span class="badge bg-warning text-dark">Pending</span>`;
          const deptCol =
            tab === "members"
              ? `<td>${esc(u.flat_no || "-")}</td>`
              : `<td class="small">${
                  (u.departments || []).map((d) => esc(d.name)).join(", ") || "-"
                }</td>`;
          let actions = "";
          if (!u.is_approved) {
            actions += `<button class="btn btn-sm btn-success me-1" data-approve="${u.id}"><i class="bi bi-check-lg"></i> Approve</button>`;
          }
          if (u.role === "manager" && u.is_approved) {
            actions += `<button class="btn btn-sm btn-outline-primary me-1" data-assign='${JSON.stringify(
              { id: u.id, deptIds: (u.departments || []).map((d) => d.id) }
            ).replace(/'/g, "&#39;")}'><i class="bi bi-diagram-3"></i> Depts</button>`;
          }
          if (u.is_active) {
            actions += `<button class="btn btn-sm btn-outline-danger" data-deact="${u.id}"><i class="bi bi-slash-circle"></i></button>`;
          } else {
            actions += `<button class="btn btn-sm btn-outline-success" data-act="${u.id}"><i class="bi bi-arrow-counterclockwise"></i></button>`;
          }
          return `<tr><td>${esc(u.name)}</td><td>${esc(
            u.mobile
          )}</td>${deptCol}<td>${status}</td><td class="text-end">${actions}</td></tr>`;
        })
        .join("")}</tbody></table></div></div>`;

    $$("[data-approve]").forEach((b) =>
      b.addEventListener("click", async () => {
        await API.post("/users/" + b.dataset.approve + "/approve");
        alertBox("#page-alert", "Manager approved.", "success");
        loadUsers(tab);
      })
    );
    $$("[data-deact]").forEach((b) =>
      b.addEventListener("click", async () => {
        if (!confirm("Deactivate this user?")) return;
        await API.post("/users/" + b.dataset.deact + "/deactivate");
        loadUsers(tab);
      })
    );
    $$("[data-act]").forEach((b) =>
      b.addEventListener("click", async () => {
        await API.post("/users/" + b.dataset.act + "/activate");
        loadUsers(tab);
      })
    );
    $$("[data-assign]").forEach((b) =>
      b.addEventListener("click", () => openAssignModal(JSON.parse(b.dataset.assign), tab))
    );
  }

  function openAssignModal(info, tab) {
    const checks = state.departments
      .map(
        (d) => `<div class="form-check">
          <input class="form-check-input" type="checkbox" value="${d.id}" id="ad-${d.id}" ${
          info.deptIds.includes(d.id) ? "checked" : ""
        }>
          <label class="form-check-label" for="ad-${d.id}">${esc(d.name)}</label>
        </div>`
      )
      .join("");
    showModal(
      "Assign Departments",
      `<div id="assign-alert"></div><div id="assign-list">${checks}</div>`,
      `<button class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
       <button class="btn btn-primary" id="save-assign">Save</button>`
    );
    $("#save-assign").addEventListener("click", async () => {
      const ids = $$("#assign-list input:checked").map((c) => Number(c.value));
      try {
        await API.put("/users/" + info.id + "/departments", { department_ids: ids });
        modal.hide();
        alertBox("#page-alert", "Departments updated.", "success");
        loadUsers(tab);
      } catch (e) {
        alertBox("#assign-alert", e.message);
      }
    });
  }

  // For managers: fetch which departments are assigned to me (via /auth/me + users list is IT-only,
  // so we infer from a dedicated endpoint). We reuse the departments list and mark all as available
  // if the manager endpoint is unavailable; server still enforces assignment on write.
  async function loadMyDepartments() {
    if (ME.role !== "manager") {
      state.myDeptIds = state.departments.map((d) => d.id);
      return;
    }
    try {
      const me = await API.get("/auth/me/departments");
      state.myDeptIds = me.map((d) => d.id);
    } catch (_) {
      state.myDeptIds = [];
    }
  }

  // ---------- OTP visibility (based on server config) ----------
  let CONFIG = { require_otp: true };

  function applyOtpVisibility() {
    const hide = !CONFIG.require_otp;
    // "Send OTP" buttons
    $$("[data-send-otp]").forEach((b) => b.classList.toggle("d-none", hide));
    // Signup OTP field
    const sOtp = $("#signup-form [name=otp]");
    if (sOtp) {
      sOtp.closest(".mb-3").classList.toggle("d-none", hide);
      sOtp.required = !hide;
    }
    // OTP-login link
    $("#show-otp-login")?.classList.toggle("d-none", hide);
  }

  async function loadConfig() {
    try {
      CONFIG = await API.get("/config");
    } catch (_) {
      /* keep default */
    }
    applyOtpVisibility();
    applyBranding();
  }

  function applyBranding() {
    const name = CONFIG.app_name || "SocietyHub";
    document.title = name + " — Society Management";
    $$("[data-app-name]").forEach((el) => (el.textContent = name));
  }

  // ---------- Bootstrap the app ----------
  updateSignupRole();
  loadConfig();
  (async () => {
    if (API.getToken()) {
      try {
        await enterApp();
      } catch (_) {
        showAuth();
      }
    }
  })();
})();
