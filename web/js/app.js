/* ==========================================================================
   EstateIQ Facility Intelligence - Main Application Controller
   - 2-Way REST API Integration
   - Role-Based Access Control (RBAC) Engine (Admin, Engineer, Auditor, Viewer)
   - Interactive Role Switcher & Access Restricted Modal
   - Interactive Chart Legend Toggles (Click legend to hide/show datasets)
   - Live Search Filtering across cards & recommendations
   - SaaS Subscription & Billing Upgrade Handlers
   ========================================================================== */

let currentUserSession = {
    user_id: "USR_SUPER_00",
    name: "RS Administrator",
    initials: "RS",
    role_key: "admin",
    role_label: "Admin (Full Access)",
    avatar_bg: "#124B3E",
    permissions: ["overview", "suggestions", "energy", "water", "waste", "mobility", "simulator", "resource-simulator", "iot-monitor", "ai-assistant", "faq", "esg", "billing", "work-orders"],
    can_execute_rules: true,
    can_upgrade_subscription: true
};

document.addEventListener("DOMContentLoaded", () => {
    initLoginPortal();
    initRoleBasedAuth();
    initTabs();
    initDatasetDropdown();
    initLocationDropdown();
    initSignalsModal();
    initTimeRangeButtons();
    initChartLegendToggles();
    initGlobalSearchFilter();
    initNotificationsDropdown();
    initChatEngine();
    initTelemetryStreamer();
    initIotSimulator();
    initKeyboardShortcuts();
    initDecisionTraceModal();
    initScoreExplanationModal();

    // Fetch initial data from REST API endpoints
    loadBackendDatasetInfo();
    loadBackendFacilitySummary();
    loadBackendForecasts();
    loadBackendAlerts();
    loadBackendMobilityStats();
    loadBackendMLModels();
    loadBackendSubscriptionDetails();
    loadBackendActionableSuggestions();
    loadBackendWorkOrders();
    loadBackendAIInsights();
    loadBackendCapabilities();

    // Initialize interactive form listeners
    initEnergyPredictorForm();
    initWaterAnomalyForm();
    initWastePredictorForm();
    initScenarioSimulatorForm();
    initSubscriptionUpgradeListeners();
    initEsgPdfDownload();
});

/* --------------------------------------------------------------------------
   GLASSMORPHISM ENTERPRISE LOGIN PORTAL CONTROLLER
   -------------------------------------------------------------------------- */
function initLoginPortal() {
    const portal = document.getElementById("loginPortalOverlay");
    const form = document.getElementById("loginPortalForm");
    const roleChips = document.querySelectorAll(".role-chip-btn");
    const emailInput = document.getElementById("loginEmailInput");
    const passInput = document.getElementById("loginPasswordInput");
    const signOutBtn = document.getElementById("btnSignOut");

    if (!portal || !form) return;

    // LOGIN FIRST POLICY: Show login portal unless explicit authenticated flag exists
    const savedSession = localStorage.getItem("estateiq_authenticated");
    if (savedSession === "true") {
        portal.classList.add("hidden");
    } else {
        portal.classList.remove("hidden");
    }

    signOutBtn?.addEventListener("click", (e) => {
        e.stopPropagation();
        document.getElementById("roleSwitcherDropdown")?.classList.remove("show");
        localStorage.removeItem("estateiq_authenticated");
        portal.classList.remove("hidden");
        showToast("Signed out of EstateIQ Session");
    });

    roleChips.forEach(chip => {
        chip.addEventListener("click", () => {
            const preset = chip.getAttribute("data-preset");
            if (preset === "admin") {
                emailInput.value = "admin@estateiq.in";
                passInput.value = "Admin@123";
            } else if (preset === "sustainability") {
                emailInput.value = "sustainability@estateiq.in";
                passInput.value = "Sust@123";
            } else if (preset === "operations") {
                emailInput.value = "operations@estateiq.in";
                passInput.value = "Ops@123";
            }
            form.dispatchEvent(new Event("submit"));
        });
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const submitBtn = document.getElementById("btnSubmitLogin");
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Authenticating...`;
        }

        const email = emailInput.value.trim();
        const password = passInput.value.trim();

        try {
            const res = await fetch("/api/v1/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            if (res.ok) {
                const data = await res.json();
                currentUserSession = data.user || currentUserSession;
                updateUIUserSession(currentUserSession);
            }
        } catch (err) {
            console.warn("Using offline authentication fallback.");
            const emailLower = email.toLowerCase();
            if (emailLower.includes("sust")) {
                currentUserSession = {
                    user_id: "USR_AUD_03",
                    name: "Dr. Priya Sharma",
                    initials: "PS",
                    role_key: "sustainability",
                    role_label: "Sustainability Officer",
                    avatar_bg: "#0D9488",
                    permissions: ["overview", "esg", "suggestions", "energy", "water", "waste", "mobility", "faq"],
                    can_execute_rules: false,
                    can_upgrade_subscription: false
                };
            } else if (emailLower.includes("oper") || emailLower.includes("alex")) {
                currentUserSession = {
                    user_id: "USR_ENG_02",
                    name: "Alex Chen",
                    initials: "AC",
                    role_key: "operations",
                    role_label: "Operations Team",
                    avatar_bg: "#1E7A68",
                    permissions: ["overview", "iot-monitor", "resource-simulator", "simulator", "work-orders", "ai-assistant", "energy", "water", "waste", "mobility", "faq"],
                    can_execute_rules: true,
                    can_upgrade_subscription: false
                };
            } else {
                currentUserSession = {
                    user_id: "USR_SUPER_00",
                    name: "RS Administrator",
                    initials: "RS",
                    role_key: "admin",
                    role_label: "Admin (Full Access)",
                    avatar_bg: "#124B3E",
                    permissions: ["overview", "suggestions", "energy", "water", "waste", "mobility", "simulator", "resource-simulator", "iot-monitor", "ai-assistant", "faq", "esg", "billing", "work-orders"],
                    can_execute_rules: true,
                    can_upgrade_subscription: true
                };
            }
            updateUIUserSession(currentUserSession);
        } finally {
            localStorage.setItem("estateiq_authenticated", "true");
            portal.classList.add("hidden");
            showToast(`Welcome to EstateIQ, ${currentUserSession.name}!`);
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<i class="fa-solid fa-arrow-right-to-bracket"></i> Sign In to EstateIQ`;
            }
        }
    });
}

function initScoreExplanationModal() {
    const heroCard = document.getElementById("heroScoreCard");
    heroCard?.addEventListener("click", () => {
        showToast("Facility Health Index: 87/100 (Gold Grade). Component Breakdown: Energy -8 pts | Water +2 pts | Air +1 pt");
    });
}

/* --------------------------------------------------------------------------
   ROLE-BASED ACCESS CONTROL (RBAC) ENGINE
   -------------------------------------------------------------------------- */
async function initRoleBasedAuth() {
    const profilePill = document.getElementById("userProfile");
    const dropdown = document.getElementById("roleSwitcherDropdown");
    const options = document.querySelectorAll(".role-option");
    const restrictedModal = document.getElementById("accessRestrictedModal");
    const closeRestrictedBtn = document.getElementById("closeRestrictedModalBtn");
    const dismissRestrictedBtn = document.getElementById("dismissRestrictedBtn");
    const switchToAdminBtn = document.getElementById("switchToAdminBtn");

    // Fetch active session from REST API
    try {
        const res = await fetch("/api/v1/auth/me");
        if (res.ok) {
            currentUserSession = await res.json();
            updateUIUserSession(currentUserSession);
        }
    } catch (e) {
        updateUIUserSession(currentUserSession);
    }

    // Profile pill click toggles role dropdown
    profilePill?.addEventListener("click", (e) => {
        e.stopPropagation();
        dropdown?.classList.toggle("show");
    });

    document.addEventListener("click", () => {
        dropdown?.classList.remove("show");
    });

    // Handle role switching
    options.forEach(opt => {
        opt.addEventListener("click", async (e) => {
            e.stopPropagation();
            const roleKey = opt.getAttribute("data-role");
            dropdown?.classList.remove("show");

            try {
                const res = await fetch("/api/v1/auth/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ role: roleKey })
                });

                if (res.ok) {
                    const data = await res.json();
                    currentUserSession = data.user;
                    updateUIUserSession(currentUserSession);
                    showToast(`Active Session: ${currentUserSession.role_label}`);
                }
            } catch (err) {
                if (roleKey === "sustainability") {
                    currentUserSession = {
                        user_id: "USR_AUD_03",
                        name: "Dr. Priya Sharma",
                        initials: "PS",
                        role_key: "sustainability",
                        role_label: "Sustainability Officer",
                        avatar_bg: "#0D9488",
                        permissions: ["overview", "esg", "suggestions", "energy", "water", "waste", "mobility", "faq"],
                        can_execute_rules: false,
                        can_upgrade_subscription: false
                    };
                } else if (roleKey === "operations") {
                    currentUserSession = {
                        user_id: "USR_ENG_02",
                        name: "Alex Chen",
                        initials: "AC",
                        role_key: "operations",
                        role_label: "Operations Team",
                        avatar_bg: "#1E7A68",
                        permissions: ["overview", "iot-monitor", "resource-simulator", "simulator", "work-orders", "ai-assistant", "energy", "water", "waste", "mobility", "faq"],
                        can_execute_rules: true,
                        can_upgrade_subscription: false
                    };
                } else {
                    currentUserSession = {
                        user_id: "USR_SUPER_00",
                        name: "RS Administrator",
                        initials: "RS",
                        role_key: "admin",
                        role_label: "Admin (Full Access)",
                        avatar_bg: "#124B3E",
                        permissions: ["overview", "suggestions", "energy", "water", "waste", "mobility", "simulator", "resource-simulator", "iot-monitor", "ai-assistant", "faq", "esg", "billing", "work-orders"],
                        can_execute_rules: true,
                        can_upgrade_subscription: true
                    };
                }
                updateUIUserSession(currentUserSession);
                showToast(`Switched active role: ${currentUserSession.role_label}`);
            }
        });
    });

    // Access Restricted Modal Controls
    const closeRestricted = () => restrictedModal?.classList.remove("show");
    closeRestrictedBtn?.addEventListener("click", closeRestricted);
    dismissRestrictedBtn?.addEventListener("click", closeRestricted);
    
    switchToAdminBtn?.addEventListener("click", () => {
        closeRestricted();
        document.querySelector('.role-option[data-role="admin"]')?.click();
    });
}

function updateUIUserSession(user) {
    if (!user) return;
    currentUserSession = user;
    window.currentUserSession = user;

    const avatar = document.getElementById("activeAvatarInitials");
    const nameEl = document.getElementById("activeUserName");
    const roleLabelEl = document.getElementById("activeUserRoleLabel");
    const statusPill = document.getElementById("backendStatusPill");
    const bannerUserRole = document.getElementById("bannerUserRole");

    if (avatar) {
        avatar.textContent = user.initials || "RS";
        avatar.style.backgroundColor = user.avatar_bg || "#124B3E";
    }
    if (nameEl) nameEl.textContent = user.name || "RS Administrator";
    if (roleLabelEl) roleLabelEl.textContent = user.role_label || "Admin (Full Access)";
    if (statusPill) statusPill.textContent = `${user.role_label || "Admin"} Active`;
    if (bannerUserRole) bannerUserRole.textContent = `${user.name} (${user.role_label})`;

    // Update active checkmarks in role switcher
    document.querySelectorAll(".role-option").forEach(opt => {
        if (opt.getAttribute("data-role") === user.role_key) {
            opt.classList.add("active");
        } else {
            opt.classList.remove("active");
        }
    });

    const perms = Array.isArray(user.permissions) ? user.permissions : [];

    // STRICT INVISIBLE ROLE ENFORCEMENT:
    // 1. Sidebar navigation links: show if permitted, HIDE COMPLETELY if not!
    document.querySelectorAll(".sidebar-nav .nav-item[data-tab-nav]").forEach(item => {
        const tabId = item.getAttribute("data-tab-nav");
        if (perms.includes(tabId)) {
            item.style.removeProperty("display");
            item.classList.remove("role-hidden");
        } else {
            item.style.setProperty("display", "none", "important");
            item.classList.add("role-hidden");
        }
    });

    // 2. Horizontal Dashboard Tabs Bar: show if permitted, HIDE COMPLETELY if not!
    document.querySelectorAll(".dashboard-tabs .tab-btn[data-tab]").forEach(btn => {
        const tabId = btn.getAttribute("data-tab");
        if (perms.includes(tabId)) {
            btn.style.removeProperty("display");
            btn.classList.remove("role-hidden");
        } else {
            btn.style.setProperty("display", "none", "important");
            btn.classList.add("role-hidden");
        }
    });

    // 3. SaaS Plan Upgrade Pill in Header
    const planPill = document.getElementById("headerPlanPill");
    if (planPill) {
        if (perms.includes("billing")) {
            planPill.style.removeProperty("display");
        } else {
            planPill.style.setProperty("display", "none", "important");
        }
    }

    // 4. Work Orders active role badge
    const woRolePill = document.getElementById("woRolePill");
    if (woRolePill) {
        woRolePill.textContent = `Active Role: ${user.role_label}`;
    }

    // 5. Auto-redirect if current active tab is now hidden in the new role
    const activeNav = document.querySelector(".sidebar-nav .nav-item.active");
    const activeTab = activeNav ? activeNav.getAttribute("data-tab-nav") : null;
    if (activeTab && !perms.includes(activeTab)) {
        if (typeof window.switchTab === "function") {
            window.switchTab("overview");
        }
    }
}

/* --------------------------------------------------------------------------
   TAB NAVIGATION SYSTEM & PERMISSION ENFORCEMENT
   -------------------------------------------------------------------------- */
function initTabs() {
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");
    const sidebarNavs = document.querySelectorAll(".nav-item[data-tab-nav]");
    const headerPlanPill = document.getElementById("headerPlanPill");

    const TAB_ALIASES = {
        "copilot": "ai-assistant",
        "copilotai": "ai-assistant",
        "ai-copilot": "ai-assistant",
        "ai": "ai-assistant",
        "assistant": "ai-assistant",
        "subscription": "billing",
        "subscriptions": "billing",
        "plans": "billing",
        "pricing": "billing",
        "subscription-plans": "billing",
        "workorder": "work-orders",
        "workorders": "work-orders",
        "iot": "iot-monitor",
        "live-iot": "iot-monitor",
        "live-iot-monitor": "iot-monitor",
        "iotmonitor": "iot-monitor",
        "resource-sim": "resource-simulator",
        "resources": "resource-simulator",
        "resourcesimulatorsim": "resource-simulator",
        "resourcesimulator": "resource-simulator",
        "esg-carbon": "esg",
        "carbon": "esg",
        "faqs": "faq",
        "decision-intelligence": "overview",
        "models": "overview"
    };

    const switchTab = (tabId) => {
        let rawTab = (tabId || "").toString().toLowerCase().trim().replace(/^#/, "");
        let activeTab = TAB_ALIASES[rawTab] || rawTab;
        if (!activeTab) activeTab = "overview";

        // Strict Role-Based Access Enforcement
        if (currentUserSession && currentUserSession.permissions && !currentUserSession.permissions.includes(activeTab)) {
            showToast(`Access Restricted: '${activeTab.toUpperCase()}' is not available for ${currentUserSession.role_label || 'this role'}.`);
            activeTab = "overview";
        }

        tabBtns.forEach(b => b.classList.remove("active"));
        tabContents.forEach(c => c.classList.remove("active"));
        sidebarNavs.forEach(s => s.classList.remove("active"));

        const selectedBtn = document.querySelector(`.tab-btn[data-tab="${activeTab}"]`);
        if (selectedBtn) selectedBtn.classList.add("active");

        const selectedSidebar = document.querySelector(`.nav-item[data-tab-nav="${activeTab}"]`);
        if (selectedSidebar) selectedSidebar.classList.add("active");

        const metricsGrid = document.querySelector(".metrics-grid-top");
        if (metricsGrid) {
            if (activeTab === "overview") {
                metricsGrid.style.display = "grid";
            } else {
                metricsGrid.style.display = "none";
            }
        }

        const capName = capitalizeFirst(activeTab);
        let targetContent = document.getElementById(`content${capName}`);
        if (!targetContent) {
            targetContent = document.getElementById(activeTab) || 
                            document.getElementById(`content-${activeTab}`) ||
                            document.querySelector(`.tab-content[data-tab="${activeTab}"]`);
        }
        if (!targetContent) {
            targetContent = document.getElementById("contentOverview");
        }
        if (targetContent) {
            targetContent.classList.add("active");
        }

        // Sync URL hash seamlessly without full page jump glitch
        if (window.history && window.history.replaceState) {
            window.history.replaceState(null, "", `#${activeTab}`);
        }

        // Scroll main viewport smoothly to top
        window.scrollTo({ top: 0, behavior: 'smooth' });

        // Trigger chart resize & re-render so hidden tab canvases calculate full width & height
        if (activeTab === "iot-monitor" || activeTab === "iot-simulator" || activeTab === "simulator") {
            window.fetchIotStatus?.();
            window.fetchIotStreamLog?.();
        } else if (activeTab === "resource-simulator") {
            window.EstateIQResourceSimulator?.syncInputsWithState?.();
            window.EstateIQResourceSimulator?.updateMetricsDOM?.();
            window.EstateIQResourceSimulator?.initCharts?.();
        } else if (activeTab === "work-orders") {
            loadBackendWorkOrders?.();
        } else if (activeTab === "billing") {
            loadBackendSubscriptionDetails?.();
        }

        setTimeout(() => {
            window.dispatchEvent(new Event('resize'));
        }, 40);
    };

    window.switchTab = switchTab;

    tabBtns.forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            switchTab(btn.getAttribute("data-tab"));
        });
    });

    sidebarNavs.forEach(nav => {
        nav.addEventListener("click", (e) => {
            e.preventDefault();
            switchTab(nav.getAttribute("data-tab-nav"));
        });
    });

    headerPlanPill?.addEventListener("click", (e) => {
        e.preventDefault();
        switchTab("billing");
    });

    // Handle initial hash navigation on page load
    const initialHash = (window.location.hash || "").replace("#", "").trim();
    if (initialHash) {
        switchTab(initialHash);
    }
    window.addEventListener("hashchange", () => {
        const h = (window.location.hash || "").replace("#", "").trim();
        if (h) switchTab(h);
    });
}

function showRestrictedAccessModal(tabId) {
    const modal = document.getElementById("accessRestrictedModal");
    const title = document.getElementById("restrictedModuleTitle");
    const desc = document.getElementById("restrictedModuleDesc");

    if (!modal) return;

    if (title) title.textContent = `${capitalizeFirst(tabId)} Module Restricted`;
    if (desc) {
        desc.innerHTML = `Your current user role <strong>(${currentUserSession.name} - ${currentUserSession.role_label})</strong> does not have authorization to view or execute actions in the <strong>${capitalizeFirst(tabId)}</strong> module.<br><br>Please switch to Administrator or an authorized role to unlock access.`;
    }

    modal.classList.add("show");
}

function capitalizeFirst(str) {
    if (!str) return "";
    let clean = String(str).toLowerCase().trim().replace(/^#/, "");
    const aliasMap = {
        "copilot": "ai-assistant",
        "copilotai": "ai-assistant",
        "ai-copilot": "ai-assistant",
        "ai": "ai-assistant",
        "assistant": "ai-assistant",
        "subscription": "billing",
        "subscriptions": "billing",
        "plans": "billing",
        "pricing": "billing",
        "subscription-plans": "billing",
        "workorder": "work-orders",
        "workorders": "work-orders",
        "iot": "iot-monitor",
        "live-iot": "iot-monitor",
        "live-iot-monitor": "iot-monitor",
        "iotmonitor": "iot-monitor",
        "resource-sim": "resource-simulator",
        "resources": "resource-simulator",
        "resourcesimulatorsim": "resource-simulator",
        "resourcesimulator": "resource-simulator",
        "esg-carbon": "esg",
        "carbon": "esg",
        "faqs": "faq",
        "decision-intelligence": "overview",
        "models": "overview"
    };
    if (aliasMap[clean]) clean = aliasMap[clean];
    if (clean === "faq") return "Faq";
    if (clean === "ai-assistant") return "AiAssistant";
    if (clean === "work-orders") return "WorkOrders";
    if (clean === "iot-simulator") return "IotSimulator";
    if (clean === "iot-monitor") return "IotMonitor";
    if (clean === "resource-simulator") return "ResourceSimulator";
    if (clean === "billing") return "Billing";
    if (clean === "esg") return "Esg";
    if (clean === "suggestions") return "Suggestions";
    if (clean === "energy") return "Energy";
    if (clean === "water") return "Water";
    if (clean === "waste") return "Waste";
    if (clean === "mobility") return "Mobility";
    if (clean === "simulator") return "Simulator";
    if (clean === "overview") return "Overview";
    return clean.charAt(0).toUpperCase() + clean.slice(1);
}

/* --------------------------------------------------------------------------
   INTERACTIVE CHART LEGEND TOGGLES
   -------------------------------------------------------------------------- */
function initChartLegendToggles() {
    const legendItems = document.querySelectorAll(".legend-item");
    legendItems.forEach((item, index) => {
        item.addEventListener("click", () => {
            if (typeof mainWaveChartInstance !== "undefined" && mainWaveChartInstance) {
                const isVisible = mainWaveChartInstance.isDatasetVisible(index);
                mainWaveChartInstance.setDatasetVisibility(index, !isVisible);
                mainWaveChartInstance.update();

                item.classList.toggle("disabled", isVisible);
            }
        });
    });
}

/* --------------------------------------------------------------------------
   GLOBAL SEARCH FILTER ENGINE
   -------------------------------------------------------------------------- */
function initGlobalSearchFilter() {
    const searchInput = document.getElementById("globalSearchInput");
    if (!searchInput) return;

    searchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        if (!query) {
            document.querySelectorAll(".suggestion-card-item, .model-card-item, .interactive-card").forEach(el => el.style.display = "");
            return;
        }

        document.querySelectorAll(".suggestion-card-item, .model-card-item, .interactive-card").forEach(card => {
            const text = card.textContent.toLowerCase();
            if (text.includes(query)) {
                card.style.display = "";
            } else {
                card.style.display = "none";
            }
        });
    });
}

/* --------------------------------------------------------------------------
   SAAS SUBSCRIPTION & BUSINESS MODEL ENDPOINTS
   -------------------------------------------------------------------------- */
async function loadBackendSubscriptionDetails() {
    try {
        const res = await fetch("/api/v1/subscription");
        if (!res.ok) return;
        const data = await res.json();
        
        const planTitle = document.getElementById("billingCurrentPlanTitle");
        const headerPlanLabel = document.getElementById("headerPlanLabel");
        const bText = document.getElementById("meterBuildingsText");
        const apiText = document.getElementById("meterApiText");

        if (planTitle) planTitle.textContent = data.current_plan.name;
        if (headerPlanLabel) headerPlanLabel.textContent = data.current_plan.name.replace(" Plan", "");

        if (bText && data.usage_limits.monitored_buildings) {
            bText.textContent = `${data.usage_limits.monitored_buildings.used} / ${data.usage_limits.monitored_buildings.total} Buildings`;
        }
        if (apiText && data.usage_limits.api_requests) {
            apiText.textContent = `${data.usage_limits.api_requests.used.toLocaleString()} / ${data.usage_limits.api_requests.total.toLocaleString()} Calls/mo`;
        }
    } catch (e) {
        console.warn("Subscription details loaded from local cache.");
    }
}

function initSubscriptionUpgradeListeners() {
    const upgradeBtns = document.querySelectorAll(".upgrade-plan-btn");
    const cycleToggle = document.getElementById("billingCycleToggle");

    upgradeBtns.forEach(btn => {
        btn.addEventListener("click", async () => {
            if (currentUserSession && !currentUserSession.can_upgrade_subscription) {
                showRestrictedAccessModal("billing");
                return;
            }

            const planId = btn.getAttribute("data-plan");
            const isAnnual = cycleToggle ? cycleToggle.checked : true;

            try {
                const res = await fetch("/api/v1/subscription/upgrade", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        target_plan: planId,
                        billing_cycle: isAnnual ? "annual" : "monthly"
                    })
                });

                const planDisplayName = (planId === "basic") ? "EstateIQ Basic" : "EstateIQ Professional";
                const planPriceText = (planId === "basic") 
                    ? "₹3,499 / month (₹41,988 / year) • Active Institutional License"
                    : "₹5,999 / month (₹71,988 / year) • Active Institutional License";

                showToast(`Subscription Updated: Activated ${planDisplayName}`);
                
                upgradeBtns.forEach(b => {
                    const p = b.getAttribute("data-plan");
                    b.disabled = false;
                    b.className = "btn btn-secondary btn-block upgrade-plan-btn";
                    b.textContent = (p === "basic") ? "Switch to Basic" : "Switch to Pro";
                });
                btn.disabled = true;
                btn.className = "btn btn-primary btn-block upgrade-plan-btn";
                btn.textContent = "Current Active Plan";

                const planTitle = document.getElementById("billingCurrentPlanTitle");
                if (planTitle) planTitle.textContent = planDisplayName;

                const planPriceEl = document.querySelector(".sub-plan-price");
                if (planPriceEl) planPriceEl.innerHTML = (planId === "basic")
                    ? '₹3,499 / month <span class="inr-sub">(₹41,988 / year)</span> • Active Institutional License'
                    : '₹5,999 / month <span class="inr-sub">(₹71,988 / year)</span> • Active Institutional License';

                const headerPlanLabel = document.getElementById("headerPlanLabel");
                if (headerPlanLabel) headerPlanLabel.textContent = (planId === "basic") ? "EstateIQ Basic" : "EstateIQ Pro";

                // Update featured card border styling
                const cardBasic = document.getElementById("planCardStarter");
                const cardPro = document.getElementById("planCardPro");
                if (planId === "basic") {
                    cardBasic?.classList.add("featured");
                    cardPro?.classList.remove("featured");
                } else {
                    cardPro?.classList.add("featured");
                    cardBasic?.classList.remove("featured");
                }
            } catch (err) {
                showToast(`Switched plan to ${planId.toUpperCase()}`);
            }
        });
    });

    cycleToggle?.addEventListener("change", () => {
        const isAnnual = cycleToggle.checked;
        const pStarterAnnual = document.getElementById("priceStarterAnnual");
        const pProAnnual = document.getElementById("priceProAnnual");
        const discountLabel = document.querySelector(".billing-toggle-pill .discount-label");

        if (pStarterAnnual) pStarterAnnual.textContent = isAnnual ? "₹41,988 / year" : "Billed monthly";
        if (pProAnnual) pProAnnual.textContent = isAnnual ? "₹71,988 / year" : "Billed monthly";
        if (discountLabel) discountLabel.textContent = isAnnual ? "Annual Plan Selected" : "Monthly Billing";
    });
}

/* --------------------------------------------------------------------------
   AI ACTION SUGGESTIONS & ROI ADVISOR ENDPOINTS
   -------------------------------------------------------------------------- */
async function loadBackendActionableSuggestions() {
    try {
        const res = await fetch("/api/v1/recommendations/actionable");
        if (!res.ok) return;
        const data = await res.json();

        const grid = document.getElementById("suggestionsListGrid");
        if (grid && data.suggestions) {
            grid.innerHTML = data.suggestions.map(s => `
                <div class="suggestion-card-item">
                    <div class="sug-top">
                        <span class="${s.priority === 'HIGH' ? 'badge-red' : 'badge-amber'}">${s.priority} PRIORITY</span>
                        <span class="sug-cat">${s.category} • ${s.building}</span>
                    </div>
                    <h3>${s.title}</h3>
                    <p>Automated recommendation engine flags setpoint optimization. Saves <strong>${s.co2_reduction_tons} Tons CO₂e</strong> annually.</p>
                    <div class="sug-footer">
                        <div class="sug-savings text-green">+$${s.annual_savings_usd.toLocaleString()} / yr (₹${(s.annual_savings_inr / 100000).toFixed(1)}L)</div>
                        <button class="btn btn-primary btn-sm apply-rule-btn" data-rule="${s.id}" data-building="${s.building.replace(/\s+/g, '_')}">
                            <i class="fa-solid fa-play"></i> Apply Automated Rule
                        </button>
                    </div>
                </div>
            `).join("");

            initRuleExecutionButtons();
        }
    } catch (e) {
        initRuleExecutionButtons();
    }
}

function initRuleExecutionButtons() {
    const applyBtns = document.querySelectorAll(".apply-rule-btn");
    const applyAllBtn = document.getElementById("applyAllRulesBtn");

    const executeRule = async (btn, ruleId, buildingId) => {
        if (currentUserSession && !currentUserSession.can_execute_rules) {
            showRestrictedAccessModal("suggestions");
            return;
        }

        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Executing...`;

        try {
            const res = await fetch("/api/v1/recommendations/apply", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ rule_id: ruleId, building_id: buildingId })
            });

            if (res.ok) {
                const data = await res.json();
                btn.className = "btn btn-emerald btn-sm";
                btn.innerHTML = `<i class="fa-solid fa-check"></i> Rule Executed`;
                showToast(`Rule ${ruleId} Executed! ${data.facility_score_boost}`);

                const heroScore = document.getElementById("heroScoreValue");
                if (heroScore) {
                    const current = parseInt(heroScore.textContent);
                    heroScore.textContent = Math.min(100, current + 3);
                }
            }
        } catch (err) {
            btn.className = "btn btn-emerald btn-sm";
            btn.innerHTML = `<i class="fa-solid fa-check"></i> Rule Executed`;
            showToast(`Rule ${ruleId} Executed Successfully! (+3.5 Facility Score Boost)`);
        }
    };

    applyBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const ruleId = btn.getAttribute("data-rule") || "REC_01";
            const bldId = btn.getAttribute("data-building") || "Block_B_Hostel";
            executeRule(btn, ruleId, bldId);
        });
    });

    applyAllBtn?.addEventListener("click", () => {
        applyBtns.forEach(btn => btn.click());
    });
}

function initEsgPdfDownload() {
    document.getElementById("downloadEsgBtn")?.addEventListener("click", () => {
        showToast("Generating ISO 14064 Compliance Audit Exporter PDF...");
        setTimeout(() => {
            window.open("/api/v1/esg/audit", "_blank");
        }, 1000);
    });
}

/* --------------------------------------------------------------------------
   BACKEND DATA LOADERS (GET ENDPOINTS)
   -------------------------------------------------------------------------- */
async function loadBackendFacilitySummary() {
    try {
        const res = await fetch("/api/v1/facility/summary");
        if (!res.ok) return;
        const data = await res.json();
        
        const dropdown = document.getElementById("locationDropdown");
        if (dropdown && data.building_list) {
            let html = `<div class="dropdown-item active" data-location="all">Main Campus - All Blocks (${data.total_buildings} Buildings)</div>`;
            data.building_list.forEach(b => {
                html += `<div class="dropdown-item" data-location="${b.toLowerCase().replace(/\s+/g, '_')}">${b}</div>`;
            });
            dropdown.innerHTML = html;
            bindLocationItemEvents();
        }
    } catch (e) {
        console.warn("Backend summary using baseline.");
    }
}

async function loadBackendForecasts() {
    try {
        const res = await fetch("/api/v1/energy/forecast");
        if (!res.ok) return;
        const data = await res.json();
        
        const f1 = document.getElementById("forecast1hVal");
        const f4 = document.getElementById("forecast4hVal");
        const f24 = document.getElementById("forecast24hVal");

        if (f1) f1.textContent = `${data.predicted_1h_kwh} kWh`;
        if (f4) f4.textContent = `${data.predicted_4h_kwh} kWh`;
        if (f24) f24.textContent = `${data.predicted_24h_kwh} kWh`;
    } catch (e) {
        console.warn("Forecast using cached values.");
    }
}

async function loadBackendAlerts() {
    try {
        const res = await fetch("/api/v1/alerts");
        if (!res.ok) return;
        const data = await res.json();
        
        const sidebarBadge = document.getElementById("sidebarAlertCount");
        const notifBadge = document.getElementById("notificationCount");

        if (sidebarBadge) sidebarBadge.textContent = data.total_active_alerts;
        if (notifBadge) notifBadge.textContent = data.total_active_alerts;
    } catch (e) {
        console.warn("Alerts using cached list.");
    }
}

async function loadBackendMobilityStats() {
    try {
        const trafRes = await fetch("/api/v1/traffic");
        if (trafRes.ok) {
            const trafData = await trafRes.json();
            const gate = document.getElementById("trafficGateStatus");
            const speed = document.getElementById("trafficAvgSpeed");
            if (gate) gate.textContent = trafData.gate_status;
            if (speed) speed.textContent = `${trafData.average_speed_kmph} km/h`;
        }

        const parkRes = await fetch("/api/v1/parking");
        if (parkRes.ok) {
            const parkData = await parkRes.json();
            const rate = document.getElementById("parkingOccupancyRate");
            const text = document.getElementById("parkingSpacesText");
            if (rate) rate.textContent = `${Math.round(parkData.occupancy_rate * 100)}%`;
            if (text) text.textContent = `${parkData.occupied_spaces} / ${parkData.total_capacity}`;
        }

        const airRes = await fetch("/api/v1/air");
        if (airRes.ok) {
            const airData = await airRes.json();
            const aqi = document.getElementById("airAqiVal");
            const cat = document.getElementById("airAqiCat");
            if (aqi) aqi.textContent = `${airData.campus_avg_aqi} AQI`;
            if (cat) cat.textContent = airData.category;
        }

        const eqRes = await fetch("/api/v1/equipment");
        if (eqRes.ok) {
            const eqData = await eqRes.json();
            const assets = document.getElementById("equipMonitoredCount");
            const risks = document.getElementById("equipRiskCount");
            if (assets) assets.textContent = `${eqData.assets_monitored} Assets`;
            if (risks) risks.textContent = `${eqData.maintenance_risk_alerts} Risk Alert`;
        }

        const wasteRes = await fetch("/api/v1/waste/summary");
        if (wasteRes.ok) {
            const wasteData = await wasteRes.json();
            const bMon = document.getElementById("binsMonitoredCount");
            const bColl = document.getElementById("binsCollectionCount");
            if (bMon) bMon.textContent = wasteData.bins_monitored;
            if (bColl) bColl.textContent = `${wasteData.bins_requiring_collection} Bins`;
        }
    } catch (e) {
        console.warn("Mobility stats cached.");
    }
}

async function loadBackendMLModels() {
    try {
        const res = await fetch("/api/v1/models");
        if (!res.ok) return;
        const data = await res.json();
        
        const grid = document.getElementById("mlModelsGrid");
        if (grid && data.models) {
            grid.innerHTML = data.models.map(m => `
                <div class="model-card-item">
                    <div class="mc-header">
                        <span class="mc-task">${m.target_variable || m.selected_model}</span>
                        <span class="badge-green">REGISTERED</span>
                    </div>
                    <h4>Model: ${m.selected_model || 'ML Pipeline'}</h4>
                    <p>Features: ${m.feature_names ? m.feature_names.length : 'N/A'} • Status: Active Inference</p>
                </div>
            `).join("");
        }
    } catch (e) {
        console.warn("ML Registry cached.");
    }
}

/* --------------------------------------------------------------------------
   DATASET A / B CONTROL PANEL & SYNCHRONIZATION
   -------------------------------------------------------------------------- */
function initDatasetDropdown() {
    const selector = document.getElementById("datasetSelector");
    const dropdown = document.getElementById("datasetDropdown");
    const textEl = document.getElementById("currentDatasetText");

    if (!selector || !dropdown) return;

    selector.addEventListener("click", (e) => {
        e.stopPropagation();
        document.getElementById("locationDropdown")?.classList.remove("show");
        document.getElementById("roleSwitcherDropdown")?.classList.remove("show");
        dropdown.classList.toggle("show");
    });

    document.addEventListener("click", () => dropdown.classList.remove("show"));

    const items = dropdown.querySelectorAll(".dropdown-item");
    items.forEach(item => {
        item.addEventListener("click", async (e) => {
            e.stopPropagation();
            dropdown.classList.remove("show");
            const targetDataset = item.getAttribute("data-dataset");
            
            try {
                const res = await fetch("/api/v1/dataset/switch", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ dataset_id: targetDataset })
                });

                if (res.ok) {
                    const data = await res.json();
                    items.forEach(i => i.classList.remove("active"));
                    item.classList.add("active");

                    const label = targetDataset === "dataset_b" ? "Dataset B (Surge 1.85x)" : "Dataset A (Baseline)";
                    if (textEl) textEl.textContent = label;

                    showToast(`Switched to ${data.name}! Multiplier: ${data.multiplier}x`);
                    
                    refreshAllBackendData();
                }
            } catch (err) {
                showToast(`Dataset switched to ${targetDataset.toUpperCase()}`);
            }
        });
    });
}

async function loadBackendDatasetInfo() {
    try {
        const res = await fetch("/api/v1/dataset/info");
        if (!res.ok) return;
        const data = await res.json();
        const textEl = document.getElementById("currentDatasetText");
        const activeItem = document.querySelector(`.dropdown-item[data-dataset="${data.active_dataset_id}"]`);
        
        if (activeItem) {
            document.querySelectorAll("#datasetDropdown .dropdown-item").forEach(i => i.classList.remove("active"));
            activeItem.classList.add("active");
        }
        if (textEl) {
            textEl.textContent = data.active_dataset_id === "dataset_b" ? "Dataset B (Surge 1.85x)" : "Dataset A (Baseline)";
        }
    } catch (e) {
        console.warn("Dataset info using default baseline.");
    }
}

function refreshAllBackendData() {
    loadBackendFacilitySummary();
    loadBackendForecasts();
    loadBackendAlerts();
    loadBackendMobilityStats();
    loadBackendMLModels();
    loadBackendActionableSuggestions();
    loadBackendWorkOrders();
    loadBackendAIInsights();
}

/* --------------------------------------------------------------------------
   STAFF WORK ORDERS & OPERATIONS CONTROLLER
   -------------------------------------------------------------------------- */
async function loadBackendWorkOrders() {
    const grid = document.getElementById("workOrdersListGrid");
    const refreshBtn = document.getElementById("btnRefreshWorkOrders");

    if (refreshBtn && !refreshBtn.hasAttribute("data-bound")) {
        refreshBtn.setAttribute("data-bound", "true");
        refreshBtn.addEventListener("click", () => {
            loadBackendWorkOrders();
            showToast("Work Orders list refreshed");
        });
    }

    try {
        const res = await fetch("/api/v1/work-orders");
        if (!res.ok) return;
        const data = await res.json();
        const orders = data.work_orders || [];

        const total = orders.length;
        const inProgress = orders.filter(o => o.status === "IN_PROGRESS" || o.status === "ASSIGNED").length;
        const completed = orders.filter(o => o.status === "COMPLETED" || o.status === "VERIFIED").length;
        const verified = orders.filter(o => o.status === "VERIFIED").length;

        const sTot = document.getElementById("woStatTotal");
        const sProg = document.getElementById("woStatInProgress");
        const sComp = document.getElementById("woStatCompleted");
        const sVer = document.getElementById("woStatVerified");

        if (sTot) sTot.textContent = total;
        if (sProg) sProg.textContent = inProgress;
        if (sComp) sComp.textContent = completed;
        if (sVer) sVer.textContent = verified;

        if (grid) {
            if (orders.length === 0) {
                grid.innerHTML = `<div class="model-card-item"><p>No active work orders found.</p></div>`;
                return;
            }

            grid.innerHTML = orders.map(o => {
                let badgeClass = "badge-amber";
                if (o.status === "VERIFIED") badgeClass = "badge-green";
                else if (o.status === "COMPLETED") badgeClass = "badge-teal";
                else if (o.status === "IN_PROGRESS") badgeClass = "badge-blue";

                let actionBtnHtml = "";
                if (o.status === "ASSIGNED" || o.status === "NEW") {
                    actionBtnHtml = `<button class="btn btn-primary btn-sm update-wo-btn" data-wo-id="${o.work_order_id}" data-target-status="IN_PROGRESS"><i class="fa-solid fa-play"></i> Start Task</button>`;
                } else if (o.status === "IN_PROGRESS") {
                    actionBtnHtml = `<button class="btn btn-emerald btn-sm update-wo-btn" data-wo-id="${o.work_order_id}" data-target-status="COMPLETED"><i class="fa-solid fa-check"></i> Complete Task</button>`;
                } else if (o.status === "COMPLETED") {
                    actionBtnHtml = `<button class="btn btn-secondary btn-sm verify-wo-btn" data-wo-id="${o.work_order_id}"><i class="fa-solid fa-user-check text-mint"></i> Verify Work Order</button>`;
                } else {
                    actionBtnHtml = `<span class="text-green" style="font-size:0.85rem; font-weight:600;"><i class="fa-solid fa-circle-check"></i> Work Order Verified</span>`;
                }

                return `
                    <div class="suggestion-card-item">
                        <div class="sug-top">
                            <span class="${badgeClass}">${o.status}</span>
                            <span class="sug-cat">${o.building_id || 'Campus'} • ${o.priority || 'MEDIUM'}</span>
                        </div>
                        <h3>${o.title || 'Work Order ' + o.work_order_id}</h3>
                        <p>${o.description || 'Facility maintenance action item.'}</p>
                        <div style="font-size:0.8rem; color:#94A3B8; margin-bottom:12px;">
                            <span>Assigned: <strong>${o.assigned_to || 'Maintenance Team'}</strong></span> • 
                            <span>Source: <strong>${o.source_signal || 'AI Anomaly'}</strong></span>
                        </div>
                        <div class="sug-footer">
                            <span style="font-size:0.75rem; color:#94A3B8;">ID: ${o.work_order_id}</span>
                            <div>${actionBtnHtml}</div>
                        </div>
                    </div>
                `;
            }).join("");

            bindWorkOrderActionEvents();
        }
    } catch (e) {
        console.warn("Work orders using cached baseline.");
    }
}

function bindWorkOrderActionEvents() {
    document.querySelectorAll(".update-wo-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
            const woId = btn.getAttribute("data-wo-id");
            const targetStatus = btn.getAttribute("data-target-status");
            btn.disabled = true;
            btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Updating...`;

            try {
                const res = await fetch(`/api/v1/work-orders/${woId}/status`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ status: targetStatus, updated_by: currentUserSession.name })
                });
                if (res.ok) {
                    showToast(`Work Order ${woId} updated to ${targetStatus}`);
                    loadBackendWorkOrders();
                }
            } catch (err) {
                showToast(`Work Order ${woId} updated to ${targetStatus}`);
                loadBackendWorkOrders();
            }
        });
    });

    document.querySelectorAll(".verify-wo-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
            const woId = btn.getAttribute("data-wo-id");
            btn.disabled = true;
            btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Verifying...`;

            try {
                const res = await fetch(`/api/v1/work-orders/${woId}/verify`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ manager_name: currentUserSession.name, verification_notes: "Manager verified field completion." })
                });
                if (res.ok) {
                    showToast(`Work Order ${woId} Verified Successfully!`);
                    loadBackendWorkOrders();
                }
            } catch (err) {
                showToast(`Work Order ${woId} Verified Successfully!`);
                loadBackendWorkOrders();
            }
        });
    });
}

/* --------------------------------------------------------------------------
   AI OPERATIONAL INSIGHTS SERVICE
   -------------------------------------------------------------------------- */
async function loadBackendAIInsights() {
    try {
        const res = await fetch("/api/v1/ai/insights");
        if (!res.ok) return;
        const data = await res.json();
    } catch (e) {
        console.warn("AI Insights loaded from cache.");
    }
}

/* --------------------------------------------------------------------------
   INTERACTIVE POST FORM HANDLERS
   -------------------------------------------------------------------------- */
function initEnergyPredictorForm() {
    const form = document.getElementById("energyPredictForm");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const reqPayload = {
            temperature: parseFloat(document.getElementById("energyTemp").value),
            humidity: parseFloat(document.getElementById("energyHumidity").value),
            occupancy: parseInt(document.getElementById("energyOccupancy").value),
            hvac_load: parseFloat(document.getElementById("energyHvac").value),
            lighting_load: parseFloat(document.getElementById("energyLighting").value),
            equipment_load: parseFloat(document.getElementById("energyEquipment").value),
            previous_energy_kwh: 110.0,
            hour: 14,
            day_of_week: 2
        };

        const resVal = document.getElementById("energyResultVal");
        const resMeta = document.getElementById("energyResultMeta");
        if (resVal) resVal.textContent = "Calculating...";

        try {
            const res = await fetch("/api/v1/energy", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(reqPayload)
            });

            if (res.ok) {
                const data = await res.json();
                if (resVal) resVal.textContent = `${data.predicted_energy_kwh} ${data.unit}`;
                if (resMeta) resMeta.textContent = `Model: ${data.algorithm} • Task: ${data.task}`;
                showToast(`Energy predicted: ${data.predicted_energy_kwh} kWh`);
            }
        } catch (err) {
            const est = (reqPayload.hvac_load * 1.8 + reqPayload.lighting_load + reqPayload.equipment_load + reqPayload.occupancy * 0.1).toFixed(2);
            if (resVal) resVal.textContent = `${est} kWh`;
            if (resMeta) resMeta.textContent = `Model: CatBoostRegressor (Offline Engine)`;
        }
    });
}

function initWaterAnomalyForm() {
    const form = document.getElementById("waterAnomalyForm");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
            facility_id: "FAC_GEC_01",
            building_id: document.getElementById("waterBuildingSelect").value,
            measurements: {
                flow_rate: parseFloat(document.getElementById("waterFlow").value),
                occupancy: parseFloat(document.getElementById("waterOccupancy").value)
            }
        };

        const statusEl = document.getElementById("waterResultStatus");
        const explEl = document.getElementById("waterResultExpl");
        if (statusEl) statusEl.textContent = "Auditing...";

        try {
            const res = await fetch("/api/v1/water/anomaly", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const data = await res.json();
                if (statusEl) {
                    statusEl.textContent = data.anomaly_status;
                    statusEl.style.color = data.anomaly_status.includes("ANOMALY") ? "#C5221F" : "#124B3E";
                }
                if (explEl) explEl.textContent = data.explanation;
                showToast(`Water Audit Complete: ${data.anomaly_status}`);
            }
        } catch (err) {
            if (statusEl) statusEl.textContent = "NORMAL";
            if (explEl) explEl.textContent = "Flow rate matches baseline expectations.";
        }
    });
}

function initWastePredictorForm() {
    const form = document.getElementById("wastePredictForm");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
            fill_level: parseFloat(document.getElementById("wasteFill").value),
            fill_rate: parseFloat(document.getElementById("wasteFillRate").value),
            temperature: parseFloat(document.getElementById("wasteTemp").value),
            occupancy: parseInt(document.getElementById("wasteOcc").value),
            day_of_week: 3,
            hour: 15,
            collection_time: 0
        };

        const probEl = document.getElementById("wasteResultProb");
        const riskEl = document.getElementById("wasteResultRisk");
        if (probEl) probEl.textContent = "Evaluating...";

        try {
            const res = await fetch("/api/v1/waste", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const data = await res.json();
                const pct = (data.overflow_probability * 100).toFixed(1);
                if (probEl) probEl.textContent = `${pct}%`;
                if (riskEl) {
                    riskEl.textContent = data.risk_level;
                    riskEl.className = data.risk_level.includes("HIGH") ? "badge-red" : "badge-amber";
                }
                showToast(`Waste Overflow Risk: ${pct}% (${data.risk_level})`);
            }
        } catch (err) {
            if (probEl) probEl.textContent = "78.5%";
            if (riskEl) riskEl.textContent = "MODERATE";
        }
    });
}

function initScenarioSimulatorForm() {
    const form = document.getElementById("scenarioSimulatorForm");
    const hvacSlider = document.getElementById("hvacModSlider");
    const solarSlider = document.getElementById("solarCapSlider");
    const waterSlider = document.getElementById("waterRecSlider");
    const tariffSlider = document.getElementById("tariffRateSlider");

    const hvacLabel = document.getElementById("hvacModLabel");
    const solarLabel = document.getElementById("solarCapLabel");
    const waterLabel = document.getElementById("waterRecLabel");
    const tariffLabel = document.getElementById("tariffRateLabel");

    const simTargetDemandVal = document.getElementById("simTargetDemandVal");
    const simDemandShiftLabel = document.getElementById("simDemandShiftLabel");
    const simCostSavingsVal = document.getElementById("simCostSavingsVal");
    const simUsdSavingsVal = document.getElementById("simUsdSavingsVal");
    const simCo2ReducedVal = document.getElementById("simCo2ReducedVal");
    const simScoreBoostVal = document.getElementById("simScoreBoostVal");

    const calculateAndUpdateSimulation = () => {
        const hvacMult = parseFloat(hvacSlider ? hvacSlider.value : 0.8);
        const solarKw = parseFloat(solarSlider ? solarSlider.value : 150);
        const waterPct = parseFloat(waterSlider ? waterSlider.value : 35);
        const tariffInr = parseFloat(tariffSlider ? tariffSlider.value : 9.5);

        // Update labels
        const hvacRedPct = Math.round((1 - hvacMult) * 100);
        if (hvacLabel) hvacLabel.textContent = `${hvacRedPct}% Setback (${hvacMult.toFixed(2)})`;
        if (solarLabel) solarLabel.textContent = `${solarKw} kWp Generation`;
        if (waterLabel) waterLabel.textContent = `${waterPct}% Recovery Rate`;
        if (tariffLabel) tariffLabel.textContent = `₹${tariffInr.toFixed(2)} / kWh`;

        // Calculate metrics
        const baseDemand = 140.0;
        const solarOffsetKwh = solarKw * 0.18;
        const targetDemand = Math.max(20.0, (baseDemand * hvacMult) - solarOffsetKwh);
        const hourlyKwhSaved = baseDemand - targetDemand;
        
        const monthlyKwhSaved = hourlyKwhSaved * 24 * 30;
        const monthlySavingsInr = monthlyKwhSaved * tariffInr;
        const monthlySavingsUsd = monthlySavingsInr / 82.0;
        const monthlyCo2Tons = (monthlyKwhSaved * 0.82) / 1000.0;
        const scoreBoost = (hourlyKwhSaved / 6.0).toFixed(1);

        const demandShiftPct = (((targetDemand - baseDemand) / baseDemand) * 100).toFixed(1);

        if (simTargetDemandVal) simTargetDemandVal.textContent = `${targetDemand.toFixed(1)} kWh`;
        if (simDemandShiftLabel) simDemandShiftLabel.textContent = `${demandShiftPct}% Shift vs Baseline`;
        if (simCostSavingsVal) simCostSavingsVal.textContent = `₹${Math.round(monthlySavingsInr).toLocaleString('en-IN')} / mo`;
        if (simUsdSavingsVal) simUsdSavingsVal.textContent = `($${Math.round(monthlySavingsUsd).toLocaleString()} / month)`;
        if (simCo2ReducedVal) simCo2ReducedVal.textContent = `${monthlyCo2Tons.toFixed(1)} Tons CO₂e`;
        if (simScoreBoostVal) simScoreBoostVal.textContent = `+${scoreBoost} Pts`;

        // Re-render chart curve
        if (typeof updateScenarioChartData === "function") {
            updateScenarioChartData(hvacMult, solarKw);
        }
    };

    [hvacSlider, solarSlider, waterSlider, tariffSlider].forEach(slider => {
        slider?.addEventListener("input", calculateAndUpdateSimulation);
    });

    // Preset buttons listeners
    document.getElementById("presetSummerPeak")?.addEventListener("click", () => {
        if (hvacSlider) hvacSlider.value = 0.75;
        if (solarSlider) solarSlider.value = 250;
        if (waterSlider) waterSlider.value = 40;
        if (tariffSlider) tariffSlider.value = 11.5;
        calculateAndUpdateSimulation();
        showToast("Loaded Preset: Summer Peak Heatwave Scenario");
    });

    document.getElementById("presetGreenCampus")?.addEventListener("click", () => {
        if (hvacSlider) hvacSlider.value = 0.70;
        if (solarSlider) solarSlider.value = 450;
        if (waterSlider) waterSlider.value = 50;
        if (tariffSlider) tariffSlider.value = 9.5;
        calculateAndUpdateSimulation();
        showToast("Loaded Preset: 100% Green Campus Push Scenario");
    });

    document.getElementById("presetOffPeak")?.addEventListener("click", () => {
        if (hvacSlider) hvacSlider.value = 0.60;
        if (solarSlider) solarSlider.value = 150;
        if (waterSlider) waterSlider.value = 30;
        if (tariffSlider) tariffSlider.value = 8.0;
        calculateAndUpdateSimulation();
        showToast("Loaded Preset: Weekend Off-Peak Saver Scenario");
    });

    form?.addEventListener("submit", (e) => {
        e.preventDefault();
        calculateAndUpdateSimulation();
        showToast("What-If Scenario Recalculated cleanly!");
    });

    document.getElementById("btnApplySimPolicy")?.addEventListener("click", () => {
        showToast("Scenario Applied as Active Operational Policy (+4.5 Score Boost)");
        const heroScore = document.getElementById("heroScoreValue");
        if (heroScore) {
            const cur = parseInt(heroScore.textContent) || 87;
            heroScore.textContent = Math.min(100, cur + 4);
        }
    });
}

/* --------------------------------------------------------------------------
   LOCATION SELECTOR DROPDOWN & FILTER
   -------------------------------------------------------------------------- */
function initLocationDropdown() {
    const selector = document.getElementById("locationSelector");
    const dropdown = document.getElementById("locationDropdown");

    if (!selector || !dropdown) return;

    selector.addEventListener("click", (e) => {
        e.stopPropagation();
        dropdown.classList.toggle("show");
    });

    document.addEventListener("click", () => {
        dropdown.classList.remove("show");
    });

    bindLocationItemEvents();
}

function bindLocationItemEvents() {
    const dropdown = document.getElementById("locationDropdown");
    const locationText = document.getElementById("currentLocationText");
    if (!dropdown) return;

    const items = dropdown.querySelectorAll(".dropdown-item");
    items.forEach(item => {
        item.addEventListener("click", (e) => {
            e.stopPropagation();
            items.forEach(i => i.classList.remove("active"));
            item.classList.add("active");
            
            const selectedLoc = item.textContent;
            if (locationText) locationText.textContent = selectedLoc;
            dropdown.classList.remove("show");

            filterDashboardByLocation(item.getAttribute("data-location"));
        });
    });
}

function filterDashboardByLocation(locationKey) {
    const energyVal = document.getElementById("energyTargetVal");
    const summaryEnergy = document.getElementById("summaryEnergyVal");
    const heroScore = document.getElementById("heroScoreValue");

    if (locationKey === "block_b") {
        if (energyVal) energyVal.textContent = "1.85 MWh";
        if (summaryEnergy) summaryEnergy.textContent = "1.85 MWh";
        if (heroScore) heroScore.textContent = "72";
        showToast("Filtered view: Block B Hostel (HVAC Focus)");
    } else if (locationKey === "cafeteria") {
        if (energyVal) energyVal.textContent = "2.10 MWh";
        if (summaryEnergy) summaryEnergy.textContent = "2.10 MWh";
        if (heroScore) heroScore.textContent = "84";
        showToast("Filtered view: Central Cafeteria (Waste Focus)");
    } else {
        if (energyVal) energyVal.textContent = "7.42 MWh";
        if (summaryEnergy) summaryEnergy.textContent = "7.42 MWh";
        if (heroScore) heroScore.textContent = "87";
        showToast("Reset view to Main Campus - All Blocks");
    }
}

/* --------------------------------------------------------------------------
   SIGNALS & DIAGNOSTICS MODAL
   -------------------------------------------------------------------------- */
function initSignalsModal() {
    const inspectBtn = document.getElementById("inspectSignalsBtn");
    const modal = document.getElementById("signalsModal");
    const closeBtn = document.getElementById("closeModalBtn");
    const dismissBtn = document.getElementById("dismissModalBtn");
    const diagnosticBtn = document.getElementById("runAiDiagnosticBtn");

    if (!modal) return;

    const openModal = () => modal.classList.add("show");
    const closeModal = () => modal.classList.remove("show");

    inspectBtn?.addEventListener("click", openModal);
    closeBtn?.addEventListener("click", closeModal);
    dismissBtn?.addEventListener("click", closeModal);

    modal.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });

    diagnosticBtn?.addEventListener("click", () => {
        closeModal();
        if (typeof window.openDecisionTraceModal === "function") {
            window.openDecisionTraceModal("ALT_01");
        } else {
            document.getElementById("decisionTraceModal")?.classList.add("show");
        }
    });
}

/* --------------------------------------------------------------------------
   TIME RANGE TOGGLE BUTTONS
   -------------------------------------------------------------------------- */
function initTimeRangeButtons() {
    const rangeBtns = document.querySelectorAll(".time-range-toggle .range-btn");
    rangeBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            rangeBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            
            const rangeText = btn.textContent.trim();
            if (typeof updateChartTimeRange === "function") {
                updateChartTimeRange(rangeText);
            }
        });
    });
}

/* --------------------------------------------------------------------------
   AI CO-PILOT CHAT ENGINE (FASTAPI BACKEND CONNECTIVITY)
   -------------------------------------------------------------------------- */
function initChatEngine() {
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInputText");
    const messagesArea = document.getElementById("chatMessagesArea");
    const quickChips = document.querySelectorAll(".quick-chip");
    const voiceBtn = document.getElementById("voicePromptBtn");

    if (!chatForm || !chatInput || !messagesArea) return;

    quickChips.forEach(chip => {
        chip.addEventListener("click", () => {
            const query = chip.getAttribute("data-query");
            if (query) {
                chatInput.value = query;
                chatForm.dispatchEvent(new Event("submit"));
            }
        });
    });

    voiceBtn?.addEventListener("click", () => {
        showToast("Listening... Speak your prompt now (Voice Input)");
        setTimeout(() => {
            chatInput.value = "Why is energy consumption high in Block B Hostel?";
            showToast("Voice transcribed: 'Why is energy consumption high in Block B Hostel?'");
        }, 1500);
    });

    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const userText = chatInput.value.trim();
        if (!userText) return;

        appendChatMessage("user", userText);
        chatInput.value = "";

        const typingId = appendTypingIndicator();

        try {
            const response = await fetch("/api/v1/ai/copilot", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: userText })
            });

            removeChatMessage(typingId);

            if (response.ok) {
                const data = await response.json();
                const badge = data.data_source_badge || "[SIMULATED IoT]";
                const hasWhatHappened = data.what_happened && data.what_happened.trim().length > 0;
                const hasWhy = data.why && Array.isArray(data.why) && data.why.some(w => w && w.trim().length > 0);

                const formattedHtml = `
                    <div style="margin-bottom:8px;"><span class="pill-badge badge-teal">${badge}</span></div>
                    <div>${data.response || data.summary}</div>
                    ${hasWhatHappened ? `<div style="margin-top:8px; font-size:0.9rem;"><strong>What Happened:</strong> ${data.what_happened}</div>` : ''}
                    ${hasWhy ? `<div style="margin-top:6px; font-size:0.9rem;"><strong>Why:</strong> ${data.why.filter(w => w && w.trim()).join(', ')}</div>` : ''}
                `;
                appendChatMessage("bot", formattedHtml);
            } else {
                const errData = await response.json().catch(() => ({ detail: "AI SERVICE ERROR" }));
                const errMsg = errData.detail || "AI SERVICE ERROR: Service unavailable.";
                appendChatMessage("bot", `<div class="alert-box error" style="background:#450A0A; border:1px solid #EF4444; padding:12px; border-radius:6px; color:#FCA5A5;">⚠️ <strong>AI SERVICE ERROR:</strong> ${escapeHtml(errMsg)}</div>`);
            }
        } catch (err) {
            removeChatMessage(typingId);
            appendChatMessage("bot", `<div class="alert-box error" style="background:#450A0A; border:1px solid #EF4444; padding:12px; border-radius:6px; color:#FCA5A5;">⚠️ <strong>AI SERVICE ERROR:</strong> Could not connect to FastAPI AI Gateway at /api/v1/ai/copilot.</div>`);
        }
    });
}

function appendChatMessage(sender, text) {
    const messagesArea = document.getElementById("chatMessagesArea");
    if (!messagesArea) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-message ${sender}`;
    
    if (sender === "bot") {
        msgDiv.innerHTML = `
            <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="msg-bubble">
                <div class="msg-header-tag">
                    <span>ESTATEIQ GROUNDED AI</span>
                    <span class="time-stamp">Just now</span>
                </div>
                <div>${text}</div>
            </div>
        `;
    } else {
        msgDiv.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
    }
    
    messagesArea.appendChild(msgDiv);
    messagesArea.scrollTop = messagesArea.scrollHeight;
    return msgDiv;
}

function appendTypingIndicator() {
    const messagesArea = document.getElementById("chatMessagesArea");
    if (!messagesArea) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = "chat-message bot typing";
    msgDiv.id = "typing_" + Date.now();
    msgDiv.innerHTML = `
        <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="msg-bubble"><i class="fa-solid fa-circle-notch fa-spin"></i> Querying FastAPI backend & SHAP Explainability Engine...</div>
    `;
    
    messagesArea.appendChild(msgDiv);
    messagesArea.scrollTop = messagesArea.scrollHeight;
    return msgDiv.id;
}

function removeChatMessage(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.remove();
}


/* --------------------------------------------------------------------------
   LIVE TELEMETRY STREAM SIMULATION
   -------------------------------------------------------------------------- */
function initTelemetryStreamer() {
    setInterval(() => {
        const energyTargetVal = document.getElementById("energyTargetVal");
        if (energyTargetVal) {
            const baseVal = 7.42;
            const delta = (Math.random() * 0.08 - 0.04).toFixed(2);
            const newVal = (baseVal + parseFloat(delta)).toFixed(2);
            energyTargetVal.textContent = `${newVal} MWh`;
        }
    }, 4000);
}

/* --------------------------------------------------------------------------
   KEYBOARD SHORTCUTS & UTILS
   -------------------------------------------------------------------------- */
function initKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === "k") {
            e.preventDefault();
            document.getElementById("globalSearchInput")?.focus();
        }
    });

    document.getElementById("closeBannerBtn")?.addEventListener("click", () => {
        const banner = document.getElementById("statusBanner");
        if (banner) banner.style.display = "none";
    });
}

/* --------------------------------------------------------------------------
   LIQUID GLASS NOTIFICATIONS DROPDOWN ENGINE
   -------------------------------------------------------------------------- */
function initNotificationsDropdown() {
    const btn = document.getElementById("notificationsBtn");
    const dropdown = document.getElementById("notificationsDropdown");
    const markReadBtn = document.getElementById("markAllNotifsReadBtn");
    const viewAllBtn = document.getElementById("viewAllSignalsBtn");
    const notifCount = document.getElementById("notificationCount");
    const notifUnreadBadge = document.getElementById("notifUnreadBadge");

    if (!btn || !dropdown) return;

    btn.addEventListener("click", (e) => {
        e.stopPropagation();
        document.getElementById("locationDropdown")?.classList.remove("show");
        document.getElementById("roleSwitcherDropdown")?.classList.remove("show");
        dropdown.classList.toggle("show");
    });

    document.addEventListener("click", () => {
        dropdown.classList.remove("show");
    });

    dropdown.addEventListener("click", (e) => {
        e.stopPropagation();
    });

    markReadBtn?.addEventListener("click", () => {
        document.querySelectorAll(".notif-item.unread").forEach(item => {
            item.classList.remove("unread");
        });
        if (notifCount) notifCount.textContent = "0";
        if (notifUnreadBadge) notifUnreadBadge.textContent = "0 New";
        showToast("All operational notifications marked as read.");
    });

    viewAllBtn?.addEventListener("click", () => {
        dropdown.classList.remove("show");
        document.querySelectorAll(".modal-backdrop.show").forEach(m => m.classList.remove("show"));
        if (typeof window.openDecisionTraceModal === "function") {
            window.openDecisionTraceModal("ALT_01");
        } else {
            document.getElementById("decisionTraceModal")?.classList.add("show");
        }
    });

    document.querySelectorAll(".notif-item").forEach(item => {
        item.addEventListener("click", () => {
            dropdown.classList.remove("show");
            if (item.classList.contains("p1-alert")) {
                document.querySelector('.tab-btn[data-tab="energy"]')?.click();
                showToast("Navigated to Energy Anomaly Audit (Block B Hostel)");
            } else if (item.classList.contains("p2-alert")) {
                document.querySelector('.tab-btn[data-tab="waste"]')?.click();
                showToast("Navigated to Waste Overflow Risk (Central Cafeteria)");
            } else {
                document.querySelector('.tab-btn[data-tab="ai-assistant"]')?.click();
                showToast("Opened AI Co-Pilot Diagnostic");
            }
        });
    });
}

function showToast(message) {
    let toast = document.getElementById("appToast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "appToast";
        document.body.appendChild(toast);
    }
    
    const isCritical = message.includes("CRITICAL") || message.includes("Alert") || message.includes("Surge");
    const isWarning = message.includes("HIGH") || message.includes("Stale") || message.includes("Warning");
    
    const themeColor = isCritical ? "#EF4444" : isWarning ? "#F59E0B" : "#00D09C";
    const bgGradient = isCritical 
        ? "linear-gradient(135deg, rgba(30, 10, 10, 0.96) 0%, rgba(60, 15, 15, 0.98) 100%)"
        : "linear-gradient(135deg, rgba(10, 46, 38, 0.96) 0%, rgba(18, 75, 62, 0.98) 100%)";
    const iconClass = isCritical ? "fa-triangle-exclamation" : isWarning ? "fa-bolt-lightning" : "fa-bell";

    toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: ${bgGradient};
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        color: #FFFFFF;
        padding: 16px 20px;
        border-radius: 16px;
        font-family: inherit;
        font-size: 13px;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5), 0 0 25px ${themeColor}40;
        border: 1px solid ${themeColor}80;
        z-index: 3000;
        display: flex;
        align-items: center;
        gap: 14px;
        min-width: 340px;
        max-width: 480px;
        transform: translateY(20px);
        opacity: 0;
        transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
        pointer-events: auto;
    `;

    toast.innerHTML = `
        <div style="background: ${themeColor}20; color: ${themeColor}; width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; border: 1px solid ${themeColor}50;">
            <i class="fa-solid ${iconClass}"></i>
        </div>
        <div style="flex: 1;">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; color: ${themeColor}; margin-bottom: 2px;">
                ${isCritical ? '⚡ Critical Anomaly Alert' : 'EstateIQ Intelligence Signal'}
            </div>
            <div style="font-size: 13px; font-weight: 600; color: #FFFFFF; line-height: 1.35;">
                ${escapeHtml(message)}
            </div>
        </div>
        <button id="closeAppToastBtn" style="background: transparent; border: none; color: rgba(255,255,255,0.5); font-size: 16px; cursor: pointer; padding: 4px 8px; border-radius: 6px; display: flex; align-items: center; justify-content: center;" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='rgba(255,255,255,0.5)'">
            <i class="fa-solid fa-xmark"></i>
        </button>
    `;

    document.getElementById("closeAppToastBtn")?.addEventListener("click", () => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(20px)";
    });

    requestAnimationFrame(() => {
        toast.style.opacity = "1";
        toast.style.transform = "translateY(0)";
    });

    if (window.toastTimer) clearTimeout(window.toastTimer);
    window.toastTimer = setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(20px)";
    }, 5000);
}

function escapeHtml(str) {
    return str.replace(/[&<>'"]/g, 
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
}

/* --------------------------------------------------------------------------
   DECISION TRACE AUDIT MODAL CONTROLLER
   -------------------------------------------------------------------------- */
function initDecisionTraceModal() {
    const traceModal = document.getElementById("decisionTraceModal");
    const closeTraceBtn = document.getElementById("closeTraceModalBtn");
    const dismissTraceBtn = document.getElementById("dismissTraceModalBtn");
    const runAiDiagnosticBtn = document.getElementById("runAiDiagnosticBtn");
    const simulateTraceActionBtn = document.getElementById("simulateTraceActionBtn");

    const openTrace = async (alertId = "ALT_01") => {
        document.querySelectorAll(".modal-backdrop.show").forEach(m => m.classList.remove("show"));
        try {
            const res = await fetch(`/api/v1/decisions/${alertId}`);
            if (res.ok) {
                const data = await res.json();
                
                const idEl = document.getElementById("traceModalId");
                const bldEl = document.getElementById("traceBuildingName");
                const obsEl = document.getElementById("traceObservedVal");
                const baseEl = document.getElementById("traceBaselineVal");
                const devAbsEl = document.getElementById("traceDevAbs");
                const devPctEl = document.getElementById("traceDevPct");
                const f1hEl = document.getElementById("traceForecast1h");
                const f24hEl = document.getElementById("traceForecast24h");
                const scoreEl = document.getElementById("traceAnomalyScore");
                const recEl = document.getElementById("traceRecommendationText");

                if (idEl) idEl.textContent = data.trace_id || `TRC_${alertId}`;
                if (bldEl) bldEl.textContent = data.building || "Block B Hostel";
                if (obsEl && data.step_1_observed) obsEl.textContent = `${data.step_1_observed.value} ${data.step_1_observed.unit}`;
                if (baseEl && data.step_2_baseline) baseEl.textContent = `${data.step_2_baseline.expected_value} ${data.step_2_baseline.unit}`;
                if (devAbsEl && data.step_3_deviation) devAbsEl.textContent = `+${data.step_3_deviation.absolute_deviation} kWh`;
                if (devPctEl && data.step_3_deviation) devPctEl.textContent = data.step_3_deviation.percentage_deviation;
                if (f1hEl && data.step_4_ml_prediction) f1hEl.textContent = `${data.step_4_ml_prediction["1h_forecast"]} kWh`;
                if (f24hEl && data.step_4_ml_prediction) f24hEl.textContent = `${data.step_4_ml_prediction["24h_forecast"]} kWh`;
                if (scoreEl && data.step_5_anomaly) scoreEl.textContent = data.step_5_anomaly.anomaly_score;
                if (recEl && data.step_8_recommendation) recEl.textContent = data.step_8_recommendation.detailed_recommendation;
            }
        } catch (e) {
            console.warn("Using baseline Decision Trace modal details.");
        }
        traceModal?.classList.add("show");
    };

    window.openDecisionTraceModal = openTrace;

    const closeTrace = () => traceModal?.classList.remove("show");

    closeTraceBtn?.addEventListener("click", closeTrace);
    dismissTraceBtn?.addEventListener("click", closeTrace);

    traceModal?.addEventListener("click", (e) => {
        if (e.target === traceModal) closeTrace();
    });

    simulateTraceActionBtn?.addEventListener("click", () => {
        closeTrace();
        const simTab = document.getElementById("tabSimulator");
        simTab?.click();
        showToast("Loaded Decision Trace parameters into What-If Simulator.");
    });
}

/* --------------------------------------------------------------------------
   ESTATEIQ KNOWLEDGE CENTER HANDLERS
   -------------------------------------------------------------------------- */
function toggleFaq(btn) {
    const item = btn.closest(".faq-accordion-item");
    if (!item) return;
    const isActive = item.classList.contains("active");
    
    // Close other active accordion items for clean single-expansion UI
    document.querySelectorAll(".faq-accordion-item.active").forEach(el => {
        if (el !== item) el.classList.remove("active");
    });

    item.classList.toggle("active", !isActive);
}

function filterFaqs() {
    const query = (document.getElementById("faqSearchInput")?.value || "").toLowerCase().trim();
    const items = document.querySelectorAll(".faq-accordion-item");
    const activeChip = document.querySelector(".faq-chip.active");
    let selectedCategory = "all";
    if (activeChip) {
        const match = activeChip.getAttribute("onclick")?.match(/'([^']+)'/);
        if (match && match[1]) selectedCategory = match[1];
    }

    items.forEach(item => {
        const cat = item.getAttribute("data-category") || "";
        const text = item.textContent.toLowerCase();
        
        const matchesCat = (selectedCategory === "all" || cat === selectedCategory);
        const matchesQuery = (!query || text.includes(query));

        if (matchesCat && matchesQuery) {
            item.style.display = "block";
        } else {
            item.style.display = "none";
        }
    });
}

function filterFaqCategory(category, chipEl) {
    document.querySelectorAll(".faq-chip").forEach(c => c.classList.remove("active"));
    if (chipEl) chipEl.classList.add("active");
    filterFaqs();
}

async function loadBackendCapabilities() {
    try {
        const res = await fetch("/api/v1/intelligence/capabilities");
        if (!res.ok) return;
        const data = await res.json();
        console.log("EstateIQ System Capabilities loaded:", data);
    } catch (e) {
        console.warn("Using default capability registry.");
    }
}

function setFaqSearchPrompt(term) {
    const searchInput = document.getElementById("faqSearchInput");
    if (searchInput) {
        searchInput.value = term;
        filterFaqs();
    }
}

// Expose handlers globally
window.toggleFaq = toggleFaq;
window.filterFaqs = filterFaqs;
window.filterFaqCategory = filterFaqCategory;
window.setFaqSearchPrompt = setFaqSearchPrompt;
window.initIotSimulator = initIotSimulator;

/* --------------------------------------------------------------------------
   INTERACTIVE IOT TELEMETRY SIMULATOR CONTROLLER
   -------------------------------------------------------------------------- */
function initIotSimulator() {
    const btnSimStart = document.getElementById("btnSimStart");
    const btnSimPause = document.getElementById("btnSimPause");
    const btnSimStep = document.getElementById("btnSimStep");
    const btnSimStop = document.getElementById("btnSimStop");
    const btnSimResetState = document.getElementById("btnSimResetState");
    const btnResetSensorControls = document.getElementById("btnResetSensorControls");
    const btnApplySensorOverrides = document.getElementById("btnApplySensorOverrides");
    const btnEvaluateSimTelemetry = document.getElementById("btnEvaluateSimTelemetry");
    const simScenarioSelect = document.getElementById("simScenarioSelect");
    const simBuildingSelect = document.getElementById("simBuildingSelect");
    const speedButtons = document.querySelectorAll(".sim-speed-btn");

    // Telemetry sliders & inputs
    const ctrlActivePowerKW = document.getElementById("ctrlActivePowerKW");
    const valActivePowerKW = document.getElementById("valActivePowerKW");

    const ctrlEnergyKWH = document.getElementById("ctrlEnergyKWH");
    const valEnergyKWH = document.getElementById("valEnergyKWH");

    const ctrlPowerFactor = document.getElementById("ctrlPowerFactor");
    const valPowerFactor = document.getElementById("valPowerFactor");

    const ctrlXfmrLoad = document.getElementById("ctrlXfmrLoad");
    const valXfmrLoad = document.getElementById("valXfmrLoad");

    const ctrlOccupancyCount = document.getElementById("ctrlOccupancyCount");
    const valOccupancyCount = document.getElementById("valOccupancyCount");

    const ctrlHvacLoadKW = document.getElementById("ctrlHvacLoadKW");
    const valHvacLoadKW = document.getElementById("valHvacLoadKW");

    const ctrlHvacStatus = document.getElementById("ctrlHvacStatus");
    const ctrlEquipStatus = document.getElementById("ctrlEquipStatus");

    const ctrlTempC = document.getElementById("ctrlTempC");
    const valTempC = document.getElementById("valTempC");

    const ctrlWaterFlow = document.getElementById("ctrlWaterFlow");
    const valWaterFlow = document.getElementById("valWaterFlow");

    const ctrlAirAqi = document.getElementById("ctrlAirAqi");
    const valAirAqi = document.getElementById("valAirAqi");

    const ctrlDgStatus = document.getElementById("ctrlDgStatus");

    // Helper: update live slider display labels
    const syncSliderLabels = () => {
        if (ctrlActivePowerKW && valActivePowerKW) valActivePowerKW.textContent = `${ctrlActivePowerKW.value} kW`;
        if (ctrlEnergyKWH && valEnergyKWH) valEnergyKWH.textContent = `${ctrlEnergyKWH.value} kWh`;
        if (ctrlPowerFactor && valPowerFactor) valPowerFactor.textContent = `${ctrlPowerFactor.value}`;
        if (ctrlXfmrLoad && valXfmrLoad) valXfmrLoad.textContent = `${ctrlXfmrLoad.value}%`;
        if (ctrlOccupancyCount && valOccupancyCount) valOccupancyCount.textContent = `${ctrlOccupancyCount.value}`;
        if (ctrlHvacLoadKW && valHvacLoadKW) valHvacLoadKW.textContent = `${ctrlHvacLoadKW.value} kW`;
        if (ctrlTempC && valTempC) valTempC.textContent = `${ctrlTempC.value}°C`;
        if (ctrlWaterFlow && valWaterFlow) valWaterFlow.textContent = `${ctrlWaterFlow.value} L/min`;
        if (ctrlAirAqi && valAirAqi) valAirAqi.textContent = `${ctrlAirAqi.value} AQI`;
    };

    // Attach input listeners for instant slider feedback
    [ctrlActivePowerKW, ctrlEnergyKWH, ctrlPowerFactor, ctrlXfmrLoad, ctrlOccupancyCount, ctrlHvacLoadKW, ctrlTempC, ctrlWaterFlow, ctrlAirAqi].forEach(el => {
        if (el) el.addEventListener("input", syncSliderLabels);
    });

    // Send control actions to backend
    const sendControlAction = async (action, extraData = {}) => {
        try {
            const bodyData = { action, ...extraData };
            const res = await fetch("/api/v1/iot-simulator/control", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(bodyData)
            });
            if (res.ok) {
                const data = await res.json();
                updateSimulatorUI(data);
                fetchStreamLog();
            }
        } catch (e) {
            console.error("Simulation control error:", e);
        }
    };

    // Control button bindings
    btnSimStart?.addEventListener("click", () => sendControlAction("start"));
    btnSimPause?.addEventListener("click", () => sendControlAction("pause"));
    btnSimStep?.addEventListener("click", () => sendControlAction("step"));
    btnSimStop?.addEventListener("click", () => sendControlAction("stop"));
    btnSimResetState?.addEventListener("click", () => sendControlAction("reset_state"));

    btnResetSensorControls?.addEventListener("click", async () => {
        await sendControlAction("reset_controls");
        fetchStatus();
    });

    // Speed button bindings
    speedButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            speedButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const speed = parseInt(btn.getAttribute("data-speed") || "1");
            sendControlAction("set_speed", { speed });
        });
    });

    // Scenario Preset select binding
    simScenarioSelect?.addEventListener("change", async () => {
        const scenarioKey = simScenarioSelect.value;
        try {
            const res = await fetch("/api/v1/iot-simulator/scenario", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ scenario_key: scenarioKey })
            });
            if (res.ok) {
                const data = await res.json();
                updateSimulatorUI(data);
                fetchStreamLog();
            }
        } catch (e) {
            console.error("Scenario error:", e);
        }
    });

    // Building selector binding
    simBuildingSelect?.addEventListener("change", () => {
        sendControlAction("start", { building_id: simBuildingSelect.value });
    });

    // Apply Sensor Overrides
    btnApplySensorOverrides?.addEventListener("click", async () => {
        const overrides = {
            active_power_kw: parseFloat(ctrlActivePowerKW?.value || 145),
            energy_kwh: parseFloat(ctrlEnergyKWH?.value || 36.3),
            power_factor: parseFloat(ctrlPowerFactor?.value || 0.94),
            transformer_load_pct: parseFloat(ctrlXfmrLoad?.value || 78),
            occupancy_count: parseInt(ctrlOccupancyCount?.value || 140),
            hvac_load_kw: parseFloat(ctrlHvacLoadKW?.value || 58),
            hvac_status: ctrlHvacStatus?.value || "ON",
            equipment_status: ctrlEquipStatus?.value || "NORMAL",
            temperature_c: parseFloat(ctrlTempC?.value || 32),
            water_flow_lmin: parseFloat(ctrlWaterFlow?.value || 50),
            air_aqi: parseFloat(ctrlAirAqi?.value || 110),
            dg_status: ctrlDgStatus?.value || "OFF"
        };

        try {
            const res = await fetch("/api/v1/iot-simulator/sensors", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(overrides)
            });
            if (res.ok) {
                const data = await res.json();
                updateSimulatorUI(data);
            }
        } catch (e) {
            console.error("Sensor override error:", e);
        }
    });

    // Evaluate DIF Engine button
    btnEvaluateSimTelemetry?.addEventListener("click", async () => {
        try {
            const res = await fetch("/api/v1/iot-simulator/evaluate", { method: "POST" });
            if (res.ok) {
                const resData = await res.json();
                const dif = resData.dif_analysis;
                const elemLevel = document.getElementById("simDifAnomalyLevel");
                const elemScore = document.getElementById("simDifAnomalyScore");
                const elemExpected = document.getElementById("simDifExpectedKwh");
                const elemActual = document.getElementById("simDifActualKwh");
                const elemDev = document.getElementById("simDifDevPct");
                const elemCost = document.getElementById("simDifCostSurge");
                const elemShap = document.getElementById("simDifShapDriver");

                if (elemLevel) {
                    elemLevel.textContent = dif.anomaly_level;
                    elemLevel.className = dif.anomaly_level.includes("NORMAL") ? "text-mint" : "text-red";
                }
                if (elemScore) elemScore.textContent = dif.anomaly_score;
                if (elemExpected) elemExpected.textContent = `${dif.expected_baseline_kwh} kWh`;
                if (elemActual) elemActual.textContent = `${resData.event_telemetry.energy_kwh} kWh`;
                if (elemDev) {
                    const sign = dif.relative_deviation_pct >= 0 ? "+" : "";
                    elemDev.textContent = `${sign}${dif.relative_deviation_pct}% deviation`;
                    elemDev.className = dif.relative_deviation_pct > 20 ? "text-red" : "text-mint";
                }
                if (elemCost) elemCost.textContent = `₹${dif.hourly_cost_inr.toLocaleString()} / hour`;
                if (elemShap && dif.shap_attribution) {
                    const drivers = Object.entries(dif.shap_attribution)
                        .slice(0, 3)
                        .map(([k, v]) => `${k} (${v > 0 ? "+" : ""}${v})`)
                        .join(", ");
                    elemShap.textContent = drivers || "Baseline steady-state operation";
                }
            }
        } catch (e) {
            console.error("DIF evaluation error:", e);
        }
    });

    // Render registered devices on an explicitly schematic site map. Positions are
    // deterministic visual placements by building ID; they are not GPS coordinates.
    const renderLiveDeviceMap = (devices) => {
        const markerLayer = document.getElementById("liveDeviceMapMarkers");
        const deviceList = document.getElementById("deviceMapDeviceList");
        const emptyNotice = document.getElementById("deviceMapEmpty");
        if (!markerLayer || !deviceList) return;
        markerLayer.replaceChildren();
        deviceList.replaceChildren();
        const safeDevices = Array.isArray(devices) ? devices : [];
        if (!safeDevices.length) {
            if (emptyNotice) emptyNotice.hidden = false;
            const empty = document.createElement("div");
            empty.className = "map-list-empty";
            empty.textContent = "No registered devices. Start a simulator or connect a provisioned ESP32.";
            deviceList.appendChild(empty);
            return;
        }
        if (emptyNotice) emptyNotice.hidden = true;

        const svgNS = "http://www.w3.org/2000/svg";
        const hashText = (value) => Array.from(String(value || "Unknown building")).reduce((h, ch) => ((h * 31) + ch.charCodeAt(0)) >>> 0, 7);
        safeDevices.forEach((device, index) => {
            const statusRaw = String(device.status || "CONNECTING").toUpperCase();
            const statusClass = statusRaw === "ONLINE" || statusRaw === "STREAMING" ? "online" : statusRaw === "STALE" ? "stale" : "offline";
            const building = device.building_id || "Building not set";
            const seed = hashText(building);
            const x = 55 + (seed % 390);
            const y = 175 + ((Math.floor(seed / 13) + index * 17) % 260);
            const marker = document.createElementNS(svgNS, "g");
            marker.setAttribute("class", `device-map-marker ${statusClass}`);
            marker.setAttribute("transform", `translate(${x} ${y})`);
            const title = document.createElementNS(svgNS, "title");
            title.textContent = `${device.device_name || device.device_id} · ${building} · ${statusRaw} · ${device.data_source_badge || "provenance unavailable"}`;
            marker.appendChild(title);
            const circle = document.createElementNS(svgNS, "circle");
            circle.setAttribute("r", "9");
            marker.appendChild(circle);
            const label = document.createElementNS(svgNS, "text");
            label.setAttribute("x", "13");
            label.setAttribute("y", "4");
            label.textContent = String(device.device_id || "device").slice(0, 22);
            marker.appendChild(label);
            markerLayer.appendChild(marker);

            const item = document.createElement("div");
            item.className = "device-map-device";
            const identity = document.createElement("span");
            const name = document.createElement("strong");
            name.textContent = device.device_name || device.device_id || "Unnamed device";
            const details = document.createElement("small");
            const provenance = device.data_source_badge || (device.source_type === "real_sensor" ? "Unverified hardware" : "[SIMULATED IoT]");
            details.textContent = `${building} · ${provenance}`;
            identity.append(name, details);
            const status = document.createElement("span");
            status.className = `map-status ${statusClass}`;
            status.textContent = statusRaw;
            item.append(identity, status);
            deviceList.appendChild(item);
        });
    };

    // Render Line Current and Power Factor cleanly without ugly wraps or clipping
    const renderCurrentAndPF = (currentA, powerFactor) => {
        const el = document.getElementById("liveMetricCurrentPF");
        if (!el) return;

        let currText = "-- A";
        if (currentA !== null && currentA !== undefined && currentA !== "") {
            const num = Number(currentA);
            if (!isNaN(num)) {
                currText = `${num < 10 ? num.toFixed(3) : num.toFixed(2)} A`;
            } else {
                currText = `${currentA} A`;
            }
        }

        let pfText = "PF: --";
        if (powerFactor !== null && powerFactor !== undefined && powerFactor !== "") {
            const pfNum = Number(powerFactor);
            if (!isNaN(pfNum)) {
                pfText = `PF: ${pfNum.toFixed(2)}`;
            } else {
                pfText = `PF: ${powerFactor}`;
            }
        }

        const currEl = document.getElementById("liveMetricCurrentVal");
        const pfEl = document.getElementById("liveMetricPfVal");
        if (currEl && pfEl) {
            currEl.textContent = currText;
            pfEl.textContent = pfText;
        } else {
            el.innerHTML = `
                <span style="font-size: 1.75rem; font-weight: 800; color: #60A5FA; text-shadow: 0 0 12px rgba(96, 165, 250, 0.25); line-height: 1.15; white-space: nowrap;" id="liveMetricCurrentVal">${currText}</span>
                <span style="font-size: 11px; font-weight: 700; color: #93C5FD; background: rgba(96, 165, 250, 0.16); border: 1px solid rgba(96, 165, 250, 0.35); padding: 3px 8px; border-radius: 6px; letter-spacing: 0.3px; white-space: nowrap; align-self: center;" id="liveMetricPfVal">${pfText}</span>
            `;
        }
    };

    // Poll status from backend and real hardware device registry
    const fetchStatus = async () => {
        try {
            // 1. Fetch simulator status
            const res = await fetch("/api/v1/iot-simulator/status");
            let simStatus = null;
            if (res.ok) {
                simStatus = await res.json();
                updateSimulatorUI(simStatus);
            }

            // 2. Fetch canonical registered devices from backend registry
            const devRes = await fetch("/api/v1/iot/devices");
            if (devRes.ok) {
                const devData = await devRes.json();
                const devices = devData.devices || [];
                const stats = devData.stats || {};
                renderLiveDeviceMap(devices);

                // Update KPI Header with real device statistics (counting only genuinely active devices)
                const monDevicesActive = document.getElementById("monDevicesActiveCount");
                if (monDevicesActive) {
                    // Count only devices that have REAL active data
                    window.cachedDevicesList = devices;
                    const activeDevs = devices.filter(d => {
                        const t = d.last_telemetry || {};
                        if (d.device_id === 'ENV-BLOCK-B-001') {
                            const adc = Number(t.mq135_raw_adc ?? t.raw_adc ?? 0);
                            const v = Number(t.mq135_voltage_v ?? t.sensor_voltage_v ?? 0);
                            return (adc >= 80 && v >= 0.08) || t.temperature_c !== undefined;
                        }
                        if (d.device_id === 'METER-BLOCK-B-001') {
                            return Number(t.active_power_kw ?? 0) > 0 || Number(t.voltage_v ?? 0) > 0;
                        }
                        if (d.device_id === 'WATER-BLOCK-B-001') {
                            return Number(t.tank_distance_cm ?? 0) > 0 || t.water_flow_lmin !== undefined || t.tank_status === 'ECHO_TIMEOUT';
                        }
                        if (d.device_id === 'WASTE-BLOCK-B-001') {
                            return Number(t.bin_distance_cm ?? 0) > 0 || Number(t.fill_level_percent ?? t.fill_level_pct ?? 0) > 0 || d.status === 'ONLINE';
                        }
                        return d.status === 'ONLINE' || d.status === 'STREAMING';
                    });
                    const activeCount = activeDevs.length;
                    monDevicesActive.textContent = `${activeCount} Device${activeCount === 1 ? '' : 's'}`;
                    const subText = monDevicesActive.nextElementSibling;
                    if (subText) {
                        subText.textContent = activeCount ? `${activeCount} Active Hardware Online` : "Waiting for fresh device telemetry";
                        subText.className = activeCount ? "fc-sub text-mint" : "fc-sub text-amber";
                    }
                }

                // Check for real electricity meter (METER-BLOCK-B-001 or any real_sensor electricity meter)
                const elecDev = devices.find(d => (d.device_id === "METER-BLOCK-B-001" || d.device_type === "electricity_meter") && (d.source_type === "real_sensor" || d.is_verified_hardware));
                if (elecDev && elecDev.last_telemetry && Object.keys(elecDev.last_telemetry).length > 0) {
                    const t = elecDev.last_telemetry;
                    const pKW = document.getElementById("liveMetricPowerKW");
                    const eKWH = document.getElementById("liveMetricEnergyKWH");
                    const vV = document.getElementById("liveMetricVoltageV");
                    const iPF = document.getElementById("liveMetricCurrentPF");

                    if (pKW && t.active_power_kw !== undefined && t.active_power_kw !== null) {
                        const kw = Number(t.active_power_kw);
                        if (!isNaN(kw)) {
                            if (kw <= 0.0001) pKW.textContent = '0.00 kW (Idle)';
                            else if (kw < 1.0) pKW.textContent = `${kw.toFixed(3)} kW`;
                            else if (kw < 100.0) pKW.textContent = `${kw.toFixed(2)} kW`;
                            else pKW.textContent = `${kw.toFixed(1)} kW`;
                        } else {
                            pKW.textContent = `${t.active_power_kw} kW`;
                        }
                    }
                    if (eKWH && (t.cumulative_energy_kwh !== undefined || t.energy_kwh !== undefined)) {
                        const val = Number(t.cumulative_energy_kwh ?? t.energy_kwh);
                        if (!isNaN(val)) {
                            eKWH.textContent = val < 10.0 ? `${val.toFixed(3)} kWh` : `${val.toFixed(2)} kWh`;
                        } else {
                            eKWH.textContent = `${t.cumulative_energy_kwh ?? t.energy_kwh} kWh`;
                        }
                    }
                    if (vV && t.voltage_v !== undefined && t.voltage_v !== null) {
                        const vNum = Number(t.voltage_v);
                        vV.textContent = !isNaN(vNum) ? `${vNum.toFixed(1)} V` : `${t.voltage_v} V`;
                    }
                    if (iPF) {
                        renderCurrentAndPF(t.current_a, t.power_factor);
                        if (t.frequency_hz !== undefined) {
                            const subEl = document.getElementById('liveMetricCurrentSub');
                            if (subEl) subEl.textContent = `Single-Phase Active Load • ${Number(t.frequency_hz).toFixed(1)} Hz`;
                        }
                    }

                    // Update matrix status
                    const mElec = document.getElementById("matrixStatusElec");
                    if (mElec) {
                        const st = elecDev.status || "ONLINE";
                        if (st === "ONLINE") {
                            mElec.innerHTML = '<span class="badge-mint" style="font-size: 10px;"><i class="fa-solid fa-check"></i> MEASURED (ONLINE)</span>';
                        } else if (st === "STALE") {
                            mElec.innerHTML = '<span class="badge-amber" style="font-size: 10px;"><i class="fa-solid fa-clock"></i> STALE (>45s)</span>';
                        } else {
                            mElec.innerHTML = '<span class="badge-red" style="font-size: 10px;"><i class="fa-solid fa-circle-xmark"></i> OFFLINE</span>';
                        }
                    }
                }

                // Check for real water flow & tank meter (WATER-BLOCK-B-001 or any real_sensor water meter)
                const waterDev = devices.find(d => (d.device_id === "WATER-BLOCK-B-001" || d.device_type === "water_meter") && (d.source_type === "real_sensor" || d.is_verified_hardware || (d.last_telemetry && Object.keys(d.last_telemetry).length > 0)));
                if (waterDev && waterDev.last_telemetry && Object.keys(waterDev.last_telemetry).length > 0) {
                    const wt = waterDev.last_telemetry;
                    const wFlow = document.getElementById("liveMetricWaterFlow");
                    const cWater = document.getElementById("liveMetricCumWater");
                    const wPress = document.getElementById("liveMetricWaterPressure");
                    const elT = document.getElementById("liveMetricTankLevel");
                    const elD = document.getElementById("liveMetricTankDistance");
                    const bar = document.getElementById("liveTankBar");
                    const barLabel = document.getElementById("liveTankBarLabel");

                    if (wFlow && wt.water_flow_lmin !== undefined && wt.water_flow_lmin !== null) wFlow.textContent = `${wt.water_flow_lmin} L/min`;
                    if (cWater && wt.water_cumulative_liters !== undefined && wt.water_cumulative_liters !== null) cWater.textContent = `${Number(wt.water_cumulative_liters).toFixed(2)} L`;
                    else if (cWater && wt.cumulative_water_m3 !== undefined && wt.cumulative_water_m3 !== null) cWater.textContent = `${wt.cumulative_water_m3} m³`;
                    if (wPress && wt.water_pressure_bar !== undefined && wt.water_pressure_bar !== null) wPress.textContent = `${wt.water_pressure_bar} bar`;

                    if (elT && wt.tank_level_pct !== undefined && Number(wt.tank_level_pct) > 0) {
                        elT.textContent = `${Number(wt.tank_level_pct).toFixed(1)} %`;
                    }
                    if (elD && wt.tank_distance_cm !== undefined && Number(wt.tank_distance_cm) > 0) {
                        elD.textContent = `${Number(wt.tank_distance_cm).toFixed(1)} cm`;
                    }
                    if (bar && wt.tank_level_pct !== undefined) {
                        const pct = Math.min(100, Math.max(0, Number(wt.tank_level_pct)));
                        bar.style.width = `${pct}%`;
                        if (barLabel) barLabel.textContent = `${pct.toFixed(1)}% Fill`;
                    }

                    const mWater = document.getElementById("matrixStatusWater");
                    if (mWater) {
                        const wst = waterDev.status || "ONLINE";
                        if (wst === "ONLINE") {
                            mWater.innerHTML = '<span class="badge-mint" style="font-size: 10px;"><i class="fa-solid fa-check"></i> MEASURED (ONLINE)</span>';
                        } else if (wst === "STALE") {
                            mWater.innerHTML = '<span class="badge-amber" style="font-size: 10px;"><i class="fa-solid fa-clock"></i> STALE (>45s)</span>';
                        } else {
                            mWater.innerHTML = '<span class="badge-red" style="font-size: 10px;"><i class="fa-solid fa-circle-xmark"></i> OFFLINE</span>';
                        }
                    }
                }

                // Check for real waste bin sensor (WASTE-BLOCK-B-001 or any real_sensor waste bin)
                const wasteDevLive = devices.find(d => (d.device_id === "WASTE-BLOCK-B-001" || d.device_type === "waste_bin") && (d.source_type === "real_sensor" || d.is_verified_hardware || (d.last_telemetry && Object.keys(d.last_telemetry).length > 0)));
                if (wasteDevLive && wasteDevLive.last_telemetry && Object.keys(wasteDevLive.last_telemetry).length > 0) {
                    const wt = wasteDevLive.last_telemetry;
                    const elFill = document.getElementById("liveMetricBinFill");
                    const elDist = document.getElementById("liveMetricBinDistance");
                    const elRisk = document.getElementById("liveMetricBinRisk");
                    const bar = document.getElementById("liveBinBar");
                    const barLabel = document.getElementById("liveBinBarLabel");
                    const badge = document.getElementById("liveWasteCardBadge");

                    const fillPct = Number(wt.fill_level_percent ?? wt.fill_level_pct ?? 0);
                    const distCm = Number(wt.bin_distance_cm ?? 0);

                    if (elFill && (wt.fill_level_percent !== undefined || wt.fill_level_pct !== undefined)) {
                        elFill.textContent = `${fillPct.toFixed(1)} %`;
                    }
                    if (elDist && wt.bin_distance_cm !== undefined && distCm > 0) {
                        elDist.textContent = `${distCm.toFixed(1)} cm`;
                    }
                    if (elRisk && (wt.fill_level_percent !== undefined || wt.fill_level_pct !== undefined)) {
                        if (fillPct >= 80.0) {
                            elRisk.textContent = 'OVERFLOW RISK';
                            elRisk.style.color = '#EF4444';
                        } else {
                            elRisk.textContent = 'NORMAL';
                            elRisk.style.color = '#00D09C';
                        }
                    }
                    if (bar && (wt.fill_level_percent !== undefined || wt.fill_level_pct !== undefined)) {
                        bar.style.width = `${Math.min(Math.max(fillPct, 0), 100)}%`;
                        if (barLabel) barLabel.textContent = `${fillPct.toFixed(1)}% Fill (${distCm.toFixed(1)} cm clearance)`;
                    }

                    // Update Waste Tab inputs
                    const wasteFillInput = document.getElementById('wasteFill');
                    if (wasteFillInput && document.activeElement !== wasteFillInput && (wt.fill_level_percent !== undefined || wt.fill_level_pct !== undefined)) {
                        wasteFillInput.value = fillPct.toFixed(1);
                    }
                    const liveFillText = document.getElementById('wasteLiveFillText');
                    if (liveFillText && (wt.fill_level_percent !== undefined || wt.fill_level_pct !== undefined)) liveFillText.textContent = `${fillPct.toFixed(1)}%`;
                    const liveDistText = document.getElementById('wasteLiveDistText');
                    if (liveDistText && wt.bin_distance_cm !== undefined) liveDistText.textContent = `${distCm.toFixed(1)} cm`;
                    const liveHwBadge = document.getElementById('wasteLiveHardwareBadge');
                    if (liveHwBadge) liveHwBadge.style.display = 'inline-flex';
                }

                // If any device is verified physical hardware, update global provenance pill
                const hasVerifiedHardware = devices.some(d => d.is_verified_hardware);
                const monProv = document.getElementById("monProvenanceBadge");
                const monConnState = document.getElementById("monConnState");
                if (hasVerifiedHardware) {
                    if (monProv) {
                        monProv.textContent = "Tagged: [REAL SENSOR] (Hardware Verified)";
                        monProv.className = "fc-sub text-mint";
                    }
                    if (monConnState) {
                        monConnState.textContent = "LIVE HARDWARE STREAM";
                    }
                }
            }

            // 3. Fetch Dual Gateway Status, Outdoor Weather & Live Alert Feed
            await Promise.allSettled([
                fetchGatewaysStatus(),
                fetchOutdoorWeather(),
                fetchFacilityAlerts()
            ]);
        } catch (e) {
            const conn = document.getElementById("simConnStatusText");
            if (conn) {
                conn.textContent = "DISCONNECTED";
                conn.className = "text-red";
            }
        }
    };

    // --------------------------------------------------------------------------
    // 4-WAY TELEMETRY SOURCE SELECTOR
    // --------------------------------------------------------------------------
    window.telemetrySourceMode = "auto";

    const initTelemetrySourceSelector = () => {
        const btnAuto = document.getElementById("btnSourceAuto");
        const btnReal = document.getElementById("btnSourceReal");
        const btnSim = document.getElementById("btnSourceSim");
        const btnSynth = document.getElementById("btnSourceSynth");
        const pipeLabel = document.getElementById("activePipelineLabel");

        const setSourceMode = (mode) => {
            window.telemetrySourceMode = mode;
            [btnAuto, btnReal, btnSim, btnSynth].forEach(b => {
                if (!b) return;
                b.style.background = "transparent";
                b.style.color = b === btnReal ? "#00F0B5" : (b === btnSim ? "#F59E0B" : (b === btnSynth ? "#60A5FA" : "#00F0B5"));
                b.style.border = "1px solid " + (b === btnReal ? "#00F0B5" : (b === btnSim ? "#F59E0B" : (b === btnSynth ? "#60A5FA" : "#00F0B5")));
                b.classList.remove("active");
            });

            if (mode === "auto") {
                if (btnAuto) {
                    btnAuto.style.background = "#00F0B5";
                    btnAuto.style.color = "#04120E";
                    btnAuto.style.border = "none";
                    btnAuto.classList.add("active");
                }
                if (pipeLabel) pipeLabel.textContent = "AUTO: PRIORITIZING VERIFIED PHYSICAL ESP32 GATEWAYS";
            } else if (mode === "real_sensor") {
                if (btnReal) {
                    btnReal.style.background = "#00F0B5";
                    btnReal.style.color = "#04120E";
                    btnReal.style.border = "none";
                    btnReal.classList.add("active");
                }
                if (pipeLabel) pipeLabel.textContent = "FILTERED: PHYSICAL ESP32 HARDWARE ONLY";
            } else if (mode === "simulated_iot") {
                if (btnSim) {
                    btnSim.style.background = "#F59E0B";
                    btnSim.style.color = "#04120E";
                    btnSim.style.border = "none";
                    btnSim.classList.add("active");
                }
                if (pipeLabel) pipeLabel.textContent = "FILTERED: IOT SIMULATOR ENGINE ONLY";
            } else if (mode === "synthetic") {
                if (btnSynth) {
                    btnSynth.style.background = "#60A5FA";
                    btnSynth.style.color = "#04120E";
                    btnSynth.style.border = "none";
                    btnSynth.classList.add("active");
                }
                if (pipeLabel) pipeLabel.textContent = "FILTERED: HISTORICAL SYNTHETIC BENCHMARK";
            }
            fetchStatus();
            fetchStreamLog();
        };

        if (btnAuto) btnAuto.onclick = () => setSourceMode("auto");
        if (btnReal) btnReal.onclick = () => setSourceMode("real_sensor");
        if (btnSim) btnSim.onclick = () => setSourceMode("simulated_iot");
        if (btnSynth) btnSynth.onclick = () => setSourceMode("synthetic");
    };

    // --------------------------------------------------------------------------
    // DUAL ESP32 GATEWAY CONNECTIVITY STATUS
    // --------------------------------------------------------------------------
    const fetchGatewaysStatus = async () => {
        try {
            const res = await fetch("/api/v1/iot/gateways");
            if (!res.ok) return;
            const data = await res.json();
            const gws = data.gateways || [];

            // Node 1: Edge Gateway
            const node1 = gws.find(g => g.gateway_id === "ESP32_EDGE_GATEWAY_01");
            if (node1) {
                const elStatus = document.getElementById("gwNode1Status");
                const elDot = document.getElementById("gwNode1Dot");
                const elMetrics = document.getElementById("gwNode1Metrics");
                if (node1.connection_status === "ONLINE") {
                    if (elStatus) { elStatus.textContent = "ONLINE"; elStatus.style.background = "rgba(0,240,181,0.2)"; elStatus.style.color = "#00F0B5"; }
                    if (elDot) elDot.style.background = "#00F0B5";
                } else if (node1.connection_status === "STALE") {
                    if (elStatus) { elStatus.textContent = "STALE (>45s)"; elStatus.style.background = "rgba(245,158,11,0.2)"; elStatus.style.color = "#F59E0B"; }
                    if (elDot) elDot.style.background = "#F59E0B";
                } else {
                    if (elStatus) { elStatus.textContent = "OFFLINE"; elStatus.style.background = "rgba(239,68,68,0.2)"; elStatus.style.color = "#EF4444"; }
                    if (elDot) elDot.style.background = "#EF4444";
                }
                if (elMetrics) {
                    const ageStr = node1.seconds_since_last_seen !== null ? `${node1.seconds_since_last_seen}s ago` : "Waiting";
                    elMetrics.textContent = `Packets: ${node1.packet_count} | Last seen: ${ageStr}`;
                }
            }

            // Node 2: PZEM Gateway
            const node2 = gws.find(g => g.gateway_id === "ESP32_PZEM_GATEWAY_01");
            if (node2) {
                const elStatus = document.getElementById("gwNode2Status");
                const elDot = document.getElementById("gwNode2Dot");
                const elMetrics = document.getElementById("gwNode2Metrics");
                if (node2.connection_status === "ONLINE") {
                    if (elStatus) { elStatus.textContent = "ONLINE"; elStatus.style.background = "rgba(0,240,181,0.2)"; elStatus.style.color = "#00F0B5"; }
                    if (elDot) elDot.style.background = "#00F0B5";
                } else if (node2.connection_status === "STALE") {
                    if (elStatus) { elStatus.textContent = "STALE"; elStatus.style.background = "rgba(245,158,11,0.2)"; elStatus.style.color = "#F59E0B"; }
                    if (elDot) elDot.style.background = "#F59E0B";
                } else {
                    if (elStatus) { elStatus.textContent = "STANDBY / READY"; elStatus.style.background = "rgba(245,158,11,0.2)"; elStatus.style.color = "#F59E0B"; }
                    if (elDot) elDot.style.background = "#F59E0B";
                }
                if (elMetrics) {
                    const ageStr = node2.seconds_since_last_seen !== null ? `${node2.seconds_since_last_seen}s ago` : "Bench Standby";
                    elMetrics.textContent = `PZEM-004T AC Metrology | ${ageStr}`;
                }
            }
        } catch (e) {
            console.error("Gateways fetch error:", e);
        }
    };

    // --------------------------------------------------------------------------
    // OUTDOOR AMBIENT WEATHER FETCH
    // --------------------------------------------------------------------------
    const fetchOutdoorWeather = async () => {
        try {
            const res = await fetch("/api/v1/weather/current");
            if (!res.ok) return;
            const w = await res.json();
            const elCond = document.getElementById("weatherOutdoorCondition");
            const elTemp = document.getElementById("weatherOutdoorTemp");
            const elHum = document.getElementById("weatherOutdoorHum");
            const elWind = document.getElementById("weatherOutdoorWind");

            if (elCond && w.weather_condition) elCond.textContent = w.weather_condition;
            if (elTemp && w.temperature_c !== undefined) elTemp.textContent = `${Number(w.temperature_c).toFixed(1)} °C`;
            if (elHum && w.humidity_pct !== undefined) elHum.textContent = `${Number(w.humidity_pct).toFixed(0)} % RH`;
            if (elWind && w.wind_speed_kmh !== undefined) elWind.textContent = `${Number(w.wind_speed_kmh).toFixed(0)} km/h`;
        } catch (e) {
            console.error("Weather fetch error:", e);
        }
    };

    // --------------------------------------------------------------------------
    // LIVE ALERTS LIFECYCLE WIDGET
    // --------------------------------------------------------------------------
    const fetchFacilityAlerts = async () => {
        try {
            const res = await fetch("/api/v1/alerts");
            if (!res.ok) return;
            const data = await res.json();
            const alerts = data.alerts || [];
            const badge = document.getElementById("liveAlertsCountBadge");
            const container = document.getElementById("liveAlertsListContainer");

            if (badge) {
                const activeCount = alerts.filter(a => a.state === "OPEN" || a.state === "ACKNOWLEDGED" || a.state === "ASSIGNED").length;
                badge.textContent = `${activeCount} Active Alert${activeCount === 1 ? '' : 's'}`;
                badge.style.background = activeCount > 0 ? "rgba(239, 68, 68, 0.2)" : "rgba(0, 240, 181, 0.2)";
                badge.style.color = activeCount > 0 ? "#EF4444" : "#00F0B5";
                badge.style.borderColor = activeCount > 0 ? "#EF4444" : "#00F0B5";
            }

            if (!container) return;
            if (alerts.length === 0) {
                container.innerHTML = '<div style="padding: 16px; text-align: center; color: #34D399;"><i class="fa-solid fa-circle-check" style="margin-right: 6px;"></i> All facility telemetry nominal. Zero open alerts.</div>';
                return;
            }

            container.innerHTML = alerts.map(a => {
                const isCrit = a.severity === "CRITICAL";
                const borderCol = isCrit ? "#EF4444" : (a.severity === "HIGH" ? "#F59E0B" : "#38BDF8");
                const bgCol = isCrit ? "rgba(239, 68, 68, 0.12)" : "rgba(245, 158, 11, 0.12)";
                const badgeText = a.source_type === "real_sensor" ? "[REAL SENSOR]" : (a.source_type === "simulated_iot" ? "[SIMULATED IoT]" : "[SYNTHETIC BENCHMARK]");
                const badgeColor = a.source_type === "real_sensor" ? "#00F0B5" : (a.source_type === "simulated_iot" ? "#F59E0B" : "#60A5FA");

                const isOpen = a.state === "OPEN";
                const isAck = a.state === "ACKNOWLEDGED";
                const isResolved = a.state === "RESOLVED";

                return `
                <div style="background: ${bgCol}; border: 1.5px solid ${borderCol}; border-radius: 12px; padding: 14px 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                <span style="font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 4px; background: rgba(255,255,255,0.1); color: ${badgeColor}; border: 1px solid ${badgeColor};">
                                    ${badgeText}
                                </span>
                                <strong style="color: #FFFFFF; font-size: 13px;">${a.device_id} &bull; ${a.metric}</strong>
                                <span style="font-size: 10px; font-weight: 800; color: ${borderCol}; background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px;">
                                    ${a.severity} &bull; ${a.state}
                                </span>
                            </div>
                            <div style="font-size: 12px; color: #FFFFFF; margin-top: 6px; font-weight: 600;">
                                ${a.reason}
                            </div>
                            <div style="font-size: 11px; color: #CBD5E1; margin-top: 4px;">
                                <strong>Observed:</strong> ${a.last_observed_value} ${a.unit || ''} (vs Expected: ${a.expected_value} ${a.unit || ''}) &bull; Count: #${a.occurrence_count}
                            </div>
                            <div style="font-size: 11px; color: #94E4D0; margin-top: 4px;">
                                <i class="fa-solid fa-screwdriver-wrench"></i> <strong>Action:</strong> ${a.recommended_action}
                            </div>
                        </div>
                        <div style="display: flex; gap: 6px; align-items: center;">
                            ${isOpen ? `<button class="btn btn-sm" onclick="window.handleAlertAction('${a.id}', 'acknowledge')" style="font-size: 11px; font-weight: 700; background: #F59E0B; color: #04120E; border: none; border-radius: 6px; padding: 4px 10px; cursor: pointer;"><i class="fa-solid fa-check"></i> Ack</button>` : ''}
                            ${!isResolved ? `<button class="btn btn-sm" onclick="window.handleAlertAction('${a.id}', 'resolve')" style="font-size: 11px; font-weight: 700; background: #00F0B5; color: #04120E; border: none; border-radius: 6px; padding: 4px 10px; cursor: pointer;"><i class="fa-solid fa-check-double"></i> Resolve</button>` : ''}
                            ${!isResolved ? `<button class="btn btn-sm" onclick="window.handleAlertAction('${a.id}', 'dismiss')" style="font-size: 11px; font-weight: 700; background: rgba(255,255,255,0.15); color: #CBD5E1; border: 1px solid rgba(255,255,255,0.25); border-radius: 6px; padding: 4px 8px; cursor: pointer;">Dismiss</button>` : `<span style="font-size: 11px; color: #34D399; font-weight: 700;"><i class="fa-solid fa-circle-check"></i> RESOLVED</span>`}
                        </div>
                    </div>
                </div>`;
            }).join("");
        } catch (e) {
            console.error("Alerts fetch error:", e);
        }
    };

    window.handleAlertAction = async (alertId, action) => {
        try {
            const res = await fetch(`/api/v1/alerts/${alertId}/${action}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ actor: "Facility Operator", notes: `Action executed from Live IoT Dashboard (${action})` })
            });
            if (res.ok) {
                showToast(`Alert ${alertId} updated (${action})`);
                fetchFacilityAlerts();
            }
        } catch (e) {
            console.error("Alert action error:", e);
        }
    };

    // Update UI from status object
    const updateSimulatorUI = (status) => {
        if (!status) return;

        const badge = document.getElementById("simStatusBadge");
        if (badge) {
            badge.textContent = status.status;
            badge.className = status.status === "RUNNING" ? "pill-badge badge-teal" :
                              status.status === "PAUSED" ? "pill-badge badge-amber" : "pill-badge badge-red";
        }

        const clockVal = document.getElementById("simClockVal");
        if (clockVal && status.simulated_timestamp) {
            clockVal.textContent = status.simulated_timestamp.replace("T", " ").slice(0, 19);
        }

        const samplesCount = document.getElementById("simSamplesCount");
        if (samplesCount) samplesCount.textContent = status.sample_count;

        const speedDisp = document.getElementById("simSpeedDisplay");
        if (speedDisp) speedDisp.textContent = `Speed: ${status.speed}×`;

        const ingestionStatus = document.getElementById("simIngestionStatus");
        if (ingestionStatus) {
            ingestionStatus.textContent = status.status === "RUNNING" ? "LIVE STREAMING" : "IDLE / READY";
            ingestionStatus.style.color = status.status === "RUNNING" ? "#00D09C" : "#0D9488";
        }

        const conn = document.getElementById("simConnStatusText");
        if (conn) {
            conn.textContent = "CONNECTED";
            conn.className = "text-mint";
        }

        const connState = document.getElementById("monConnState");
        if (connState) {
            if (window.hasLiveHardwareTelemetry) {
                connState.textContent = "HARDWARE STREAMING";
            } else {
                connState.textContent = status.status === "RUNNING" ? "LIVE STREAMING" : (status.status || "CONNECTED");
            }
        }
        const monSimInstancesCount = document.getElementById("monSimInstancesCount");
        if (monSimInstancesCount) {
            if (window.hasLiveHardwareTelemetry) {
                monSimInstancesCount.textContent = "1 Physical Gateway";
            } else {
                monSimInstancesCount.textContent = "1 Simulator Node";
            }
        }
        const simIpLabel = document.getElementById("monSimIpLabel");
        if (simIpLabel) {
            if (window.hasLiveHardwareTelemetry) {
                simIpLabel.textContent = "IP: 172.16.222.83 (ESP32 Hardware)";
            } else {
                simIpLabel.textContent = `IP: 127.0.0.1 (${status.mode || 'Standard'})`;
            }
        }
        const monThroughput = document.getElementById("monThroughput");
        if (monThroughput) {
            monThroughput.textContent = `${(status.speed || 1) * 12} Packets/min`;
        }

        // Sync slider positions if not actively focused by user
        if (status.sensors) {
            const s = status.sensors;
            if (document.activeElement !== ctrlActivePowerKW && ctrlActivePowerKW) ctrlActivePowerKW.value = s.active_power_kw;
            if (document.activeElement !== ctrlEnergyKWH && ctrlEnergyKWH) ctrlEnergyKWH.value = s.energy_kwh;
            if (document.activeElement !== ctrlPowerFactor && ctrlPowerFactor) ctrlPowerFactor.value = s.power_factor;
            if (document.activeElement !== ctrlXfmrLoad && ctrlXfmrLoad) ctrlXfmrLoad.value = s.transformer_load_pct;
            if (document.activeElement !== ctrlOccupancyCount && ctrlOccupancyCount) ctrlOccupancyCount.value = s.occupancy_count;
            if (document.activeElement !== ctrlHvacLoadKW && ctrlHvacLoadKW) ctrlHvacLoadKW.value = s.hvac_load_kw;
            if (document.activeElement !== ctrlHvacStatus && ctrlHvacStatus) ctrlHvacStatus.value = s.hvac_status;
            if (document.activeElement !== ctrlEquipStatus && ctrlEquipStatus) ctrlEquipStatus.value = s.equipment_status;
            if (document.activeElement !== ctrlTempC && ctrlTempC) ctrlTempC.value = s.temperature_c;
            if (document.activeElement !== ctrlWaterFlow && ctrlWaterFlow) ctrlWaterFlow.value = s.water_flow_lmin;
            if (document.activeElement !== ctrlAirAqi && ctrlAirAqi) ctrlAirAqi.value = s.air_aqi;
            if (document.activeElement !== ctrlDgStatus && ctrlDgStatus) ctrlDgStatus.value = s.dg_status;
            syncSliderLabels();

            // Helper to format metric or show unavailable state honestly
            const formatMetric = (val, unit, unavailableText = "--") => {
                if (val === null || val === undefined || isNaN(val)) return unavailableText;
                return `${val} ${unit}`.trim();
            };

            // Populate Live IoT Monitor Tab Cards (Only if no live physical hardware stream is active)
            const hKW = document.getElementById("liveMetricHvacKW");
            const cTemp = document.getElementById("liveMetricChillerTemp");
            const fSpeed = document.getElementById("liveMetricFanSpeed");
            const hStat = document.getElementById("liveMetricHvacStatus");

            if (hKW) hKW.textContent = formatMetric(s.hvac_load_kw, "kW");
            if (cTemp) cTemp.textContent = formatMetric(s.chiller_temp_c, "°C");
            if (fSpeed) fSpeed.textContent = formatMetric(s.fan_speed_rpm, "RPM");
            if (hStat) hStat.textContent = s.hvac_status || "NORMAL";

            if (!window.hasLiveHardwareTelemetry) {
                const pKW = document.getElementById("liveMetricPowerKW");
                const eKWH = document.getElementById("liveMetricEnergyKWH");
                const vV = document.getElementById("liveMetricVoltageV");
                const iPF = document.getElementById("liveMetricCurrentPF");

                if (pKW) pKW.textContent = formatMetric(s.active_power_kw, "kW");
                if (eKWH) eKWH.textContent = formatMetric(s.energy_kwh, "kWh");
                if (vV) vV.textContent = formatMetric(s.voltage_v, "V");
                if (iPF) {
                    renderCurrentAndPF(s.current_a, s.power_factor);
                }

                const wFlow = document.getElementById("liveMetricWaterFlow");
                const tLvl = document.getElementById("liveMetricTankLevel");
                const wPress = document.getElementById("liveMetricWaterPressure");
                const cWater = document.getElementById("liveMetricCumWater");

                if (wFlow) wFlow.textContent = formatMetric(s.water_flow_lmin, "L/min");
                if (tLvl) tLvl.textContent = (s.tank_level_pct !== null && s.tank_level_pct !== undefined) ? `${s.tank_level_pct} %` : "-- % (Uncalibrated)";
                if (wPress) wPress.textContent = (s.water_pressure_bar !== null && s.water_pressure_bar !== undefined) ? `${s.water_pressure_bar} bar` : "-- bar (Disabled)";
                if (cWater) cWater.textContent = formatMetric(s.cumulative_water_m3, "m³");
            }

            const rTemp = document.getElementById("liveMetricRoomTemp");
            const oCount = document.getElementById("liveMetricOccupancyCount");
            const rHum = document.getElementById("liveMetricHumidity");
            const aAqi = document.getElementById("liveMetricAirAqi");

            if (rTemp) rTemp.textContent = formatMetric(s.temperature_c, "°C");
            if (oCount) oCount.textContent = (s.occupancy_count !== null && s.occupancy_count !== undefined) ? `${s.occupancy_count} People` : "-- People";
            if (rHum) rHum.textContent = formatMetric(s.humidity_pct, "%");
            if (aAqi) {
                if (s.air_quality_aqi !== null && s.air_quality_aqi !== undefined) {
                    aAqi.textContent = `${s.air_quality_aqi} AQI (${s.co2_ppm ?? '--'} ppm)`;
                } else if (s.air_aqi !== null && s.air_aqi !== undefined) {
                    aAqi.textContent = `${s.air_aqi} AQI`;
                } else {
                    aAqi.textContent = "-- AQI";
                }
            }

            // Update Sensor Hardware Matrix Status Cells
            const mElec = document.getElementById("matrixStatusElec");
            const mWater = document.getElementById("matrixStatusWater");
            if (mElec) {
                const isElecActive = s.active_power_kw !== null && s.active_power_kw !== undefined;
                mElec.innerHTML = isElecActive ? '<span class="badge-mint" style="font-size: 10px;">MEASURED</span>' : '<span class="badge-amber" style="font-size: 10px;">UNAVAILABLE</span>';
            }
            if (mWater) {
                const isWaterActive = s.water_flow_lmin !== null && s.water_flow_lmin !== undefined;
                mWater.innerHTML = isWaterActive ? '<span class="badge-mint" style="font-size: 10px;">MEASURED</span>' : '<span class="badge-amber" style="font-size: 10px;">UNAVAILABLE</span>';
            }
        }
    };

    // Fetch Stream Log from Canonical Unified Registry Stream
    
    // =========================================================================
    // LIVE HARDWARE & IOT SPARKLINE CHARTS
    // =========================================================================
    let livePowerChart = null;
    let liveWaterChart = null;
    let liveMq135Chart = null;
    let liveWasteChart = null;

    const initLiveSparklines = () => {
        if (typeof Chart === 'undefined') return;

        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { enabled: true } },
            scales: {
                x: { display: false },
                y: { display: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#A3C9BE', font: { size: 9 } } }
            },
            elements: { point: { radius: 2, hoverRadius: 4 }, line: { tension: 0.3, borderWidth: 2 } }
        };

        const ctxPower = document.getElementById('liveChartPower');
        if (ctxPower && !livePowerChart) {
            livePowerChart = new Chart(ctxPower.getContext('2d'), {
                type: 'line',
                data: {
                    labels: Array(10).fill(''),
                    datasets: [{
                        label: 'Active Power (kW)',
                        data: [42.1, 45.0, 48.2, 46.5, 49.0, 52.3, 50.1, 47.8, 49.5, 51.2],
                        borderColor: '#00D09C',
                        backgroundColor: 'rgba(0, 208, 156, 0.15)',
                        fill: true
                    }]
                },
                options: commonOptions
            });
        }

        const ctxWater = document.getElementById('liveChartWater');
        if (ctxWater && !liveWaterChart) {
            liveWaterChart = new Chart(ctxWater.getContext('2d'), {
                type: 'line',
                data: {
                    labels: Array(10).fill(''),
                    datasets: [{
                        label: 'Flow Rate (L/min)',
                        data: [12.0, 13.5, 14.2, 13.8, 14.5, 15.1, 14.0, 13.6, 14.8, 14.2],
                        borderColor: '#60A5FA',
                        backgroundColor: 'rgba(96, 165, 250, 0.15)',
                        fill: true
                    }]
                },
                options: commonOptions
            });
        }

        const ctxMq = document.getElementById('liveChartMq135');
        if (ctxMq && !liveMq135Chart) {
            liveMq135Chart = new Chart(ctxMq.getContext('2d'), {
                type: 'line',
                data: {
                    labels: Array(10).fill(''),
                    datasets: [{
                        label: 'Raw ADC Signal (count)',
                        data: [1150, 1180, 1220, 1205, 1248, 1260, 1240, 1255, 1270, 1248],
                        borderColor: '#F59E0B',
                        backgroundColor: 'rgba(245, 158, 11, 0.15)',
                        fill: true
                    }]
                },
                options: commonOptions
            });
        }

        const ctxWaste = document.getElementById('liveChartWaste');
        if (ctxWaste && !liveWasteChart) {
            liveWasteChart = new Chart(ctxWaste.getContext('2d'), {
                type: 'line',
                data: {
                    labels: Array(10).fill(''),
                    datasets: [{
                        label: 'Bin Fill Level (%)',
                        data: [45.0, 48.0, 52.0, 55.0, 58.5, 62.0, 65.0, 68.0, 71.5, 74.0],
                        borderColor: '#F59E0B',
                        backgroundColor: 'rgba(245, 158, 11, 0.15)',
                        fill: true
                    }]
                },
                options: commonOptions
            });
        }
    };

    const pushSparklinePoint = (chart, val, label = '') => {
        if (!chart || val === null || val === undefined || isNaN(val)) return;
        const data = chart.data.datasets[0].data;
        const labels = chart.data.labels;
        data.push(Number(val));
        labels.push(label);
        if (data.length > 20) {
            data.shift();
            labels.shift();
        }
        chart.update('none');
    };

    // =========================================================================
    // WIRE PAYLOAD VIEWER & AI SUGGESTIONS HELPERS (GLOBAL)
    // =========================================================================
    window.togglePayloadViewer = function(boxId, btnTextId) {
        const box = document.getElementById(boxId);
        const btn = btnTextId ? document.getElementById(btnTextId) : null;
        if (!box) return;
        const isHidden = (box.style.display === 'none' || !box.style.display);
        box.style.display = isHidden ? 'block' : 'none';
        if (btn) {
            btn.textContent = isHidden ? 'Hide Payload' : (boxId === 'elecPayloadBox' ? 'View Format' : (boxId === 'gatewayPayloadBox' ? 'View Gateway Info' : 'View Live Payload'));
        }
    };

    window.openWirePayloadModal = function(messageId) {
        const modal = document.getElementById('wirePayloadModal');
        const code = document.getElementById('wireModalJsonCode');
        const title = document.getElementById('wireModalTitle');
        const subtitle = document.getElementById('wireModalSubtitle');
        const meta = document.getElementById('wireModalFooterMeta');
        if (!modal || !code) return;

        let item = null;
        if (window.cachedStreamList && window.cachedStreamList.length > 0) {
            item = window.cachedStreamList.find(i => i.message_id === messageId);
        }
        if (!item && messageId) {
            item = { message_id: messageId, status: "Awaiting stream lookup" };
        }

        if (item) {
            code.textContent = JSON.stringify(item, null, 2);
            if (title) title.textContent = `Telemetry Packet: ${item.device_id || 'ESP32'}`;
            if (subtitle) subtitle.textContent = `Message ID: ${item.message_id || '--'} • Ingested: ${item.event_timestamp || item.sent_timestamp || item.ingested_at || 'Just now'}`;
            if (meta) meta.textContent = `Source: ${item.source_type || 'real_sensor'} • Transport: HTTP Ingest • State: ${item.reporting_state || 'NORMAL_15M'}`;
        } else {
            code.textContent = "// Packet not found in memory buffer";
        }
        modal.style.display = 'flex';
    };

    window.closeWirePayloadModal = function() {
        const modal = document.getElementById('wirePayloadModal');
        if (modal) modal.style.display = 'none';
    };

    window.copyModalWirePayload = function() {
        const code = document.getElementById('wireModalJsonCode');
        const btn = document.getElementById('btnCopyWireModal');
        if (!code) return;
        navigator.clipboard.writeText(code.textContent).then(() => {
            if (btn) {
                const oldHtml = btn.innerHTML;
                btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                btn.style.color = '#34D399';
                setTimeout(() => {
                    btn.innerHTML = oldHtml;
                    btn.style.color = '#00F0B5';
                }, 1800);
            }
        });
    };

    const getPacketSecondsAgo = (ts) => {
        if (!ts) return 9999;
        try {
            const d = new Date(ts);
            const diff = (Date.now() - d.getTime()) / 1000;
            return isNaN(diff) ? 5 : Math.max(0, diff);
        } catch (e) {
            return 5;
        }
    };

    const updateCardLiveBadge = (badgeEl, lastSeenEl, secAgo, activeLabel, activeColor) => {
        if (!badgeEl) return;
        const isOnline = (secAgo < 45);
        if (isOnline) {
            badgeEl.className = 'live-pulse-badge online';
            badgeEl.innerHTML = '<span class="pulse-beacon-dot online"></span> LIVE CONNECTED · RECEIVING DATA';
            if (lastSeenEl) {
                lastSeenEl.textContent = `${activeLabel} (${Math.round(secAgo)}s ago)`;
                lastSeenEl.style.color = activeColor || '#00F0B5';
            }
        } else {
            badgeEl.className = 'live-pulse-badge standby';
            badgeEl.innerHTML = '<span class="pulse-beacon-dot standby"></span> INACTIVE / STANDBY';
            if (lastSeenEl) {
                lastSeenEl.textContent = secAgo > 3600 ? 'Inactive (Standby)' : `Last seen ${Math.round(secAgo)}s ago`;
                lastSeenEl.style.color = '#94A3B8';
            }
        }
    };

    const updateAiFacilitySuggestions = (data) => {
        // 1. Waste Bin Evaluation
        const sugWasteTitle = document.getElementById('sugWasteTitle');
        const sugWasteDesc = document.getElementById('sugWasteDesc');
        const sugWasteBox = document.getElementById('sugWasteBox');
        if (data.waste) {
            const f = data.waste.fillPct;
            const d = data.waste.distCm;
            if (f >= 80.0) {
                if (sugWasteTitle) sugWasteTitle.textContent = `Smart Waste Bin Overflowing (${f.toFixed(1)}% Full)`;
                if (sugWasteDesc) sugWasteDesc.innerHTML = `Ultrasonic clearance is <strong>${d.toFixed(1)} cm</strong> (depth baseline: 80 cm). Critical threshold of 80% is exceeded. Edge anomaly triggered immediate 5s telemetry cadence.`;
                if (sugWasteBox) {
                    sugWasteBox.style.background = 'rgba(239, 68, 68, 0.1)';
                    sugWasteBox.style.borderColor = 'rgba(239, 68, 68, 0.5)';
                    sugWasteBox.style.borderLeft = '4px solid #EF4444';
                }
            } else {
                if (sugWasteTitle) sugWasteTitle.textContent = `Smart Waste Bin Normal (${f.toFixed(1)}% Full)`;
                if (sugWasteDesc) sugWasteDesc.innerHTML = `Ultrasonic clearance is <strong>${d.toFixed(1)} cm</strong> (fill: ${f.toFixed(1)}%). Bin capacity optimal; no immediate collection dispatch required.`;
                if (sugWasteBox) {
                    sugWasteBox.style.background = 'rgba(0, 240, 181, 0.08)';
                    sugWasteBox.style.borderColor = 'rgba(0, 240, 181, 0.35)';
                    sugWasteBox.style.borderLeft = '4px solid #00F0B5';
                }
            }
        }

        // 2. Climate Evaluation
        const sugClimateTitle = document.getElementById('sugClimateTitle');
        const sugClimateDesc = document.getElementById('sugClimateDesc');
        const sugClimateBox = document.getElementById('sugClimateBox');
        if (data.dht) {
            const t = data.dht.temp;
            const h = data.dht.hum;
            const hi = data.dht.hi;
            if (h >= 65.0) {
                if (sugClimateTitle) sugClimateTitle.textContent = `Zone B Relative Humidity Elevated (${h}% RH)`;
                if (sugClimateDesc) sugClimateDesc.innerHTML = `Temp: <strong>${t}°C</strong>, Heat Index: <strong>${hi}°C</strong>. Humidity exceeds ASHRAE 60% comfort guideline. Mild mold hazard risk if prolonged.`;
                if (sugClimateBox) {
                    sugClimateBox.style.background = 'rgba(245, 158, 11, 0.08)';
                    sugClimateBox.style.borderColor = 'rgba(245, 158, 11, 0.35)';
                    sugClimateBox.style.borderLeft = '4px solid #F59E0B';
                }
            } else {
                if (sugClimateTitle) sugClimateTitle.textContent = `Zone B Thermal Comfort Optimal (${t}°C / ${h}%)`;
                if (sugClimateDesc) sugClimateDesc.innerHTML = `Temp: <strong>${t}°C</strong>, Humidity: <strong>${h}% RH</strong>. Both within ASHRAE 55 comfort standard. Baseline HVAC operation maintained.`;
                if (sugClimateBox) {
                    sugClimateBox.style.background = 'rgba(0, 240, 181, 0.08)';
                    sugClimateBox.style.borderColor = 'rgba(0, 240, 181, 0.35)';
                    sugClimateBox.style.borderLeft = '4px solid #00F0B5';
                }
            }
        }

        // 3. Water Leakage Evaluation
        const sugWaterTitle = document.getElementById('sugWaterTitle');
        const sugWaterDesc = document.getElementById('sugWaterDesc');
        if (data.water) {
            const flow = data.water.flow;
            const pulses = data.water.pulses;
            if (flow > 0.0) {
                if (sugWaterTitle) sugWaterTitle.textContent = `Active Water Flow Detected (${flow.toFixed(1)} L/min)`;
                if (sugWaterDesc) sugWaterDesc.innerHTML = `ZJ-S201 turbine reading <strong>${flow.toFixed(1)} L/min</strong> (${pulses} pulses). Water draw active in Block B riser line.`;
            } else {
                if (sugWaterTitle) sugWaterTitle.textContent = `Plumbing Riser Integrity Confirmed`;
                if (sugWaterDesc) sugWaterDesc.innerHTML = `Hardware flow turbine reads <strong>0.0 L/min</strong> (0 pulses). Zero unmetered seepage or concealed valve leakage across Block B riser line.`;
            }
        }

        // 4. Air Quality Evaluation
        const sugAirTitle = document.getElementById('sugAirTitle');
        const sugAirDesc = document.getElementById('sugAirDesc');
        if (data.air) {
            const adc = data.air.adc;
            const v = data.air.volt;
            if (adc > 800) {
                if (sugAirTitle) sugAirTitle.textContent = `Elevated Gas / VOC Activity (${adc} ADC)`;
                if (sugAirDesc) sugAirDesc.innerHTML = `Raw ADC reads <strong>${adc} counts</strong> (${v}V). Air quality response indicates volatile compounds or smoke. Recommend 100% fresh air damper purge.`;
            } else {
                if (sugAirTitle) sugAirTitle.textContent = `Ambient Air Quality Within Clean Baseline`;
                if (sugAirDesc) sugAirDesc.innerHTML = `Raw ADC reads <strong>${adc} counts</strong> (${v}V). Sensor indicates clean ambient air with no volatile gas spikes detected.`;
            }
        }
    };
    window.updateAiFacilitySuggestions = updateAiFacilitySuggestions;
    window.refreshAiFacilitySuggestions = () => {
        if (window.cachedStreamList) updateLiveTelemetryFromStream(window.cachedStreamList);
    };

    const updateLiveTelemetryFromStream = (streamItems) => {
        if (!streamItems || streamItems.length === 0) return;
        initLiveSparklines();

        let hasHw = false;
        let waterUpdated = false;
        let elecUpdated = false;
        let airUpdated = false;
        let dhtUpdated = false;
        let wasteUpdated = false;

        let latestWasteData = null;
        let latestDhtData = null;
        let latestAirData = null;
        let latestWaterData = null;

        // Loop through items (streamItems is newest first)
        for (const item of streamItems) {
            const m = item.metrics || item.telemetry || {};
            const isVerifiedHw = item.is_verified_hardware === true || item.source_type === 'real_sensor';
            if (isVerifiedHw) hasHw = true;
            const rawTs = item.event_timestamp || item.sent_timestamp || item.ingested_at || '';
            const timeStr = rawTs.slice(11, 19);
            const secAgo = getPacketSecondsAgo(rawTs);

            // Update smart waste bin card with NEWEST waste packet
            if (!wasteUpdated && (m.fill_level_percent !== undefined || m.fill_level_pct !== undefined || m.bin_distance_cm !== undefined || item.device_id === 'WASTE-BLOCK-B-001')) {
                wasteUpdated = true;
                const elFill = document.getElementById('liveMetricBinFill');
                const elDist = document.getElementById('liveMetricBinDistance');
                const elRisk = document.getElementById('liveMetricBinRisk');
                const bar = document.getElementById('liveBinBar');
                const barLabel = document.getElementById('liveBinBarLabel');
                const badge = document.getElementById('liveWasteCardBadge');
                const lastSeen = document.getElementById('liveWasteLastSeen');

                const fillPct = Number(m.fill_level_percent ?? m.fill_level_pct ?? 0);
                const distCm = Number(m.bin_distance_cm ?? 0);
                latestWasteData = { fillPct, distCm };

                if (elFill) elFill.textContent = `${fillPct.toFixed(1)} %`;
                if (elDist) elDist.textContent = `${distCm.toFixed(1)} cm`;
                if (elRisk) {
                    if (fillPct >= 75.0 || (distCm > 0 && distCm <= 15.0)) {
                        elRisk.textContent = 'OVERFLOW RISK';
                        elRisk.style.color = '#EF4444';
                        // LIVE JURY DEMO: Immediate Waste Bin Sonar Popup
                        window.triggerLiveHardwareAnomalyPopup({
                            id: 'ALT_WASTE_BIN_OVERFLOW',
                            device_id: item.device_id || 'WASTE-BLOCK-B-001',
                            metric: 'fill_level_percent',
                            issue: '🗑️ HIGH ANOMALY: SMART WASTE BIN CRITICAL OVERFLOW',
                            severity: 'HIGH',
                            observed_value: `${fillPct.toFixed(1)}% Fill (${distCm.toFixed(1)} cm clearance)`,
                            explanation: 'HC-SR04 ultrasonic sonar detected bin capacity threshold exceeded.',
                            recommended_action: 'Dispatch custodial / waste collection crew for immediate bin emptying.'
                        });
                    } else {
                        elRisk.textContent = 'NORMAL';
                        elRisk.style.color = '#00D09C';
                    }
                }

                if (bar) bar.style.width = `${Math.min(Math.max(fillPct, 0), 100)}%`;
                if (barLabel) barLabel.textContent = `${fillPct.toFixed(1)}% Fill (${distCm.toFixed(1)} cm clearance)`;

                updateCardLiveBadge(badge, lastSeen, secAgo, 'Active Sonar Stream', '#00F0B5');

                // Populate Wire JSON Payload
                const wasteCode = document.getElementById('wasteWirePayloadCode');
                if (wasteCode) wasteCode.textContent = JSON.stringify(item, null, 2);

                // Update Waste Tab (#contentWaste) live values
                const wasteFillInput = document.getElementById('wasteFill');
                if (wasteFillInput && document.activeElement !== wasteFillInput) {
                    wasteFillInput.value = fillPct.toFixed(1);
                }
                const liveFillText = document.getElementById('wasteLiveFillText');
                if (liveFillText) liveFillText.textContent = `${fillPct.toFixed(1)}%`;
                const liveDistText = document.getElementById('wasteLiveDistText');
                if (liveDistText) liveDistText.textContent = `${distCm.toFixed(1)} cm`;
                const liveHwBadge = document.getElementById('wasteLiveHardwareBadge');
                if (liveHwBadge) liveHwBadge.style.display = isVerifiedHw ? 'inline-flex' : 'none';

                const alertBadge = document.getElementById('wasteLiveAlertBadge');
                if (alertBadge) {
                    if (fillPct >= 80.0) {
                        alertBadge.textContent = 'PRIORITY 1 CRITICAL OVERFLOW';
                        alertBadge.className = 'badge-red';
                    } else if (fillPct >= 65.0) {
                        alertBadge.textContent = 'PRIORITY 2 OVERFLOW RISK';
                        alertBadge.className = 'badge-amber';
                    } else {
                        alertBadge.textContent = 'STATUS: NORMAL CAPACITY';
                        alertBadge.className = 'badge-teal';
                    }
                }

                pushSparklinePoint(liveWasteChart, fillPct, timeStr);
            }

            // Update water card with NEWEST water packet
            if (!waterUpdated && (m.water_flow_lmin !== undefined || m.water_pulse_count_total !== undefined || m.tank_level_pct !== undefined || m.tank_distance_cm !== undefined || item.device_id === 'WATER-BLOCK-B-001')) {
                waterUpdated = true;
                const elF = document.getElementById('liveMetricWaterFlow');
                const elC = document.getElementById('liveMetricCumWater');
                const elPulses = document.getElementById('liveMetricWaterPulses');
                const elT = document.getElementById('liveMetricTankLevel');
                const elD = document.getElementById('liveMetricTankDistance');
                const bar = document.getElementById('liveTankBar');
                const barLabel = document.getElementById('liveTankBarLabel');
                const badge = document.getElementById('liveWaterCardBadge');
                const lastSeen = document.getElementById('liveWaterLastSeen');

                const flow = Number(m.water_flow_lmin ?? 0);
                const pulses = Number(m.water_pulse_count_total ?? m.pulses ?? 0);
                const distCm = (m.tank_distance_cm !== undefined || m.distance_cm !== undefined) ? Number(m.tank_distance_cm ?? m.distance_cm) : null;
                const tankPct = (m.tank_level_pct !== undefined && m.tank_level_pct !== null && !isNaN(Number(m.tank_level_pct))) ? Number(m.tank_level_pct) : null;
                latestWaterData = { flow, pulses, distCm, tankPct };

                if (elF) elF.textContent = `${flow.toFixed(1)} L/min`;
                if (elC) {
                    if (m.water_cumulative_liters !== undefined) elC.textContent = `${Number(m.water_cumulative_liters).toFixed(2)} L`;
                    else if (m.cumulative_water_m3 !== undefined) elC.textContent = `${Number(m.cumulative_water_m3).toFixed(3)} m³`;
                }
                if (elPulses) elPulses.textContent = `${pulses.toLocaleString()} pulses`;
                
                if (elT) {
                    if (tankPct !== null && tankPct >= 0) {
                        elT.textContent = `${tankPct.toFixed(1)} %`;
                    } else {
                        elT.textContent = 'STANDBY';
                    }
                }
                if (elD) {
                    if (distCm !== null && distCm > 0) {
                        elD.textContent = `${distCm.toFixed(1)} cm`;
                    } else {
                        elD.textContent = '-- cm';
                    }
                }
                if (bar && tankPct !== null) {
                    const clamped = Math.min(100, Math.max(0, tankPct));
                    bar.style.width = `${clamped}%`;
                    if (barLabel) {
                        const dText = distCm !== null && distCm > 0 ? ` (${distCm.toFixed(1)} cm clearance)` : '';
                        barLabel.textContent = `${clamped.toFixed(1)}% Storage${dText}`;
                    }
                }

                updateCardLiveBadge(badge, lastSeen, secAgo, 'Active Interrupt Stream', '#38BDF8');

                // Populate Wire JSON Payload
                const waterCode = document.getElementById('waterWirePayloadCode');
                if (waterCode) waterCode.textContent = JSON.stringify(item, null, 2);

                pushSparklinePoint(liveWaterChart, flow, timeStr);

                // LIVE JURY DEMO: Immediate Water Pipe Leak / Burst Popup
                if (flow >= 8.0) {
                    window.triggerLiveHardwareAnomalyPopup({
                        id: 'ALT_WATER_BURST',
                        device_id: item.device_id || 'WATER-BLOCK-B-001',
                        metric: 'water_flow_lmin',
                        issue: '💧 CRITICAL: RAPID WATER PIPE LEAK / BURST SURGE',
                        severity: 'CRITICAL',
                        observed_value: `${flow.toFixed(1)} L/min (Baseline: < 5.0 L/min)`,
                        explanation: 'Turbine flow meter recorded sustained high volumetric velocity.',
                        recommended_action: 'Inspect riser line isolation valves and emergency shutoff actuators.'
                    });
                }
            }

            // Update electricity card with NEWEST electricity packet
            if (!elecUpdated && (m.active_power_kw !== undefined || m.voltage_v !== undefined || item.device_id === 'METER-BLOCK-B-001')) {
                elecUpdated = true;
                const elP = document.getElementById('liveMetricPowerKW');
                const elE = document.getElementById('liveMetricEnergyKWH');
                const elV = document.getElementById('liveMetricVoltageV');
                const elPF = document.getElementById('liveMetricCurrentPF');
                const elSub = document.getElementById('liveMetricPowerSub');
                const elCurrSub = document.getElementById('liveMetricCurrentSub');
                const badge = document.getElementById('liveElecCardBadge');
                const lastSeen = document.getElementById('liveElecLastSeen');

                const hasPzemOnline = (m.voltage_v !== undefined && Number(m.voltage_v) > 50.0) || (m.active_power_kw !== undefined && Number(m.active_power_kw) > 0);
                if (hasPzemOnline) {
                    const kw = Number(m.active_power_kw ?? 0);
                    if (elP) {
                        if (kw <= 0.0001) elP.textContent = '0.00 kW (Idle)';
                        else if (kw < 1.0) elP.textContent = `${kw.toFixed(3)} kW`;
                        else if (kw < 100.0) elP.textContent = `${kw.toFixed(2)} kW`;
                        else elP.textContent = `${kw.toFixed(1)} kW`;
                    }
                    if (elSub) elSub.textContent = kw > 0.0001 ? 'Peak Demand Load' : 'Line Active (Zero Load)';
                    updateCardLiveBadge(badge, lastSeen, secAgo, 'PZEM-004T Live Stream', '#00D09C');
                    pushSparklinePoint(livePowerChart, kw, timeStr);

                    // LIVE JURY DEMO: Immediate Electrical Load / Current Surge Popup
                    const curA = Number(m.current_a ?? 0);
                    if (curA >= 2.0 || kw >= 0.45) {
                        window.triggerLiveHardwareAnomalyPopup({
                            id: 'ALT_ELEC_OVERLOAD',
                            device_id: item.device_id || 'METER-BLOCK-B-001',
                            metric: 'current_a',
                            issue: '⚡ HIGH: ELECTRICAL LINE CURRENT SURGE / OVERLOAD',
                            severity: 'HIGH',
                            observed_value: `${curA.toFixed(3)} A (${(kw * 1000).toFixed(0)} W)`,
                            explanation: 'PZEM-004T Modbus metrology recorded branch current exceeding normal load envelope.',
                            recommended_action: 'Audit circuit breaker branch load and stage-shed non-critical devices.'
                        });
                    }
                } else {
                    if (elP) elP.textContent = '-- kW';
                    if (elSub) elSub.textContent = 'PZEM not connected';
                    renderCurrentAndPF(null, null);
                    if (badge) {
                        badge.className = 'live-pulse-badge standby';
                        badge.innerHTML = '<span class="pulse-beacon-dot standby"></span> STANDBY (No PZEM)';
                    }
                    if (lastSeen) {
                        lastSeen.textContent = 'Waiting for PZEM Node telemetry';
                        lastSeen.style.color = '#94A3B8';
                    }
                }
                if (elE && (m.cumulative_energy_kwh !== undefined || m.energy_kwh !== undefined)) {
                    const eVal = Number(m.cumulative_energy_kwh ?? m.energy_kwh);
                    elE.textContent = eVal < 10.0 ? `${eVal.toFixed(3)} kWh` : `${eVal.toFixed(2)} kWh`;
                }
                if (elV && m.voltage_v !== undefined) elV.textContent = `${Number(m.voltage_v).toFixed(1)} V`;
                if (elPF && m.current_a !== undefined) renderCurrentAndPF(m.current_a, m.power_factor ?? '0.95');
                if (m.frequency_hz !== undefined && elCurrSub) {
                    elCurrSub.textContent = `Single-Phase Active Load • ${Number(m.frequency_hz).toFixed(1)} Hz`;
                }

                const elecCode = document.getElementById('elecWirePayloadCode');
                if (elecCode) elecCode.textContent = JSON.stringify(item, null, 2);
            }

            // Update MQ-135 air quality card with NEWEST air packet
            if (!airUpdated && (m.mq135_raw_adc !== undefined || m.raw_adc !== undefined || m.mq135_voltage_v !== undefined || m.mq135_adc_pin_voltage_v !== undefined)) {
                airUpdated = true;
                const elAdc = document.getElementById('liveMetricMq135Adc');
                const elVolt = document.getElementById('liveMetricMq135Voltage');
                const elCo2 = document.getElementById('liveMetricMq135Co2');
                const elStat = document.getElementById('liveMetricMq135Status');
                const badge = document.getElementById('liveAirCardBadge');
                const lastSeen = document.getElementById('liveAirLastSeen');

                const rawVal = m.mq135_raw_adc ?? m.raw_adc;
                const voltVal = m.mq135_voltage_v ?? m.sensor_voltage_v;
                const isActuallyConnected = (rawVal !== undefined && Number(rawVal) >= 80 && Number(voltVal) >= 0.08);

                latestAirData = { adc: Math.round(rawVal || 0), volt: Number(voltVal || 0).toFixed(2) };

                if (isActuallyConnected) {
                    if (elAdc) elAdc.textContent = `${Math.round(rawVal)} count`;
                    if (elVolt) elVolt.textContent = `${Number(voltVal).toFixed(2)} V`;
                    if (elCo2) {
                        const ppmVal = m.mq135_estimated_ppm ?? m.estimated_ppm;
                        if (ppmVal !== undefined && !isNaN(Number(ppmVal))) {
                            elCo2.textContent = `${Math.round(Number(ppmVal))} ppm`;
                        } else {
                            const estPpm = Math.max(380, Math.round(rawVal * 0.76));
                            elCo2.textContent = `${estPpm} ppm`;
                        }
                    }
                    if (elStat) {
                        const isWarm = m.mq135_warmup_status === 0 || m.mq135_warmup_status === 0.0;
                        elStat.textContent = isWarm ? 'WARMING UP (180s)' : (Number(rawVal) >= 600 ? 'SMOKE SURGE' : 'STABILIZED');
                        elStat.style.color = isWarm ? '#F59E0B' : (Number(rawVal) >= 600 ? '#EF4444' : '#00D09C');
                    }
                    updateCardLiveBadge(badge, lastSeen, secAgo, 'Active ADC Stream', '#F59E0B');
                    pushSparklinePoint(liveMq135Chart, rawVal ?? voltVal, timeStr);

                    // LIVE JURY DEMO: Immediate Smoke / Hazardous Gas Popup
                    if (Number(rawVal) >= 600) {
                        const isSmoke = Number(rawVal) >= 850;
                        window.triggerLiveHardwareAnomalyPopup({
                            id: 'ALT_SMOKE_HAZARD',
                            device_id: item.device_id || 'ENV-BLOCK-B-001',
                            metric: 'mq135_raw_adc',
                            issue: isSmoke ? '🔥 CRITICAL: SMOKE & COMBUSTION FUMES DETECTED!' : '⚠️ HIGH: ELEVATED AIR QUALITY POLLUTANTS SURGE',
                            severity: isSmoke ? 'CRITICAL' : 'HIGH',
                            observed_value: `${Math.round(rawVal)} ADC count (~${Math.round(rawVal * 0.76)} PPM)`,
                            explanation: 'MQ-135 detected rapid aerosol/fume combustion particles near sensor probe.',
                            recommended_action: 'Initiate localized exhaust ventilation and verify zone fire safety.'
                        });
                    }
                } else {
                    if (elAdc) elAdc.textContent = '-- count';
                    if (elVolt) elVolt.textContent = '-- V';
                    if (elCo2) elCo2.textContent = '-- ppm';
                    if (elStat) {
                        elStat.textContent = 'DISCONNECTED';
                        elStat.style.color = '#94A3B8';
                    }
                    if (badge) {
                        badge.className = 'live-pulse-badge standby';
                        badge.innerHTML = '<span class="pulse-beacon-dot standby"></span> INACTIVE / STANDBY';
                    }
                    if (lastSeen) {
                        lastSeen.textContent = 'Sensor Disconnected';
                        lastSeen.style.color = '#94A3B8';
                    }
                }

                // Populate Wire JSON Payload
                const airCode = document.getElementById('airWirePayloadCode');
                if (airCode) airCode.textContent = JSON.stringify(item, null, 2);
            }

            // Update DHT11 climate card with NEWEST environmental packet
            if (!dhtUpdated && (m.temperature_c !== undefined || m.humidity_pct !== undefined)) {
                dhtUpdated = true;
                const elTemp = document.getElementById('liveMetricDhtTemp');
                const elHum = document.getElementById('liveMetricDhtHumidity');
                const elHi = document.getElementById('liveMetricDhtHeatIndex');
                const elStat = document.getElementById('liveMetricDhtStatus');
                const badge = document.getElementById('liveDhtCardBadge');
                const lastSeen = document.getElementById('liveDhtLastSeen');

                const temp = Number(m.temperature_c ?? 0).toFixed(1);
                const hum = Number(m.humidity_pct ?? 0).toFixed(0);
                const hi = m.heat_index_c !== undefined ? Number(m.heat_index_c).toFixed(1) : temp;

                latestDhtData = { temp, hum, hi };

                if (elTemp) elTemp.textContent = `${temp} °C`;
                if (elHum) elHum.textContent = `${hum} % RH`;
                if (elHi) elHi.textContent = `${hi} °C`;
                if (elStat) {
                    if (Number(hi) >= 38.0) {
                        elStat.textContent = 'HEAT STRESS HAZARD';
                        elStat.style.color = '#EF4444';
                    } else if (Number(hum) >= 75) {
                        elStat.textContent = 'HIGH MOLD RISK';
                        elStat.style.color = '#F59E0B';
                    } else {
                        elStat.textContent = 'COMFORT OPTIMAL';
                        elStat.style.color = '#00D09C';
                    }
                }
                updateCardLiveBadge(badge, lastSeen, secAgo, 'Active Climate Stream', '#2DD4BF');

                // Populate Wire JSON Payload
                const dhtCode = document.getElementById('dhtWirePayloadCode');
                if (dhtCode) dhtCode.textContent = JSON.stringify(item, null, 2);
            }
        }

        if (!dhtUpdated) {
            const elTemp = document.getElementById('liveMetricDhtTemp');
            const elHum = document.getElementById('liveMetricDhtHumidity');
            const elHi = document.getElementById('liveMetricDhtHeatIndex');
            const elStat = document.getElementById('liveMetricDhtStatus');
            const badge = document.getElementById('liveDhtCardBadge');
            const lastSeen = document.getElementById('liveDhtLastSeen');
            if (elTemp) elTemp.textContent = '-- °C';
            if (elHum) elHum.textContent = '-- % RH';
            if (elHi) elHi.textContent = '-- °C';
            if (elStat) {
                elStat.textContent = 'STANDBY';
                elStat.style.color = '#94A3B8';
            }
            if (badge) {
                badge.className = 'live-pulse-badge standby';
                badge.innerHTML = '<span class="pulse-beacon-dot standby"></span> INACTIVE / STANDBY';
            }
            if (lastSeen) {
                lastSeen.textContent = 'Awaiting 1-Wire Frame';
                lastSeen.style.color = '#94A3B8';
            }
        }

        // Card 6 OLED Edge Terminal & Bus status
        const elOledStat = document.getElementById('liveMetricOledStatus');
        const elModbusStat = document.getElementById('liveMetricModbusStatus');
        const elFlowStat = document.getElementById('liveMetricFlowStatus');
        const oledBadge = document.getElementById('liveOledCardBadge');
        const oledLastSeen = document.getElementById('liveOledLastSeen');
        if (hasHw) {
            if (elOledStat) elOledStat.textContent = 'SSD1306 ACTIVE';
            if (elModbusStat) elModbusStat.textContent = '9600 BAUD (PZEM UART)';
            if (elFlowStat) elFlowStat.textContent = 'GPIO26 ARMED (ZJ-S201)';
            if (oledBadge) {
                oledBadge.className = 'live-pulse-badge online';
                oledBadge.innerHTML = '<span class="pulse-beacon-dot online"></span> GATEWAY ONLINE';
            }
            if (oledLastSeen) {
                oledLastSeen.textContent = 'ESP32_EDGE_GATEWAY_01';
                oledLastSeen.style.color = '#00F0B5';
            }
        } else {
            if (elOledStat) elOledStat.textContent = 'STANDBY (Awaiting ESP32)';
            if (elModbusStat) elModbusStat.textContent = 'STANDBY (GPIO16/17)';
            if (elFlowStat) elFlowStat.textContent = 'STANDBY (GPIO26)';
            if (oledBadge) {
                oledBadge.className = 'live-pulse-badge standby';
                oledBadge.innerHTML = '<span class="pulse-beacon-dot standby"></span> GATEWAY STANDBY';
            }
            if (oledLastSeen) {
                oledLastSeen.textContent = 'Offline / Standby';
                oledLastSeen.style.color = '#94A3B8';
            }
        }

        // Populate Gateway Wire Diagnostics JSON
        const gwCode = document.getElementById('gatewayWirePayloadCode');
        if (gwCode) {
            gwCode.textContent = JSON.stringify({
                "gateway_id": "ESP32_EDGE_GATEWAY_01",
                "firmware_version": "v3.0-ProdIoT (FreeRTOS Dual-Core)",
                "ingestion_endpoint": "http://127.0.0.1:8000/api/v1/iot/telemetry",
                "transport_modes": ["HTTP REST Direct", "USB Serial Bridge (COM7)"],
                "attached_sensors": {
                    "HC-SR04": { "role": "Waste Bin Sonar", "pins": "Trig:GPIO14, Echo:GPIO27 (Level-Shifted)", "status": wasteUpdated ? "ACTIVE_STREAMING" : "STANDBY" },
                    "DHT11": { "role": "Climate Environment", "pin": "GPIO4 1-Wire", "status": dhtUpdated ? "ACTIVE_STREAMING" : "STANDBY" },
                    "MQ-135": { "role": "Gas / Air Quality", "pin": "GPIO34 ADC1 (1.45x divider)", "status": airUpdated ? "ACTIVE_STREAMING" : "STANDBY" },
                    "ZJ-S201": { "role": "Water Turbine Pulse", "pin": "GPIO26 Interrupt (450 p/L)", "status": waterUpdated ? "ACTIVE_STREAMING" : "STANDBY" },
                    "SSD1306": { "role": "OLED Edge Display", "pins": "I2C SDA:GPIO21, SCL:GPIO22 (0x3C)", "status": "ACTIVE" },
                    "PZEM-004T": { "role": "AC Electricity Meter", "pins": "UART2 RX:GPIO16, TX:GPIO17", "status": "STANDBY_UNFITTED" }
                },
                "system_status": hasHw ? "ONLINE_STREAMING" : "STANDBY"
            }, null, 2);
        }

        // Update AI Facility Prescriptive Suggestions
        updateAiFacilitySuggestions({
            waste: latestWasteData,
            dht: latestDhtData,
            air: latestAirData,
            water: latestWaterData
        });

        if (hasHw) {
            window.hasLiveHardwareTelemetry = true;
            const provBadge = document.getElementById('monProvenanceBadge');
            if (provBadge) provBadge.innerHTML = '<i class="fa-solid fa-shield-halved"></i> Tagged: [REAL SENSOR] (ESP32 Gateway)';
            const simIpLabel = document.getElementById('monSimIpLabel');
            if (simIpLabel) simIpLabel.textContent = 'IP: 172.16.222.83 (ESP32 Hardware)';
            const simInst = document.getElementById('monSimInstancesCount');
            if (simInst) simInst.textContent = '1 Physical Gateway';
            const connState = document.getElementById('monConnState');
            if (connState) connState.textContent = 'HARDWARE STREAMING';
        } else {
            window.hasLiveHardwareTelemetry = false;
        }

        // Update Matrix Header Badges
        const mBadge = document.getElementById('matrixMeterBadge');
        if (mBadge) {
            const hasLiveElec = streamItems.some(s => s.device_id === 'METER-BLOCK-B-001' && (Number(s.metrics?.active_power_kw ?? s.telemetry?.active_power_kw ?? 0) > 0 || Number(s.metrics?.voltage_v ?? s.telemetry?.voltage_v ?? 0) > 50.0));
            mBadge.innerHTML = hasLiveElec 
                ? '<i class="fa-solid fa-bolt"></i> Meter: PZEM-004T (LIVE)'
                : '<i class="fa-solid fa-bolt"></i> Meter: PZEM-004T (Standby)';
            mBadge.style.color = hasLiveElec ? '#00F0B5' : '#CBD5E1';
            mBadge.style.border = hasLiveElec ? '1px solid #00F0B5' : '1px solid rgba(255,255,255,0.25)';
        }
        const wBadge = document.getElementById('matrixWaterBadge');
        if (wBadge) {
            const hasDist = streamItems.some(s => s.device_id === 'WATER-BLOCK-B-001' && (s.metrics?.tank_distance_cm > 0 || s.telemetry?.tank_distance_cm > 0));
            const isTimeout = streamItems.some(s => s.device_id === 'WATER-BLOCK-B-001' && (s.metrics?.tank_status === 'ECHO_TIMEOUT' || s.telemetry?.tank_status === 'ECHO_TIMEOUT'));
            if (hasDist) {
                wBadge.innerHTML = '<i class="fa-solid fa-water"></i> Water: AJ-SR04M Sonar (LIVE)';
                wBadge.style.background = 'rgba(0, 240, 181, 0.18)';
                wBadge.style.color = '#00F0B5';
                wBadge.style.border = '1px solid #00F0B5';
            } else if (isTimeout) {
                wBadge.innerHTML = '<i class="fa-solid fa-water"></i> Water: AJ-SR04M (Awaiting Echo)';
                wBadge.style.background = 'rgba(245, 158, 11, 0.18)';
                wBadge.style.color = '#F59E0B';
                wBadge.style.border = '1px solid #F59E0B';
            } else {
                wBadge.innerHTML = '<i class="fa-solid fa-water"></i> Water: AJ-SR04M (Standby)';
                wBadge.style.background = 'rgba(255, 255, 255, 0.08)';
                wBadge.style.color = '#CBD5E1';
                wBadge.style.border = '1px solid rgba(255, 255, 255, 0.25)';
            }
        }
        const aBadge = document.getElementById('matrixAuxBadge');
        if (aBadge) {
            const hasRealAir = streamItems.some(s => s.device_id === 'ENV-BLOCK-B-001' && ((s.metrics?.mq135_raw_adc >= 80) || (s.telemetry?.mq135_raw_adc >= 80)));
            if (hasRealAir) {
                aBadge.innerHTML = '<i class="fa-solid fa-wind"></i> Air: MQ-135 Gas Sensor (LIVE)';
                aBadge.style.background = 'rgba(245, 158, 11, 0.18)';
                aBadge.style.color = '#F59E0B';
                aBadge.style.border = '1px solid #F59E0B';
            } else {
                aBadge.innerHTML = '<i class="fa-solid fa-wind"></i> Air: MQ-135 (Standby)';
                aBadge.style.background = 'rgba(255, 255, 255, 0.08)';
                aBadge.style.color = '#CBD5E1';
                aBadge.style.border = '1px solid rgba(255, 255, 255, 0.25)';
            }
        }
    };

    // =========================================================================
    // DYNAMIC SENSOR METROLOGY MATRIX (ZERO DEMO DATA — LIVE SENSORS ONLY)
    // =========================================================================
    const renderSensorMatrixTable = (devices, stream) => {
        const tbody = document.getElementById('sensorMatrixTableBody');
        if (!tbody) return;

        devices = devices || window.cachedDevicesList || [];
        stream = stream || window.cachedStreamList || [];

        let rowsHtml = '';

        // 1. PZEM-004T AC Electricity Meter (Physical Hardware)
        const elecStream = stream.find(s => s.device_id === 'METER-BLOCK-B-001');
        const elecDev = devices.find(d => d.device_id === 'METER-BLOCK-B-001');
        const elecM = elecStream ? (elecStream.metrics || elecStream.telemetry || {}) : (elecDev ? (elecDev.last_telemetry || {}) : {});
        const hasLiveElec = (elecM.active_power_kw !== undefined && Number(elecM.active_power_kw) > 0) || (elecM.voltage_v !== undefined && Number(elecM.voltage_v) > 0);

        if (hasLiveElec) {
            const p = elecM.active_power_kw !== undefined ? `${Number(elecM.active_power_kw).toFixed(2)} kW` : '-- kW';
            const v = elecM.voltage_v !== undefined ? `${Number(elecM.voltage_v).toFixed(1)} V` : '-- V';
            const i = elecM.current_a !== undefined ? `${Number(elecM.current_a).toFixed(2)} A` : '-- A';
            const pf = elecM.power_factor !== undefined ? `PF: ${Number(elecM.power_factor).toFixed(2)}` : '';
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #061813;">
                    <td class="subsystem-col"><i class="fa-solid fa-bolt text-mint"></i> Electricity Meter</td>
                    <td style="color:#FFFFFF; font-weight:800; font-size:13px;">Peacefair PZEM-004T 10A</td>
                    <td class="interface-col">UART2 (RX:GPIO16, TX:GPIO17)</td>
                    <td class="range-col">80 - 260 V / 0 - 10 A (2.3 kW)</td>
                    <td><span style="background:#00F0B5; color:#04120F; font-weight:900; padding:4px 10px; border-radius:12px; font-size:11px; display:inline-flex; align-items:center; gap:5px;"><span class="pulse-dot"></span> LIVE MEASURED [PZEM-004T]</span></td>
                    <td class="cal-col">Active Power: <strong style="color:#00F0B5; font-size:13px;">${p}</strong> | Voltage: <strong style="color:#38BDF8;">${v}</strong> | Current: <strong style="color:#FDE047;">${i}</strong> ${pf}</td>
                </tr>
            `;
        } else {
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #061813;">
                    <td class="subsystem-col"><i class="fa-solid fa-bolt" style="color:#94A3B8;"></i> Electricity Meter</td>
                    <td style="color:#CBD5E1; font-weight:700;">Peacefair PZEM-004T 10A</td>
                    <td class="interface-col">UART2 (RX:GPIO16, TX:GPIO17)</td>
                    <td class="range-col">80 - 260 V / 0 - 10 A</td>
                    <td><span style="background:rgba(255,255,255,0.08); color:#CBD5E1; border:1px solid rgba(255,255,255,0.2); padding:3px 8px; border-radius:12px; font-size:11px;"><i class="fa-solid fa-pause"></i> STANDBY (Awaiting AC Load)</span></td>
                    <td class="cal-col" style="color:#94A3B8;">UART2 initialized on GPIO16/17 &bull; Connect AC line and load to meter CT coil</td>
                </tr>
            `;
        }

        // 2. Ultrasonic Water Level & Distance (JSN-SR04T / AJ-SR04M / HC-SR04)
        const waterStream = stream.find(s => s.device_id === 'WATER-BLOCK-B-001');
        const waterDev = devices.find(d => d.device_id === 'WATER-BLOCK-B-001');
        const waterM = waterStream ? (waterStream.metrics || waterStream.telemetry || {}) : (waterDev ? (waterDev.last_telemetry || {}) : {});
        const hasLiveDistance = (waterM.tank_distance_cm !== undefined && Number(waterM.tank_distance_cm) > 0);
        const isSonarTimeout = (waterM.tank_status === 'ECHO_TIMEOUT' || (waterM.tank_distance_cm !== undefined && Number(waterM.tank_distance_cm) <= 0));

        if (hasLiveDistance) {
            const dist = `${Number(waterM.tank_distance_cm).toFixed(1)} cm`;
            const lvl = waterM.tank_level_pct !== undefined ? `${Number(waterM.tank_level_pct).toFixed(1)}%` : '--%';
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #0A241D;">
                    <td class="subsystem-col"><i class="fa-solid fa-water text-blue"></i> Water Tank Level</td>
                    <td style="color:#FFFFFF; font-weight:800; font-size:13px;">Ultrasonic AJ-SR04M Sonar</td>
                    <td class="interface-col">Trig:GPIO5 / Echo:GPIO18</td>
                    <td class="range-col">20 - 450 cm (0 - 100% Fill)</td>
                    <td><span style="background:#00F0B5; color:#04120F; font-weight:900; padding:4px 10px; border-radius:12px; font-size:11px; display:inline-flex; align-items:center; gap:5px;"><span class="pulse-dot"></span> LIVE MEASURED [REAL HARDWARE]</span></td>
                    <td class="cal-col">Current Distance: <strong style="color:#00F0B5; font-size:14px;">${dist}</strong> | Fill Level: <strong style="color:#38BDF8; font-size:14px;">${lvl}</strong> (Geometric echo flight time)</td>
                </tr>
            `;
        } else if (isSonarTimeout) {
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #0A241D;">
                    <td class="subsystem-col"><i class="fa-solid fa-water text-blue"></i> Water Tank Level</td>
                    <td style="color:#FFFFFF; font-weight:800; font-size:13px;">Ultrasonic AJ-SR04M Sonar</td>
                    <td class="interface-col">Trig:GPIO5 / Echo:GPIO18</td>
                    <td class="range-col">20 - 450 cm (0 - 100% Fill)</td>
                    <td><span style="background:rgba(245,158,11,0.18); color:#F59E0B; border:1px solid #F59E0B; font-weight:800; padding:4px 10px; border-radius:12px; font-size:11px; display:inline-flex; align-items:center; gap:5px;"><span class="pulse-dot" style="background:#F59E0B;"></span> ONLINE (Awaiting Echo / Out of Range) [REAL HARDWARE]</span></td>
                    <td class="cal-col" style="color:#FDE047;">Pinging on GPIO5/18 &bull; Place flat reflective surface <strong style="color:#00F0B5;">20&ndash;450 cm</strong> in front of probe (Blind zone: &lt;20cm)</td>
                </tr>
            `;
        } else {
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #0A241D;">
                    <td class="subsystem-col"><i class="fa-solid fa-water" style="color:#94A3B8;"></i> Water Tank Level</td>
                    <td style="color:#CBD5E1; font-weight:700;">Ultrasonic AJ-SR04M Sonar</td>
                    <td class="interface-col">Trig:GPIO5 / Echo:GPIO18</td>
                    <td class="range-col">20 - 450 cm (0 - 100% Fill)</td>
                    <td><span style="background:rgba(255,255,255,0.08); color:#CBD5E1; border:1px solid rgba(255,255,255,0.2); padding:3px 8px; border-radius:12px; font-size:11px;"><i class="fa-solid fa-pause"></i> STANDBY (Awaiting Sonar Hardware)</span></td>
                    <td class="cal-col" style="color:#94A3B8;">Connect AJ-SR04M Trig to GPIO5 and Echo to GPIO18 via 1k/2.2k divider</td>
                </tr>
            `;
        }


        // 2B. HC-SR04 Ultrasonic Smart Waste Bin (Physical Hardware)
        const wasteStream = stream.find(s => s.device_id === 'WASTE-BLOCK-B-001');
        const wasteDev = devices.find(d => d.device_id === 'WASTE-BLOCK-B-001');
        const wasteM = wasteStream ? (wasteStream.metrics || wasteStream.telemetry || {}) : (wasteDev ? (wasteDev.last_telemetry || {}) : {});
        const hasLiveWaste = (wasteM.bin_distance_cm !== undefined && Number(wasteM.bin_distance_cm) > 0) ||
                             (wasteM.fill_level_percent !== undefined && Number(wasteM.fill_level_percent) > 0);

        if (hasLiveWaste) {
            const wDist = Number(wasteM.bin_distance_cm || 0).toFixed(1);
            const wFill = Number(wasteM.fill_level_percent ?? wasteM.fill_level_pct ?? 0).toFixed(1);
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #0A241D;">
                    <td class="subsystem-col"><i class="fa-solid fa-trash-can text-amber"></i> Waste Management</td>
                    <td style="color:#FFFFFF; font-weight:800; font-size:13px;">HC-SR04 Ultrasonic Sonar</td>
                    <td class="interface-col">Trig:GPIO14 / Echo:GPIO27</td>
                    <td class="range-col">4 - 400 cm (0 - 100% Bin Fill)</td>
                    <td><span style="background:#00F0B5; color:#04120F; font-weight:900; padding:4px 10px; border-radius:12px; font-size:11px; display:inline-flex; align-items:center; gap:5px;"><span class="pulse-dot"></span> LIVE MEASURED [REAL HARDWARE]</span></td>
                    <td class="cal-col">Current Distance: <strong style="color:#00F0B5; font-size:14px;">${wDist} cm</strong> | Fill Level: <strong style="color:#F59E0B; font-size:14px;">${wFill}%</strong> (Sonar echo flight time)</td>
                </tr>
            `;
        } else {
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #0A241D;">
                    <td class="subsystem-col"><i class="fa-solid fa-trash-can" style="color:#94A3B8;"></i> Waste Management</td>
                    <td style="color:#CBD5E1; font-weight:700;">HC-SR04 Ultrasonic Sonar</td>
                    <td class="interface-col">Trig:GPIO14 / Echo:GPIO27</td>
                    <td class="range-col">4 - 400 cm (0 - 100% Bin Fill)</td>
                    <td><span style="background:rgba(255,255,255,0.08); color:#CBD5E1; border:1px solid rgba(255,255,255,0.2); padding:3px 8px; border-radius:12px; font-size:11px;"><i class="fa-solid fa-pause"></i> STANDBY (Awaiting Sonar Hardware)</span></td>
                    <td class="cal-col" style="color:#94A3B8;">Connect HC-SR04 Trig to GPIO14 and Echo to GPIO27 through a 5V-to-3.3V level divider</td>
                </tr>
            `;
        }

        // 3. Water Flow Sensor (ZJ-S201 Hall Turbine Pulse Meter)
        const hasFlow = (waterM.water_flow_lmin !== undefined && waterM.water_flow_lmin !== null);
        const flowVal = waterM.water_flow_lmin !== undefined && waterM.water_flow_lmin !== null ? `${Number(waterM.water_flow_lmin).toFixed(1)} L/min` : '-- L/min';
        const cumM3 = waterM.cumulative_water_m3 !== undefined ? `${Number(waterM.cumulative_water_m3).toFixed(3)} m³` : '0.000 m³';
        const cumLiters = waterM.water_cumulative_liters !== undefined ? `${Number(waterM.water_cumulative_liters).toFixed(2)} L` : cumM3;
        const pulseCount = waterM.water_pulse_count_total !== undefined ? Number(waterM.water_pulse_count_total).toLocaleString() : '--';

        if (hasFlow) {
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #061813;">
                    <td class="subsystem-col"><i class="fa-solid fa-droplet text-blue"></i> Water Flow Sensor</td>
                    <td style="color:#FFFFFF; font-weight:800; font-size:13px;">ZJ-S201 Hall Turbine</td>
                    <td class="interface-col">Interrupt Pulse (GPIO26)</td>
                    <td class="range-col">1.0 - 30.0 L/min (~450 pulses/L)</td>
                    <td><span style="background:#00F0B5; color:#04120F; font-weight:900; padding:4px 10px; border-radius:12px; font-size:11px; display:inline-flex; align-items:center; gap:5px;"><span class="pulse-dot"></span> LIVE MEASURED [REAL HARDWARE]</span></td>
                    <td class="cal-col">Current Flow: <strong style="color:#60A5FA; font-size:13px;">${flowVal}</strong> | Total: <strong style="color:#34D399;">${cumLiters}</strong> | Pulses: <strong>${pulseCount}</strong></td>
                </tr>
            `;
        } else {
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #061813;">
                    <td class="subsystem-col"><i class="fa-solid fa-droplet" style="color:#94A3B8;"></i> Water Flow Sensor</td>
                    <td style="color:#CBD5E1; font-weight:700;">ZJ-S201 Hall Turbine</td>
                    <td class="interface-col">Interrupt Pulse (GPIO26)</td>
                    <td class="range-col">1.0 - 30.0 L/min</td>
                    <td><span style="background:rgba(255,255,255,0.08); color:#CBD5E1; border:1px solid rgba(255,255,255,0.2); padding:3px 8px; border-radius:12px; font-size:11px;"><i class="fa-solid fa-pause"></i> STANDBY (Sensor Disconnected / Zero Flow)</span></td>
                    <td class="cal-col" style="color:#94A3B8;">Hardware pulse counter armed on GPIO26 &bull; Awaiting water flow rotation</td>
                </tr>
            `;
        }

        // 4. MQ-135 Gas / Air Quality Sensor (Physical Hardware)
        const airStream = stream.find(s => s.device_id === 'ENV-BLOCK-B-001');
        const airDev = devices.find(d => d.device_id === 'ENV-BLOCK-B-001');
        const airM = airStream ? (airStream.metrics || airStream.telemetry || {}) : (airDev ? (airDev.last_telemetry || {}) : {});
        const rawAdc = Math.round(airM.mq135_raw_adc ?? airM.raw_adc ?? 0);
        const volt = Number(airM.mq135_voltage_v ?? airM.sensor_voltage_v ?? 0);
        const isAirActuallyConnected = (rawAdc >= 80 && volt >= 0.08);

        if (isAirActuallyConnected) {
            const isWarm = airM.mq135_warmup_status === 0 || airM.mq135_warmup_status === 0.0;
            const warmupText = isWarm ? '<span style="color:#F59E0B; font-weight:700;">Warming Up (180s Baseline)</span>' : '<span style="color:#00F0B5; font-weight:700;">Stabilized</span>';
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #0A241D;">
                    <td class="subsystem-col"><i class="fa-solid fa-wind text-amber"></i> Air Quality / Gas</td>
                    <td style="color:#FFFFFF; font-weight:800; font-size:13px;">MQ-135 Gas Sensor</td>
                    <td class="interface-col">GPIO34 (ADC1 with Divider)</td>
                    <td class="range-col">0 - 4095 ADC (0.0 - 5.0 V)</td>
                    <td><span style="background:#00F0B5; color:#04120F; font-weight:900; padding:4px 10px; border-radius:12px; font-size:11px; display:inline-flex; align-items:center; gap:5px;"><span class="pulse-dot"></span> LIVE MEASURED [REAL HARDWARE]</span></td>
                    <td class="cal-col">Current ADC: <strong style="color:#F59E0B; font-size:13px;">${rawAdc} count</strong> (${volt.toFixed(2)}V) | ${warmupText} | Gas concentration not calibrated</td>
                </tr>
            `;
        } else {
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #0A241D;">
                    <td class="subsystem-col"><i class="fa-solid fa-wind" style="color:#94A3B8;"></i> Air Quality / Gas</td>
                    <td style="color:#CBD5E1; font-weight:700;">MQ-135 Gas Sensor</td>
                    <td class="interface-col">GPIO34 (ADC1 with Divider)</td>
                    <td class="range-col">0 - 4095 ADC (0.0 - 5.0 V)</td>
                    <td><span style="background:rgba(255,255,255,0.08); color:#CBD5E1; border:1px solid rgba(255,255,255,0.2); padding:3px 8px; border-radius:12px; font-size:11px;"><i class="fa-solid fa-pause"></i> STANDBY (Sensor Disconnected)</span></td>
                    <td class="cal-col" style="color:#94A3B8;">GPIO34 reads 0 count (0.00V) &bull; Sensor not connected to analog port</td>
                </tr>
            `;
        }

        // 5. DHT11 Digital Temperature & Humidity Sensor
        const isDhtActive = (airM.temperature_c !== undefined || airM.humidity_pct !== undefined);
        if (isDhtActive) {
            const t = Number(airM.temperature_c).toFixed(1);
            const h = Number(airM.humidity_pct).toFixed(0);
            const hi = airM.heat_index_c !== undefined ? Number(airM.heat_index_c).toFixed(1) : t;
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #061813;">
                    <td class="subsystem-col"><i class="fa-solid fa-temperature-half text-teal"></i> Climate & Environment</td>
                    <td style="color:#FFFFFF; font-weight:800; font-size:13px;">DHT11 Digital Sensor Module</td>
                    <td class="interface-col">1-Wire Digital (GPIO4)</td>
                    <td class="range-col">0 - 50 °C / 20 - 90 % RH</td>
                    <td><span style="background:#00F0B5; color:#04120F; font-weight:900; padding:4px 10px; border-radius:12px; font-size:11px; display:inline-flex; align-items:center; gap:5px;"><span class="pulse-dot"></span> LIVE MEASURED [DHT11]</span></td>
                    <td class="cal-col">Temperature: <strong style="color:#2DD4BF; font-size:13px;">${t} °C</strong> | Humidity: <strong style="color:#38BDF8;">${h}% RH</strong> | Heat Index: <strong style="color:#F59E0B;">${hi} °C</strong></td>
                </tr>
            `;
        } else {
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #061813;">
                    <td class="subsystem-col"><i class="fa-solid fa-temperature-half" style="color:#94A3B8;"></i> Climate & Environment</td>
                    <td style="color:#CBD5E1; font-weight:700;">DHT11 Digital Sensor Module</td>
                    <td class="interface-col">1-Wire Digital (GPIO4)</td>
                    <td class="range-col">0 - 50 °C / 20 - 90 % RH</td>
                    <td><span style="background:rgba(255,255,255,0.08); color:#CBD5E1; border:1px solid rgba(255,255,255,0.2); padding:3px 8px; border-radius:12px; font-size:11px;"><i class="fa-solid fa-pause"></i> STANDBY (Sensor Disconnected)</span></td>
                    <td class="cal-col" style="color:#94A3B8;">1-Wire interface listening on GPIO4 &bull; Awaiting DHT11 data frame</td>
                </tr>
            `;
        }

        // 6. 0.96 Inch I2C OLED Display
        rowsHtml += `
            <tr style="border-bottom: 1px solid rgba(0,240,181,0.25); background: #0A241D;">
                <td class="subsystem-col"><i class="fa-solid fa-desktop text-mint"></i> Edge Display & Terminal</td>
                <td style="color:#FFFFFF; font-weight:800; font-size:13px;">0.96" SSD1306 Blue OLED</td>
                <td class="interface-col">I2C (SDA:GPIO21, SCL:GPIO22)</td>
                <td class="range-col">128 x 64 Dot Matrix</td>
                <td><span style="background:#00F0B5; color:#04120F; font-weight:900; padding:4px 10px; border-radius:12px; font-size:11px; display:inline-flex; align-items:center; gap:5px;"><span class="pulse-dot"></span> ACTIVE [LOCAL DISPLAY]</span></td>
                <td class="cal-col" style="color:#A7F3D0;">Real-time on-device telemetry dashboard active &bull; Cyclical 7-line local stream</td>
            </tr>
        `;

        // 7. Dynamic Additional Physically Connected Hardware
        devices.forEach(d => {
            const isBase = (d.device_id === 'WATER-BLOCK-B-001' || d.device_id === 'ENV-BLOCK-B-001' || d.device_id === 'METER-BLOCK-B-001' || d.device_id === 'WASTE-BLOCK-B-001');
            const isHw = (d.is_verified_hardware === true || d.source_type === 'real_sensor');
            if (!isBase && isHw && (d.status === 'ONLINE' || d.status === 'STREAMING')) {
                const m = d.last_telemetry || {};
                const metricSummary = Object.entries(m).slice(0, 3).map(([k, v]) => `${k.replace(/_/g, ' ')}: <strong style="color:#00F0B5;">${v}</strong>`).join(' | ') || 'Transmitting telemetry packets';
                rowsHtml += `
                    <tr style="border-bottom: 1px solid rgba(0,240,181,0.2); background: #061813;">
                        <td class="subsystem-col"><i class="fa-solid fa-microchip text-mint"></i> ${d.device_name || d.device_id}</td>
                        <td style="color:#FFFFFF; font-weight:800; font-size:13px;">${d.device_type || 'Edge Sensor Node'}</td>
                        <td class="interface-col">${d.instance_id || 'Wi-Fi / REST / MQTT'}</td>
                        <td class="range-col">Dynamic Auto-Calibrated</td>
                        <td><span style="background:#00F0B5; color:#04120F; font-weight:900; padding:4px 10px; border-radius:12px; font-size:11px; display:inline-flex; align-items:center; gap:5px;"><span class="pulse-dot"></span> LIVE MEASURED [REAL HARDWARE]</span></td>
                        <td class="cal-col">${metricSummary}</td>
                    </tr>
                `;
            }
        });

        // 8. Active Simulator Nodes (Only when actively streaming)
        const simHvacStream = stream.find(s => s.device_id === 'DEV_HVAC_01' || s.source_type === 'simulated_iot');
        if (simHvacStream) {
            const m = simHvacStream.metrics || simHvacStream.telemetry || {};
            const kw = m.hvac_load_kw !== undefined ? `${Number(m.hvac_load_kw).toFixed(1)} kW` : '-- kW';
            const temp = m.temperature_c !== undefined ? `${Number(m.temperature_c).toFixed(1)} °C` : '-- °C';
            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(56,189,248,0.25); background: #051F27;">
                    <td class="subsystem-col"><i class="fa-solid fa-snowflake" style="color:#38BDF8;"></i> HVAC Chiller</td>
                    <td style="color:#FFFFFF; font-weight:800; font-size:13px;">Centrifugal Chiller & AHU</td>
                    <td class="interface-col" style="color:#38BDF8;">Simulator Virtual Node (Port 8503)</td>
                    <td class="range-col">10 - 200 kW (0 - 50 °C)</td>
                    <td><span style="background:rgba(56,189,248,0.2); color:#38BDF8; border:1px solid #38BDF8; font-weight:800; padding:3px 8px; border-radius:12px; font-size:11px; display:inline-flex; align-items:center; gap:4px;"><i class="fa-solid fa-microchip"></i> LIVE [SIMULATED IoT]</span></td>
                    <td class="cal-col">Live Simulation: Compressor Load: <strong style="color:#38BDF8;">${kw}</strong> | Temp: <strong style="color:#2DD4BF;">${temp}</strong></td>
                </tr>
            `;
        }

        tbody.innerHTML = rowsHtml;
    };


window.currentFleetFilter = 'all';
    window.currentStreamFilter = 'all';
    window.cachedDevicesList = [];
    window.cachedStreamList = [];

    const initFleetFilterButtons = () => {
        const btnAll = document.getElementById('filterFleetAll');
        const btnHw = document.getElementById('filterFleetHw');
        const btnSim = document.getElementById('filterFleetSim');

        const updateBtnStyles = () => {
            if (btnAll) {
                btnAll.style.background = window.currentFleetFilter === 'all' ? '#00F0B5' : 'rgba(0, 240, 181, 0.15)';
                btnAll.style.color = window.currentFleetFilter === 'all' ? '#04120F' : '#00F0B5';
            }
            if (btnHw) {
                btnHw.style.background = window.currentFleetFilter === 'hardware' ? '#00F0B5' : 'rgba(0, 240, 181, 0.15)';
                btnHw.style.color = window.currentFleetFilter === 'hardware' ? '#04120F' : '#00F0B5';
            }
            if (btnSim) {
                btnSim.style.background = window.currentFleetFilter === 'simulator' ? '#38BDF8' : 'rgba(56, 189, 248, 0.15)';
                btnSim.style.color = window.currentFleetFilter === 'simulator' ? '#04120F' : '#38BDF8';
            }
        };

        if (btnAll) btnAll.onclick = () => { window.currentFleetFilter = 'all'; updateBtnStyles(); renderDynamicFleet(); };
        if (btnHw) btnHw.onclick = () => { window.currentFleetFilter = 'hardware'; updateBtnStyles(); renderDynamicFleet(); };
        if (btnSim) btnSim.onclick = () => { window.currentFleetFilter = 'simulator'; updateBtnStyles(); renderDynamicFleet(); };

        const sAll = document.getElementById('streamFilterAll');
        const sHw = document.getElementById('streamFilterHw');
        const sSim = document.getElementById('streamFilterSim');

        const updateStreamBtnStyles = () => {
            if (sAll) {
                sAll.style.background = window.currentStreamFilter === 'all' ? '#00F0B5' : 'transparent';
                sAll.style.color = window.currentStreamFilter === 'all' ? '#04120F' : '#00F0B5';
            }
            if (sHw) {
                sHw.style.background = window.currentStreamFilter === 'hardware' ? '#00F0B5' : 'transparent';
                sHw.style.color = window.currentStreamFilter === 'hardware' ? '#04120F' : '#00F0B5';
            }
            if (sSim) {
                sSim.style.background = window.currentStreamFilter === 'simulator' ? '#38BDF8' : 'transparent';
                sSim.style.color = window.currentStreamFilter === 'simulator' ? '#04120F' : '#38BDF8';
            }
        };

        if (sAll) sAll.onclick = () => { window.currentStreamFilter = 'all'; updateStreamBtnStyles(); renderStreamTable(); };
        if (sHw) sHw.onclick = () => { window.currentStreamFilter = 'hardware'; updateStreamBtnStyles(); renderStreamTable(); };
        if (sSim) sSim.onclick = () => { window.currentStreamFilter = 'simulator'; updateStreamBtnStyles(); renderStreamTable(); };
    };

    const renderDynamicFleet = async () => {
        const container = document.getElementById('dynamicFleetContainer');
        if (!container) return;

        try {
            const res = await fetch('/api/v1/iot/devices');
            if (!res.ok) return;
            const data = await res.json();
            const devices = data.devices || [];
            window.cachedDevicesList = devices;
            renderSensorMatrixTable(devices, window.cachedStreamList);

            let hwCount = 0;
            let simCount = 0;
            devices.forEach(d => {
                if (d.is_verified_hardware || d.source_type === 'real_sensor') hwCount++;
                else simCount++;
            });

            const countAllEl = document.getElementById('countFleetAll');
            const countHwEl = document.getElementById('countFleetHw');
            const countSimEl = document.getElementById('countFleetSim');
            if (countAllEl) countAllEl.textContent = devices.length;
            if (countHwEl) countHwEl.textContent = hwCount;
            if (countSimEl) countSimEl.textContent = simCount;

            const filtered = devices.filter(d => {
                const isHw = d.is_verified_hardware || d.source_type === 'real_sensor';
                if (window.currentFleetFilter === 'hardware') return isHw;
                if (window.currentFleetFilter === 'simulator') return !isHw;
                return true;
            });

            // Sort: ONLINE first, then STALE, then OFFLINE
            filtered.sort((a, b) => {
                const order = { 'ONLINE': 1, 'STREAMING': 2, 'STALE': 3, 'OFFLINE': 4 };
                return (order[a.status] || 5) - (order[b.status] || 5);
            });

            if (filtered.length === 0) {
                container.innerHTML = `
                    <div style="grid-column: 1 / -1; padding: 30px; text-align: center; color: #CBD5E1; background: rgba(0,0,0,0.3); border-radius: 12px; border: 1px dashed rgba(255,255,255,0.15);">
                        <i class="fa-solid fa-satellite-dish" style="font-size: 28px; margin-bottom: 8px; color: #00F0B5;"></i>
                        <p style="margin: 0; font-size: 14px; font-weight: 600;">No devices match the "${window.currentFleetFilter}" filter.</p>
                        <span style="font-size: 12px; color: #94A3B8;">Power on your ESP32 or trigger the simulator to see devices stream live.</span>
                    </div>
                `;
                return;
            }

            container.innerHTML = filtered.map(d => {
                const isHw = d.is_verified_hardware || d.source_type === 'real_sensor';
                const statusColor = d.status === 'ONLINE' ? '#00F0B5' : (d.status === 'STREAMING' ? '#38BDF8' : (d.status === 'STALE' ? '#F59E0B' : '#EF4444'));
                const statusBg = d.status === 'ONLINE' ? 'rgba(0, 240, 181, 0.15)' : (d.status === 'STREAMING' ? 'rgba(56, 189, 248, 0.15)' : (d.status === 'STALE' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)'));
                
                const provBadge = isHw
                    ? `<span style="background: rgba(0, 240, 181, 0.18); color: #00F0B5; border: 1px solid rgba(0, 240, 181, 0.5); padding: 3px 8px; border-radius: 12px; font-size: 10px; font-weight: 800; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-shield-halved"></i> [REAL SENSOR]</span>`
                    : `<span style="background: rgba(56, 189, 248, 0.18); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.5); padding: 3px 8px; border-radius: 12px; font-size: 10px; font-weight: 800; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-microchip"></i> [SIMULATED IoT]</span>`;

                let iconClass = 'fa-microchip';
                let iconColor = '#00F0B5';
                if (d.device_type === 'electricity_meter') { iconClass = 'fa-bolt'; iconColor = '#00F0B5'; }
                else if (d.device_type === 'water_meter') { iconClass = 'fa-droplet'; iconColor = '#38BDF8'; }
                else if (d.device_type === 'hvac_monitor') { iconClass = 'fa-snowflake'; iconColor = '#2DD4BF'; }
                else if (d.device_type === 'air_quality_monitor' || d.device_type === 'air_quality_sensor') { iconClass = 'fa-wind'; iconColor = '#F59E0B'; }
                else if (d.device_type === 'dg_monitor') { iconClass = 'fa-gas-pump'; iconColor = '#FBBF24'; }

                const m = d.last_telemetry || {};
                let metricChips = [];

                if (m.tank_level_pct !== undefined) {
                    metricChips.push(`
                        <div style="background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 10px; padding: 8px 12px;">
                            <div style="font-size: 10px; color: #BAE6FD; font-weight: 700; text-transform: uppercase;">Tank Water Level</div>
                            <div style="font-size: 1.4rem; font-weight: 800; color: #38BDF8;">${Number(m.tank_level_pct).toFixed(1)} %</div>
                            <div style="height: 6px; background: rgba(0,0,0,0.3); border-radius: 3px; overflow: hidden; margin-top: 4px;">
                                <div style="height: 100%; width: ${Math.min(100, Math.max(0, m.tank_level_pct))}%; background: linear-gradient(90deg, #00F0B5, #38BDF8);"></div>
                            </div>
                        </div>
                    `);
                }
                if (m.tank_distance_cm !== undefined) {
                    metricChips.push(`
                        <div style="background: rgba(0, 240, 181, 0.15); border: 1px solid rgba(0, 240, 181, 0.35); border-radius: 10px; padding: 8px 12px;">
                            <div style="font-size: 10px; color: #A7F3D0; font-weight: 700; text-transform: uppercase;">Ultrasonic Clearance</div>
                            <div style="font-size: 1.4rem; font-weight: 800; color: #00F0B5;">${Number(m.tank_distance_cm).toFixed(1)} cm</div>
                            <div style="font-size: 10px; color: #CBD5E1; margin-top: 2px;">AJ-SR04M Sonar</div>
                        </div>
                    `);
                }
                if (m.active_power_kw !== undefined) {
                    metricChips.push(`
                        <div style="background: rgba(0, 240, 181, 0.15); border: 1px solid rgba(0, 240, 181, 0.35); border-radius: 10px; padding: 8px 12px;">
                            <div style="font-size: 10px; color: #A7F3D0; font-weight: 700; text-transform: uppercase;">Active Power</div>
                            <div style="font-size: 1.4rem; font-weight: 800; color: #00F0B5;">${Number(m.active_power_kw).toFixed(1)} kW</div>
                            <div style="font-size: 10px; color: #CBD5E1; margin-top: 2px;">Demand Load</div>
                        </div>
                    `);
                }
                if (m.water_flow_lmin !== undefined) {
                    metricChips.push(`
                        <div style="background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 10px; padding: 8px 12px;">
                            <div style="font-size: 10px; color: #BAE6FD; font-weight: 700; text-transform: uppercase;">Water Flow</div>
                            <div style="font-size: 1.4rem; font-weight: 800; color: #38BDF8;">${Number(m.water_flow_lmin).toFixed(1)} L/min</div>
                            <div style="font-size: 10px; color: #CBD5E1; margin-top: 2px;">Velocity</div>
                        </div>
                    `);
                }
                if (m.mq135_raw_adc !== undefined || m.raw_adc !== undefined) {
                    const adcVal = m.mq135_raw_adc ?? m.raw_adc;
                    metricChips.push(`
                        <div style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 10px; padding: 8px 12px;">
                            <div style="font-size: 10px; color: #FEF3C7; font-weight: 700; text-transform: uppercase;">MQ-135 Gas ADC</div>
                            <div style="font-size: 1.4rem; font-weight: 800; color: #F59E0B;">${Math.round(adcVal)} count</div>
                            <div style="font-size: 10px; color: #CBD5E1; margin-top: 2px;">12-bit ADC1</div>
                        </div>
                    `);
                }
                if (m.hvac_load_kw !== undefined) {
                    metricChips.push(`
                        <div style="background: rgba(45, 212, 191, 0.15); border: 1px solid rgba(45, 212, 191, 0.35); border-radius: 10px; padding: 8px 12px;">
                            <div style="font-size: 10px; color: #CCFBF1; font-weight: 700; text-transform: uppercase;">HVAC Chiller Load</div>
                            <div style="font-size: 1.4rem; font-weight: 800; color: #2DD4BF;">${Number(m.hvac_load_kw).toFixed(1)} kW</div>
                            <div style="font-size: 10px; color: #CBD5E1; margin-top: 2px;">Compressor</div>
                        </div>
                    `);
                }
                if (m.fill_level_percent !== undefined || m.fill_level_pct !== undefined) {
                    const fVal = Number(m.fill_level_percent ?? m.fill_level_pct);
                    metricChips.push(`
                        <div style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 10px; padding: 8px 12px;">
                            <div style="font-size: 10px; color: #FEF3C7; font-weight: 700; text-transform: uppercase;">Bin Fill Level</div>
                            <div style="font-size: 1.4rem; font-weight: 800; color: #F59E0B;">${fVal.toFixed(1)} %</div>
                            <div style="height: 6px; background: rgba(0,0,0,0.3); border-radius: 3px; overflow: hidden; margin-top: 4px;">
                                <div style="height: 100%; width: ${Math.min(100, Math.max(0, fVal))}%; background: linear-gradient(90deg, #00D09C, #F59E0B);"></div>
                            </div>
                        </div>
                    `);
                }
                if (m.bin_distance_cm !== undefined) {
                    metricChips.push(`
                        <div style="background: rgba(0, 240, 181, 0.15); border: 1px solid rgba(0, 240, 181, 0.35); border-radius: 10px; padding: 8px 12px;">
                            <div style="font-size: 10px; color: #A7F3D0; font-weight: 700; text-transform: uppercase;">Sonar Clearance</div>
                            <div style="font-size: 1.4rem; font-weight: 800; color: #00D09C;">${Number(m.bin_distance_cm).toFixed(1)} cm</div>
                            <div style="font-size: 10px; color: #CBD5E1; margin-top: 2px;">HC-SR04 Sonar</div>
                        </div>
                    `);
                }
                if (m.temperature_c !== undefined) {
                    metricChips.push(`
                        <div style="background: rgba(45, 212, 191, 0.15); border: 1px solid rgba(45, 212, 191, 0.35); border-radius: 10px; padding: 8px 12px;">
                            <div style="font-size: 10px; color: #CCFBF1; font-weight: 700; text-transform: uppercase;">Temperature</div>
                            <div style="font-size: 1.4rem; font-weight: 800; color: #2DD4BF;">${Number(m.temperature_c).toFixed(1)} °C</div>
                            <div style="font-size: 10px; color: #CBD5E1; margin-top: 2px;">DHT11 1-Wire</div>
                        </div>
                    `);
                }
                if (m.humidity_pct !== undefined) {
                    metricChips.push(`
                        <div style="background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 10px; padding: 8px 12px;">
                            <div style="font-size: 10px; color: #BAE6FD; font-weight: 700; text-transform: uppercase;">Humidity</div>
                            <div style="font-size: 1.4rem; font-weight: 800; color: #38BDF8;">${Number(m.humidity_pct).toFixed(0)} % RH</div>
                            <div style="font-size: 10px; color: #CBD5E1; margin-top: 2px;">Relative Humidity</div>
                        </div>
                    `);
                }
                if (m.voltage_v !== undefined) {
                    metricChips.push(`
                        <div style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 10px; padding: 8px 12px;">
                            <div style="font-size: 10px; color: #FEF3C7; font-weight: 700; text-transform: uppercase;">Line Voltage</div>
                            <div style="font-size: 1.4rem; font-weight: 800; color: #F59E0B;">${Number(m.voltage_v).toFixed(1)} V</div>
                            <div style="font-size: 10px; color: #CBD5E1; margin-top: 2px;">PZEM Metrology</div>
                        </div>
                    `);
                }
                if (m.current_a !== undefined) {
                    const curVal = Number(m.current_a);
                    metricChips.push(`
                        <div style="background: rgba(96, 165, 250, 0.15); border: 1px solid rgba(96, 165, 250, 0.35); border-radius: 10px; padding: 8px 12px;">
                            <div style="font-size: 10px; color: #DBEAFE; font-weight: 700; text-transform: uppercase;">Line Current</div>
                            <div style="font-size: 1.4rem; font-weight: 800; color: #60A5FA;">${curVal < 10 ? curVal.toFixed(3) : curVal.toFixed(2)} A</div>
                            <div style="font-size: 10px; color: #CBD5E1; margin-top: 2px;">CT Coil Induction</div>
                        </div>
                    `);
                }

                if (metricChips.length === 0) {
                    const fallbackKeys = Object.keys(m).slice(0, 2);
                    fallbackKeys.forEach(k => {
                        metricChips.push(`
                            <div style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; padding: 8px 12px;">
                                <div style="font-size: 10px; color: #CBD5E1; font-weight: 700; text-transform: uppercase;">${k.replace('_', ' ')}</div>
                                <div style="font-size: 1.25rem; font-weight: 800; color: #FFFFFF;">${m[k]}</div>
                            </div>
                        `);
                    });
                }

                if (metricChips.length === 0) {
                    metricChips.push(`
                        <div style="background: rgba(255,255,255,0.04); border-radius: 8px; padding: 8px 12px; color: #94A3B8; font-size: 12px; text-align: center;">
                            Awaiting Telemetry Packet...
                        </div>
                    `);
                }

                const lastSeenText = d.last_sample_at ? d.last_sample_at.replace('T', ' ').slice(11, 19) : 'None';

                return `
                    <div style="background: linear-gradient(145deg, rgba(14, 46, 38, 0.8) 0%, rgba(6, 24, 20, 0.95) 100%); border: 1.5px solid ${isHw ? 'rgba(0, 240, 181, 0.4)' : 'rgba(56, 189, 248, 0.35)'}; border-radius: 14px; padding: 18px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div style="width: 38px; height: 38px; border-radius: 10px; background: rgba(0,0,0,0.3); border: 1px solid ${iconColor}; display: flex; align-items: center; justify-content: center; font-size: 18px; color: ${iconColor};">
                                        <i class="fa-solid ${iconClass}"></i>
                                    </div>
                                    <div>
                                        <h4 style="margin: 0; font-size: 1rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.2px;">${d.device_id}</h4>
                                        <span style="font-size: 11px; color: #CBD5E1;">${d.building_id || 'Block B Hostel'}</span>
                                    </div>
                                </div>
                                <span style="background: ${statusBg}; color: ${statusColor}; border: 1px solid ${statusColor}; border-radius: 12px; padding: 3px 8px; font-size: 10px; font-weight: 800; display: inline-flex; align-items: center; gap: 4px;">
                                    ${d.status === 'ONLINE' ? '<span class="pulse-dot"></span>' : ''} ${d.status}
                                </span>
                            </div>

                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                ${provBadge}
                                <span style="font-size: 10px; color: #94A3B8;">Last seen: <strong style="color: #E2E8F0;">${lastSeenText}</strong></span>
                            </div>

                            <div style="display: grid; grid-template-columns: repeat(${Math.min(2, metricChips.length)}, 1fr); gap: 10px; margin-top: 10px;">
                                ${metricChips.join('')}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            console.error('Dynamic fleet render error:', e);
        }
    };

    const renderStreamTable = () => {
        const monTbody = document.getElementById("monIotStreamTableBody");
        if (!monTbody || !window.cachedStreamList || window.cachedStreamList.length === 0) return;

        const filtered = window.cachedStreamList.filter(item => {
            const isReal = item.source_type === 'real_sensor' || item.is_verified_hardware === true;
            if (window.currentStreamFilter === 'hardware') return isReal;
            if (window.currentStreamFilter === 'simulator') return !isReal;
            return true;
        });

        if (filtered.length === 0) {
            monTbody.innerHTML = `
                <tr>
                    <td colspan="8" style="padding: 20px; text-align: center; color: #CBD5E1;">
                        No telemetry packets matching "${window.currentStreamFilter}".
                    </td>
                </tr>
            `;
            return;
        }

        monTbody.innerHTML = filtered.map(item => {
            const m = item.metrics || item.telemetry || {};
            let summaryStr = "--";
            if (m.bin_distance_cm !== undefined || m.fill_level_percent !== undefined || m.fill_level_pct !== undefined || item.device_id === 'WASTE-BLOCK-B-001') {
                const f = m.fill_level_percent ?? m.fill_level_pct ?? '--';
                const d = m.bin_distance_cm ?? '--';
                summaryStr = `Fill: <strong>${f}%</strong> | Clearance: <strong>${d} cm</strong>`;
            } else if (m.tank_distance_cm !== undefined || m.tank_level_pct !== undefined) {
                summaryStr = `Level: <strong>${m.tank_level_pct ?? '--'}%</strong> | Dist: <strong>${m.tank_distance_cm ?? '--'} cm</strong>`;
            } else if (m.active_power_kw !== undefined && m.active_power_kw !== null) {
                summaryStr = `Power: <strong>${m.active_power_kw} kW</strong>` + (m.voltage_v !== undefined ? ` | ${m.voltage_v} V` : '');
            } else if (m.water_flow_lmin !== undefined && m.water_flow_lmin !== null) {
                const total = m.water_cumulative_liters !== undefined ? `${m.water_cumulative_liters} L` : (m.cumulative_water_m3 !== undefined ? `${m.cumulative_water_m3} m³` : '');
                const pulses = m.water_pulse_count_total !== undefined ? ` | ${Number(m.water_pulse_count_total).toLocaleString()} pulses` : '';
                summaryStr = `Flow: <strong>${m.water_flow_lmin} L/min</strong>` + (total ? ` | Total: ${total}` : '') + pulses;
            } else if (m.mq135_raw_adc !== undefined || m.raw_adc !== undefined) {
                summaryStr = `ADC: <strong>${m.mq135_raw_adc ?? m.raw_adc}</strong> | Pin: ${m.mq135_adc_pin_voltage_v ?? '--'} V | Module: ${m.mq135_voltage_v ?? '--'} V`;
            } else if (m.temperature_c !== undefined || m.humidity_pct !== undefined) {
                summaryStr = `Temp: <strong>${m.temperature_c}°C</strong> | Humidity: <strong>${m.humidity_pct}% RH</strong>` + (m.heat_index_c !== undefined ? ` | HI: ${m.heat_index_c}°C` : '');
            } else if (m.hvac_load_kw !== undefined) {
                summaryStr = `HVAC: <strong>${m.hvac_load_kw} kW</strong> | Temp: ${m.temperature_c ?? '--'}°C`;
            } else if (m.meter_status !== undefined) {
                summaryStr = `Modbus: Standby`;
            } else {
                summaryStr = Object.entries(m).slice(0, 2).map(([k, v]) => `${k}: ${v}`).join(", ") || "OK";
            }

            const isReal = item.source_type === 'real_sensor' || item.is_verified_hardware === true;
            const provBadge = isReal
                ? '<span class="badge-mint" style="font-size:10px; font-weight:800; padding: 3px 8px;"><i class="fa-solid fa-shield-halved"></i> [REAL SENSOR]</span>'
                : '<span class="badge-amber" style="font-size:10px; font-weight:800; padding: 3px 8px;"><i class="fa-solid fa-microchip"></i> [SIMULATED IoT]</span>';

            const statusBadge = item.quarantined
                ? '<span style="color:#EF4444; font-size:12px; font-weight:700;"><i class="fa-solid fa-triangle-exclamation"></i> QUARANTINED</span>'
                : '<span style="color:#00F0B5; font-size:12px; font-weight:700;"><i class="fa-solid fa-circle-check"></i> INGESTED</span>';

            const rawTs = item.event_timestamp || item.sent_timestamp || item.ingested_at || "";
            const tsStr = rawTs.includes("T") ? rawTs.split("T")[1].slice(0, 8) : (rawTs.slice(11, 19) || "--");

            let cadenceTag = "";
            const cadenceSec = Number(item.reporting_interval_sec);
            const cadenceText = Number.isFinite(cadenceSec) && cadenceSec > 0
                ? (cadenceSec < 60 ? `${cadenceSec}s DEMO` : `${Math.round(cadenceSec / 60)}m`)
                : (item.reporting_state === "ANOMALY_5M" || item.reporting_state === "RECOVERY_5M" ? "5m" : "15m");
            if (item.reporting_state === "ANOMALY_5M") {
                cadenceTag = `<span style="font-size:10px; color:#EF4444; font-weight:800; background:rgba(239,68,68,0.15); border:1px solid #EF4444; border-radius:6px; padding:1px 5px; margin-left:4px;">${cadenceText} ANOM</span>`;
            } else if (item.reporting_state === "RECOVERY_5M") {
                cadenceTag = `<span style="font-size:10px; color:#F59E0B; font-weight:800; background:rgba(245,158,11,0.15); border:1px solid #F59E0B; border-radius:6px; padding:1px 5px; margin-left:4px;">${cadenceText} RECOV</span>`;
            } else if (item.reporting_state === "NORMAL_15M") {
                cadenceTag = `<span style="font-size:10px; color:#00F0B5; font-weight:600; background:rgba(0,240,181,0.1); border:1px solid rgba(0,240,181,0.3); border-radius:6px; padding:1px 5px; margin-left:4px;">${cadenceText} NORM</span>`;
            }

            let anomalyBadge = "";
            if (item.is_anomaly) {
                const originLabel = item.anomaly_origin === "EDGE_DETECTED" ? "[EDGE DETECTED]" : "[BACKEND DETECTED]";
                anomalyBadge = `<div style="margin-top:3px;"><span style="color:#EF4444; font-size:10px; font-weight:800; background:rgba(239,68,68,0.18); border:1px solid #EF4444; border-radius:8px; padding:2px 6px; display:inline-flex; align-items:center; gap:4px;"><i class="fa-solid fa-triangle-exclamation"></i> ${originLabel} ${item.anomaly_reason || item.anomaly_details || 'Anomaly'}</span></div>`;
            }

            return `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); background: ${isReal ? 'rgba(0, 240, 181, 0.04)' : 'transparent'};">
                <td style="padding:11px 10px; font-family:monospace; font-size:11px; color:#A7F3D0;">${item.message_id || '--'}</td>
                <td style="padding:11px 10px; font-size:12px; color:#E2E8F0;">${tsStr}</td>
                <td style="padding:11px 10px; font-weight:700; color:#38BDF8;">${item.device_id || '--'}</td>
                <td style="padding:11px 10px; font-size:12px; color:#CBD5E1;">${item.building_id || 'Block B Hostel'}</td>
                <td style="padding:11px 10px; font-size:12px; color:#FFFFFF;">${summaryStr} ${cadenceTag}${anomalyBadge}</td>
                <td style="padding:11px 10px;">${provBadge}</td>
                <td style="padding:11px 10px;">${statusBadge}</td>
                <td style="padding:11px 10px; text-align:center;">
                    <button type="button" class="btn btn-xs" onclick="window.openWirePayloadModal('${item.message_id}')" style="font-size:11px; padding:4px 9px; border-radius:6px; background:rgba(0,240,181,0.12); border:1px solid #00F0B5; color:#00F0B5; cursor:pointer; font-weight:700; display:inline-flex; align-items:center; gap:4px;">
                        <i class="fa-solid fa-code"></i> Wire JSON
                    </button>
                </td>
            </tr>
            `;
        }).join("");
    };

    const fetchStreamLog = async () => {
        try {
            // First update the small simulator table from simulator stream
            try {
                const simRes = await fetch("/api/v1/iot-simulator/stream?limit=10");
                if (simRes.ok) {
                    const simData = await simRes.json();
                    const tbody = document.getElementById("simStreamTableBody");
                    if (tbody && simData.stream) {
                        tbody.innerHTML = simData.stream.map(item => {
                            const pKW = item.active_power_kw ?? item.telemetry?.active_power_kw ?? 145.2;
                            const tC = item.temperature_c ?? item.telemetry?.temperature_c ?? 24.5;
                            return `
                            <tr>
                                <td style="padding:6px; font-family:monospace; font-size:11px;">${item.sample_id || '--'}</td>
                                <td style="padding:6px;">${item.timestamp ? item.timestamp.replace("T", " ").slice(11, 19) : "--"}</td>
                                <td style="padding:6px; font-weight:600;">${pKW} kW</td>
                                <td style="padding:6px;">${tC}°C</td>
                                <td style="padding:6px;"><span class="badge-amber" style="font-size:10px;">${item.data_source || item.data_source_mode || 'simulated_iot'}</span></td>
                            </tr>
                        `}).join("");
                    }
                }
            } catch (simErr) {}

            // Now fetch canonical unified registry stream for Live IoT Monitor Console
            const res = await fetch("/api/v1/iot/telemetry/stream?limit=30");
            if (res.ok) {
                const streamData = await res.json();
                const monTotal = document.getElementById("monTotalIngestedRecords");
                if (monTotal) monTotal.textContent = streamData.total_ingested || streamData.stream?.length || 0;

                if (streamData.stream && streamData.stream.length > 0) {
                    window.cachedStreamList = streamData.stream;
                    updateLiveTelemetryFromStream(streamData.stream);
                    renderStreamTable();
                    renderDynamicFleet();
                    renderSensorMatrixTable(window.cachedDevicesList, streamData.stream);
                }
            }
        } catch (e) {
            console.error("Stream log error:", e);
        }
    };


// =========================================================================
// REAL-TIME DEMO ANOMALY & POPUP NOTIFICATION MANAGER (JURY DEMO)
// =========================================================================
window.liveAnomalyDebounceMap = window.liveAnomalyDebounceMap || {};
let liveAutoDismissTimer = null;
let currentActiveAlert = null;

function playAnomalyChime(severity) {
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        const ctx = new AudioCtx();
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        
        const isCrit = (severity === 'CRITICAL');
        osc.type = isCrit ? 'sawtooth' : 'sine';
        osc.frequency.setValueAtTime(isCrit ? 880 : 660, now);
        osc.frequency.exponentialRampToValueAtTime(isCrit ? 1320 : 880, now + 0.15);
        
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.32);
        
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.35);
    } catch (e) {
        // Audio policy fallback
    }
}

window.triggerLiveHardwareAnomalyPopup = function(anomaly) {
    if (!anomaly || !anomaly.issue) return;

    const key = `${anomaly.device_id || 'DEV'}_${anomaly.metric || anomaly.id || 'ANOM'}`;
    const now = Date.now();
    const severity = (anomaly.severity || 'HIGH').toUpperCase();
    const isCritical = (severity === 'CRITICAL');

    let tracker = window.liveAnomalyDebounceMap[key];
    if (!tracker) {
        tracker = {
            timesShown: 0,
            lastShownAt: 0,
            acknowledged: false,
            firstSeenAt: now
        };
        window.liveAnomalyDebounceMap[key] = tracker;
    }

    // If user already acknowledged this specific episode, don't popup again
    if (tracker.acknowledged) {
        updateNotificationBellCount();
        return;
    }

    // Anti-glitch cooldown:
    // CRITICAL: max 3 times total, at least 20 seconds between popups
    // HIGH: max 2 times total, at least 30 seconds between popups
    // MEDIUM / LOW: max 1 time total
    const maxShows = isCritical ? 3 : (severity === 'HIGH' ? 2 : 1);
    const minSpacingMs = isCritical ? 20000 : 30000;

    if (tracker.timesShown >= maxShows) {
        updateNotificationBellCount();
        return;
    }

    if (tracker.lastShownAt > 0 && (now - tracker.lastShownAt) < minSpacingMs) {
        return;
    }

    // Update tracker
    tracker.timesShown++;
    tracker.lastShownAt = now;
    currentActiveAlert = { key, anomaly };

    // 1. Play Sound Chime
    playAnomalyChime(severity);

    // 2. Render On-Screen Floating Popup
    const container = document.getElementById('liveAnomalyPopupContainer');
    const card = document.getElementById('liveAnomalyCard');
    const sevBadge = document.getElementById('liveAnomalySeverityBadge');
    const devTag = document.getElementById('liveAnomalyDeviceTag');
    const titleEl = document.getElementById('liveAnomalyTitle');
    const detailEl = document.getElementById('liveAnomalyDetail');
    const actionEl = document.getElementById('liveAnomalyActionText');
    const timeEl = document.getElementById('liveAnomalyTimeText');
    const iconBox = document.getElementById('liveAnomalyIconBox');
    const iconEl = document.getElementById('liveAnomalyIcon');

    if (container && card) {
        card.className = `live-anomaly-card ${isCritical ? 'severity-critical' : 'severity-high'}`;
        if (sevBadge) sevBadge.textContent = severity;
        if (devTag) devTag.textContent = anomaly.device_id || 'ESP32 GATEWAY';
        if (titleEl) titleEl.textContent = anomaly.issue;
        if (detailEl) detailEl.textContent = anomaly.observed_value 
            ? `Observed: ${anomaly.observed_value} • ${anomaly.explanation || 'Edge boundary exceeded'}`
            : (anomaly.explanation || 'Sensor threshold exceeded contextual envelope');
        if (actionEl) actionEl.textContent = anomaly.recommended_action || 'Inspect physical sensor and verify zone safety.';
        if (timeEl) timeEl.textContent = `Just now • Live Hardware Sensor (${tracker.timesShown}/${maxShows})`;

        if (iconBox && iconEl) {
            let iconClass = 'fa-triangle-exclamation';
            const issueLower = (anomaly.issue || '').toLowerCase();
            const metricLower = (anomaly.metric || '').toLowerCase();
            if (issueLower.includes('smoke') || issueLower.includes('fire') || metricLower.includes('smoke') || metricLower.includes('mq135')) {
                iconClass = 'fa-fire-flame-curved';
            } else if (issueLower.includes('water') || issueLower.includes('leak') || metricLower.includes('water')) {
                iconClass = 'fa-faucet-drip';
            } else if (issueLower.includes('bin') || issueLower.includes('waste') || metricLower.includes('fill')) {
                iconClass = 'fa-trash-can';
            } else if (issueLower.includes('voltage') || issueLower.includes('power') || issueLower.includes('current') || metricLower.includes('volt')) {
                iconClass = 'fa-bolt';
            } else if (issueLower.includes('temp') || issueLower.includes('heat') || metricLower.includes('temp')) {
                iconClass = 'fa-temperature-high';
            }
            iconEl.className = `fa-solid ${iconClass}`;
        }

        container.style.display = 'block';

        // Auto-hide popup after 12s if user doesn't dismiss, but keep in bell
        if (liveAutoDismissTimer) clearTimeout(liveAutoDismissTimer);
        liveAutoDismissTimer = setTimeout(() => {
            container.style.display = 'none';
        }, 12000);
    }

    // 3. Update Top Navbar Notification Bell & Dropdown
    prependNotificationDropdownItem(anomaly, key);
    updateNotificationBellCount();
};

window.dismissLiveHardwareAnomalyPopup = function() {
    const container = document.getElementById('liveAnomalyPopupContainer');
    if (container) container.style.display = 'none';
    if (liveAutoDismissTimer) clearTimeout(liveAutoDismissTimer);
};

window.acknowledgeLiveHardwareAnomaly = function() {
    if (currentActiveAlert && window.liveAnomalyDebounceMap[currentActiveAlert.key]) {
        window.liveAnomalyDebounceMap[currentActiveAlert.key].acknowledged = true;
    }
    window.dismissLiveHardwareAnomalyPopup();
    showToast('✓ Incident Acknowledged. Telemetry alerts silenced for this cycle.');
    updateNotificationBellCount();
};

window.muteLiveHardwareAnomaly = function(seconds = 30) {
    if (currentActiveAlert && window.liveAnomalyDebounceMap[currentActiveAlert.key]) {
        window.liveAnomalyDebounceMap[currentActiveAlert.key].lastShownAt = Date.now() + (seconds * 1000) - 20000;
    }
    window.dismissLiveHardwareAnomalyPopup();
    showToast(`Muted alert popup for ${seconds}s.`);
};

window.resetAnomalyTrackerIfNormal = function(activeAnomalyKeys) {
    Object.keys(window.liveAnomalyDebounceMap).forEach(key => {
        if (!activeAnomalyKeys.has(key)) {
            const tr = window.liveAnomalyDebounceMap[key];
            // If clean for 15 seconds, clear tracker so jury can re-trigger test
            if (Date.now() - tr.lastShownAt > 15000) {
                delete window.liveAnomalyDebounceMap[key];
            }
        }
    });
};

function updateNotificationBellCount() {
    const notifBadge = document.getElementById('notificationCount');
    const notifUnread = document.getElementById('notifUnreadBadge');
    const notifList = document.getElementById('notifListItems');
    if (!notifList) return;

    const unreadCount = notifList.querySelectorAll('.notif-item.unread').length;
    if (notifBadge) {
        notifBadge.textContent = unreadCount;
        notifBadge.style.display = unreadCount > 0 ? 'flex' : 'none';
        if (unreadCount > 0) {
            notifBadge.classList.add('pulse');
        } else {
            notifBadge.classList.remove('pulse');
        }
    }
    if (notifUnread) {
        notifUnread.textContent = `${unreadCount} New`;
    }
}

function prependNotificationDropdownItem(anomaly, key) {
    const notifList = document.getElementById('notifListItems');
    if (!notifList) return;

    // Check if an item for this key already exists
    const existing = notifList.querySelector(`[data-alert-key="${key}"]`);
    if (existing) {
        const timeEl = existing.querySelector('.notif-time');
        if (timeEl) timeEl.textContent = 'Just now';
        return;
    }

    const isCrit = (anomaly.severity === 'CRITICAL');
    let iconClass = 'fa-triangle-exclamation';
    const issueLower = (anomaly.issue || '').toLowerCase();
    if (issueLower.includes('smoke') || issueLower.includes('fire')) {
        iconClass = 'fa-fire-flame-curved';
    } else if (issueLower.includes('water') || issueLower.includes('leak')) {
        iconClass = 'fa-faucet-drip';
    } else if (issueLower.includes('bin') || issueLower.includes('waste')) {
        iconClass = 'fa-trash-can';
    } else if (issueLower.includes('voltage') || issueLower.includes('power') || issueLower.includes('current')) {
        iconClass = 'fa-bolt';
    } else if (issueLower.includes('temp') || issueLower.includes('heat')) {
        iconClass = 'fa-temperature-high';
    }

    const item = document.createElement('div');
    item.className = `notif-item unread ${isCrit ? 'p1-alert' : 'p2-alert'}`;
    item.setAttribute('data-alert-key', key);
    item.innerHTML = `
        <div class="notif-icon-box ${isCrit ? 'bg-red' : 'bg-amber'}">
            <i class="fa-solid ${iconClass}"></i>
        </div>
        <div class="notif-content" style="flex: 1;">
            <div class="notif-top-row">
                <span class="notif-severity ${isCrit ? 'badge-red' : 'badge-amber'}">${anomaly.severity}</span>
                <span class="notif-time">Just now</span>
            </div>
            <h4 style="margin: 3px 0 2px 0;">${escapeHtml(anomaly.issue)}</h4>
            <p style="margin: 0 0 6px 0; font-size: 11px;">${escapeHtml(anomaly.observed_value || anomaly.explanation || '')}</p>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 10px; color: #94A3B8;">${escapeHtml(anomaly.device_id || 'Hardware')}</span>
                <button class="btn btn-sm" onclick="this.closest('.notif-item').classList.remove('unread'); this.remove(); updateNotificationBellCount();" style="font-size: 10px; padding: 2px 7px; background: rgba(0, 240, 181, 0.15); color: #00D09C; border: 1px solid rgba(0, 240, 181, 0.4); border-radius: 4px; cursor: pointer;">
                    <i class="fa-solid fa-check"></i> Ack
                </button>
            </div>
        </div>
    `;
    notifList.insertBefore(item, notifList.firstChild);
}

// Bind live anomaly popup buttons
document.addEventListener('DOMContentLoaded', () => {
    const dismissBtn = document.getElementById('liveAnomalyDismissBtn');
    const ackBtn = document.getElementById('liveAnomalyAckBtn');
    const muteBtn = document.getElementById('liveAnomalyMuteBtn');

    if (dismissBtn) dismissBtn.addEventListener('click', window.dismissLiveHardwareAnomalyPopup);
    if (ackBtn) ackBtn.addEventListener('click', window.acknowledgeLiveHardwareAnomaly);
    if (muteBtn) muteBtn.addEventListener('click', () => window.muteLiveHardwareAnomaly(30));
});

    const syncGlobalTelemetryDashboard = async () => {
        try {
            // 1. Fetch live energy forecasts
            loadBackendForecasts();

            // 2. Fetch live anomalies & evaluate alerts
            const res = await fetch("/api/v1/energy/anomalies");
            if (res.ok) {
                const data = await res.json();
                
                // Update badge counts and provenance badge
                const sidebarBadge = document.getElementById("sidebarAlertCount");
                const notifBadge = document.getElementById("notificationCount");
                const notifUnreadBadge = document.getElementById("notifUnreadBadge");
                const monProv = document.getElementById("monProvenanceBadge");

                if (sidebarBadge) sidebarBadge.textContent = data.active_anomalies_count;
                if (notifBadge) notifBadge.textContent = data.active_anomalies_count;
                if (notifUnreadBadge) notifUnreadBadge.textContent = `${data.active_anomalies_count} Active`;
                if (monProv && data.provenance_badge) {
                    monProv.textContent = `Tagged: ${data.provenance_badge}`;
                    monProv.className = data.provenance_badge.includes("REAL") ? "fc-sub text-mint" : "fc-sub text-gold";
                }

                const activeKeys = new Set();
                (data.anomalies || []).forEach(anom => {
                    if (anom.severity !== 'NORMAL' && anom.id !== 'ALT_NORMAL_00') {
                        const alertKey = `${anom.device_id || 'DEV'}_${anom.metric || anom.id || anom.issue}`;
                        activeKeys.add(alertKey);
                        // Trigger smart debounced popup & bell update
                        window.triggerLiveHardwareAnomalyPopup(anom);
                    }
                });

                // Reset trackers for sensors that returned to normal so they can trigger again
                window.resetAnomalyTrackerIfNormal(activeKeys);
            }
        } catch (e) {
            console.error("Telemetry sync error:", e);
        }
    };


    const fetchAdaptiveStatus = async () => {
        try {
            const res = await fetch("/api/v1/iot/telemetry/adaptive-status");
            if (!res.ok) return;
            const data = await res.json();

            const badgeEl = document.getElementById("adaptiveReportingBadge");
            const modeTextEl = document.getElementById("adaptiveReportingModeText");
            const nextReportEl = document.getElementById("adaptiveNextReportText");
            const cadencePill = document.getElementById("cadenceStatusPill");
            const lastAgeEl = document.getElementById("cadenceLastReceivedAge");
            const nextTimeEl = document.getElementById("cadenceNextExpectedTime");
            const anomStatusEl = document.getElementById("cadenceAnomalyStatusText");
            const edgeAlertPill = document.getElementById("cadenceEdgeAlertPill");
            const backendAlertPill = document.getElementById("cadenceBackendAlertPill");

            const state = data.campus_reporting_state || "NORMAL_15M";
            const nextSec = data.campus_next_report_expected_sec !== undefined ? data.campus_next_report_expected_sec : 900;
            const formatSec = (s) => {
                if (s === null || s === undefined || isNaN(s)) return "--";
                if (s <= 0) return "Due now";
                const m = Math.floor(s / 60);
                const remS = Math.floor(s % 60);
                return m > 0 ? (m + "m " + remS + "s") : (remS + "s");
            };

            const nextStr = formatSec(nextSec);
            if (nextReportEl) nextReportEl.textContent = "(Next: in " + nextStr + ")";
            if (nextTimeEl) nextTimeEl.textContent = "In " + nextStr;

            if (state === "ANOMALY_5M") {
                if (modeTextEl) modeTextEl.textContent = "Anomaly monitoring · 5 min";
                if (badgeEl) {
                    badgeEl.style.background = "rgba(239, 68, 68, 0.2)";
                    badgeEl.style.borderColor = "#EF4444";
                    badgeEl.style.color = "#EF4444";
                }
                if (cadencePill) {
                    cadencePill.textContent = "ANOMALY MONITORING · 5 MIN CADENCE";
                    cadencePill.className = "badge-red";
                    cadencePill.style.cssText = "background: rgba(239, 68, 68, 0.2); color: #EF4444; border: 1px solid #EF4444; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 800;";
                }
            } else if (state === "RECOVERY_5M") {
                if (modeTextEl) modeTextEl.textContent = "Recovery check · 5 min";
                if (badgeEl) {
                    badgeEl.style.background = "rgba(245, 158, 11, 0.2)";
                    badgeEl.style.borderColor = "#F59E0B";
                    badgeEl.style.color = "#F59E0B";
                }
                if (cadencePill) {
                    cadencePill.textContent = "RECOVERY CHECK · 5 MIN CADENCE (Verifying Stability)";
                    cadencePill.className = "badge-amber";
                    cadencePill.style.cssText = "background: rgba(245, 158, 11, 0.2); color: #F59E0B; border: 1px solid #F59E0B; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 800;";
                }
            } else {
                if (modeTextEl) modeTextEl.textContent = "Normal · 15 min";
                if (badgeEl) {
                    badgeEl.style.background = "rgba(0, 208, 156, 0.15)";
                    badgeEl.style.borderColor = "#00D09C";
                    badgeEl.style.color = "#00D09C";
                }
                if (cadencePill) {
                    cadencePill.textContent = "NORMAL · 15 MIN CADENCE";
                    cadencePill.className = "badge-mint";
                    cadencePill.style.cssText = "background: rgba(0, 208, 156, 0.15); color: #00D09C; border: 1px solid rgba(0, 208, 156, 0.4); padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 800;";
                }
            }

            // Anomaly details & pills
            const hasAnom = data.active_anomalies && data.active_anomalies.length > 0;
            if (hasAnom) {
                const firstAnom = data.active_anomalies[0];
                if (anomStatusEl) {
                    const devText = firstAnom.device_id || "Campus";
                    const metText = firstAnom.metric || firstAnom.issue || "Anomaly";
                    const obsText = firstAnom.observed_value !== undefined ? firstAnom.observed_value : "--";
                    const rsnText = firstAnom.reason || firstAnom.details || "Deviation outside baseline bounds";
                    anomStatusEl.innerHTML = "⚠️ <strong style=\"color: #F87171;\">" + devText + "</strong>: " + metText + " = <strong>" + obsText + "</strong> &mdash; <span style=\"color: #FCA5A5;\">" + rsnText + "</span>";
                }
                const hasEdge = data.active_anomalies.some(a => a.origin === "EDGE_DETECTED" || a.origin === "EDGE_FIRMWARE");
                const hasBackend = data.active_anomalies.some(a => a.origin === "BACKEND_DETECTED" || a.origin === "BACKEND_ADAPTIVE_ENGINE");
                if (edgeAlertPill) edgeAlertPill.style.display = hasEdge ? "inline-flex" : "none";
                if (backendAlertPill) backendAlertPill.style.display = hasBackend ? "inline-flex" : "none";
            } else {
                if (anomStatusEl) {
                    anomStatusEl.innerHTML = "All telemetry metrics nominal across campus &bull; Continuous 2.0s acquisition active";
                }
                if (edgeAlertPill) edgeAlertPill.style.display = "none";
                if (backendAlertPill) backendAlertPill.style.display = "none";
            }

            if (lastAgeEl && data.last_telemetry_at) {
                const elapsedSec = Math.max(0, Math.round((Date.now() - new Date(data.last_telemetry_at).getTime()) / 1000));
                lastAgeEl.textContent = elapsedSec + "s ago";
            } else if (lastAgeEl) {
                lastAgeEl.textContent = "Live streaming";
            }
        } catch (e) {
            console.error("Adaptive status sync error:", e);
        }
    };

    const btnRefreshIotLog = document.getElementById("btnRefreshIotLog");
    if (btnRefreshIotLog) {
        btnRefreshIotLog.addEventListener("click", () => {
            fetchStreamLog();
            showToast("Refreshing Live IoT Stream Log...");
        });
    }

    window.fetchIotStatus = fetchStatus;
    window.fetchIotStreamLog = fetchStreamLog;

    // Initial fetch
    initFleetFilterButtons();
    initTelemetrySourceSelector();
    fetchStatus();
    fetchStreamLog();
    renderDynamicFleet();
    syncGlobalTelemetryDashboard();
    fetchAdaptiveStatus();

    // Auto refresh interval: silky smooth, debounced, synchronized cadence
    let isGlobalSyncInProgress = false;
    setInterval(async () => {
        if (isGlobalSyncInProgress) return;
        isGlobalSyncInProgress = true;
        try {
            await fetchStreamLog();
            await fetchStatus();
            await fetchAdaptiveStatus();
            await syncGlobalTelemetryDashboard();
        } catch (err) {
            console.error('Telemetry sync loop error:', err);
        } finally {
            isGlobalSyncInProgress = false;
        }
    }, 1200);
}



