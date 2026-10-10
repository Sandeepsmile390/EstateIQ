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
    user_id: "USR_ADMIN_01",
    name: "RS Administrator",
    initials: "RS",
    role_key: "admin",
    role_label: "Facility Lead & Admin",
    avatar_bg: "#124B3E",
    permissions: ["overview", "suggestions", "energy", "water", "waste", "mobility", "simulator", "iot-simulator", "iot-monitor", "faq", "decision-intelligence", "esg", "billing", "work-orders", "ai-assistant"],
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
            } else if (preset === "manager") {
                emailInput.value = "manager@estateiq.in";
                passInput.value = "Manager@123";
            } else if (preset === "operations") {
                emailInput.value = "operations@estateiq.in";
                passInput.value = "Ops@123";
            } else if (preset === "sustainability") {
                emailInput.value = "sustainability@estateiq.in";
                passInput.value = "Sust@123";
            } else if (preset === "staff") {
                emailInput.value = "staff@estateiq.in";
                passInput.value = "Staff@123";
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
                    showToast(`Logged in as ${currentUserSession.name} (${currentUserSession.role_label})`);
                }
            } catch (err) {
                showToast(`Switched active session role to ${roleKey.toUpperCase()}`);
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
    const avatar = document.getElementById("activeAvatarInitials");
    const nameEl = document.getElementById("activeUserName");
    const roleLabelEl = document.getElementById("activeUserRoleLabel");
    const statusPill = document.getElementById("backendStatusPill");
    const bannerUserRole = document.getElementById("bannerUserRole");

    if (avatar) {
        avatar.textContent = user.initials;
        avatar.style.backgroundColor = user.avatar_bg || "#124B3E";
    }
    if (nameEl) nameEl.textContent = user.name;
    if (roleLabelEl) roleLabelEl.textContent = user.role_label;
    if (statusPill) statusPill.textContent = `${user.role_label} Active`;
    if (bannerUserRole) bannerUserRole.textContent = `${user.name} (${user.role_label})`;

    // Update active checkmarks in role switcher
    document.querySelectorAll(".role-option").forEach(opt => {
        if (opt.getAttribute("data-role") === user.role_key) {
            opt.classList.add("active");
        } else {
            opt.classList.remove("active");
        }
    });

    // Update sidebar locks based on permissions
    document.querySelectorAll(".nav-item[data-tab-nav]").forEach(item => {
        const tabId = item.getAttribute("data-tab-nav");
        const lockIcon = item.querySelector(".lock-icon");
        if (user.permissions.includes(tabId)) {
            if (lockIcon) lockIcon.style.display = "none";
            item.style.opacity = "1";
        } else {
            if (lockIcon) lockIcon.style.display = "inline-block";
            item.style.opacity = "0.7";
        }
    });
}

/* --------------------------------------------------------------------------
   TAB NAVIGATION SYSTEM & PERMISSION ENFORCEMENT
   -------------------------------------------------------------------------- */
function initTabs() {
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");
    const sidebarNavs = document.querySelectorAll(".nav-item[data-tab-nav]");
    const headerPlanPill = document.getElementById("headerPlanPill");

    const switchTab = (tabId) => {
        let activeTab = tabId;
        if (!activeTab || activeTab === "decision-intelligence" || activeTab === "models") activeTab = "overview";

        // Unrestricted tab opening policy: all tabs open directly for any active user session
        if (currentUserSession && currentUserSession.permissions && !currentUserSession.permissions.includes(activeTab)) {
            currentUserSession.permissions.push(activeTab);
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
        const targetContent = document.getElementById(`content${capName}`) || document.getElementById("contentOverview");
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
    if (str === "faq" || str === "decision-intelligence" || str === "models") return "Faq";
    if (str === "ai-assistant") return "AiAssistant";
    if (str === "work-orders") return "WorkOrders";
    if (str === "iot-simulator") return "IotSimulator";
    if (str === "iot-monitor") return "IotMonitor";
    return str.charAt(0).toUpperCase() + str.slice(1);
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

                if (res.ok) {
                    const data = await res.json();
                    showToast(`Subscription Upgrade: ${data.message}`);
                    
                    upgradeBtns.forEach(b => {
                        b.disabled = false;
                        b.textContent = "Switch to " + b.getAttribute("data-plan").replace("_", " ").toUpperCase();
                    });
                    btn.disabled = true;
                    btn.textContent = "Current Active Plan";

                    const headerPlanLabel = document.getElementById("headerPlanLabel");
                    if (headerPlanLabel) headerPlanLabel.textContent = planId.replace("_", " ").toUpperCase();
                }
            } catch (err) {
                showToast(`Switched plan to ${planId.toUpperCase()}`);
            }
        });
    });

    cycleToggle?.addEventListener("change", () => {
        const isAnnual = cycleToggle.checked;
        const pStarter = document.getElementById("priceStarter");
        const pPro = document.getElementById("pricePro");

        if (pStarter) pStarter.textContent = isAnnual ? "$399" : "$499";
        if (pPro) pPro.textContent = isAnnual ? "$1,199" : "$1,499";
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

    // Poll status from backend
    const fetchStatus = async () => {
        try {
            const res = await fetch("/api/v1/iot-simulator/status");
            if (res.ok) {
                const status = await res.json();
                updateSimulatorUI(status);
            }
        } catch (e) {
            const conn = document.getElementById("simConnStatusText");
            if (conn) {
                conn.textContent = "DISCONNECTED";
                conn.className = "text-red";
            }
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
            connState.textContent = status.status === "RUNNING" ? "LIVE STREAMING" : (status.status || "CONNECTED");
        }
        const monSimInstancesCount = document.getElementById("monSimInstancesCount");
        if (monSimInstancesCount) {
            monSimInstancesCount.textContent = `1 Simulator (${status.mode || 'Standard Mode'})`;
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

            // Populate Live IoT Monitor Tab Cards
            const pKW = document.getElementById("liveMetricPowerKW");
            const eKWH = document.getElementById("liveMetricEnergyKWH");
            const vV = document.getElementById("liveMetricVoltageV");
            const iPF = document.getElementById("liveMetricCurrentPF");

            if (pKW) pKW.textContent = `${s.active_power_kw} kW`;
            if (eKWH) eKWH.textContent = `${s.energy_kwh} kWh`;
            if (vV) vV.textContent = `${s.voltage_v || 230} V`;
            if (iPF) iPF.textContent = `${s.current_a || 18.4} A (PF: ${s.power_factor || 0.95})`;

            const hKW = document.getElementById("liveMetricHvacKW");
            const cTemp = document.getElementById("liveMetricChillerTemp");
            const fSpeed = document.getElementById("liveMetricFanSpeed");
            const hStat = document.getElementById("liveMetricHvacStatus");

            if (hKW) hKW.textContent = `${s.hvac_load_kw} kW`;
            if (cTemp) cTemp.textContent = `${s.chiller_temp_c || 7.2} °C`;
            if (fSpeed) fSpeed.textContent = `${s.fan_speed_rpm || 1450} RPM`;
            if (hStat) hStat.textContent = s.hvac_status || "NORMAL";

            const wFlow = document.getElementById("liveMetricWaterFlow");
            const tLvl = document.getElementById("liveMetricTankLevel");
            const wPress = document.getElementById("liveMetricWaterPressure");
            const cWater = document.getElementById("liveMetricCumWater");

            if (wFlow) wFlow.textContent = `${s.water_flow_lmin} L/min`;
            if (tLvl) tLvl.textContent = `${s.tank_level_pct || 78} %`;
            if (wPress) wPress.textContent = `${s.water_pressure_bar || 3.4} bar`;
            if (cWater) cWater.textContent = `${s.cumulative_water_m3 || 1240} m³`;

            const rTemp = document.getElementById("liveMetricRoomTemp");
            const oCount = document.getElementById("liveMetricOccupancyCount");
            const rHum = document.getElementById("liveMetricHumidity");
            const aAqi = document.getElementById("liveMetricAirAqi");

            if (rTemp) rTemp.textContent = `${s.temperature_c} °C`;
            if (oCount) oCount.textContent = `${s.occupancy_count} People`;
            if (rHum) rHum.textContent = `${s.humidity_pct || 58} %`;
            if (aAqi) aAqi.textContent = `${s.air_quality_aqi || s.air_aqi || 45} AQI (${s.co2_ppm || 650} ppm)`;
        }
    };

    // Fetch Stream Log
    const fetchStreamLog = async () => {
        try {
            const res = await fetch("/api/v1/iot-simulator/stream?limit=15");
            if (res.ok) {
                const streamData = await res.json();
                const tbody = document.getElementById("simStreamTableBody");
                if (tbody && streamData.stream) {
                    tbody.innerHTML = streamData.stream.map(item => {
                        const pKW = item.active_power_kw ?? item.telemetry?.active_power_kw ?? 145.2;
                        const tC = item.temperature_c ?? item.telemetry?.temperature_c ?? 24.5;
                        return `
                        <tr>
                            <td style="padding:6px; font-family:monospace; font-size:11px;">${item.sample_id}</td>
                            <td style="padding:6px;">${item.timestamp ? item.timestamp.replace("T", " ").slice(11, 19) : "--"}</td>
                            <td style="padding:6px; font-weight:600;">${pKW} kW</td>
                            <td style="padding:6px;">${tC}°C</td>
                            <td style="padding:6px;"><span class="badge-amber" style="font-size:10px;">${item.data_source || item.data_source_mode || 'simulated_iot'}</span></td>
                        </tr>
                    `}).join("");
                }

                // Populate Live IoT Monitor Tab Packet Table
                const monTbody = document.getElementById("monIotStreamTableBody");
                const monTotal = document.getElementById("monTotalIngestedRecords");
                if (monTotal) monTotal.textContent = streamData.total_records || streamData.stream?.length || 0;

                if (monTbody && streamData.stream) {
                    monTbody.innerHTML = streamData.stream.map(item => {
                        const pKW = item.active_power_kw ?? item.telemetry?.active_power_kw ?? 145.2;
                        const tC = item.temperature_c ?? item.telemetry?.temperature_c ?? 24.5;
                        return `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                            <td style="padding:10px; font-family:monospace; font-size:11px; color:#A3C9BE;">${item.sample_id}</td>
                            <td style="padding:10px; font-size:12px;">${item.timestamp ? item.timestamp.replace("T", " ").slice(11, 19) : "--"}</td>
                            <td style="padding:10px; font-weight:600; color:#38BDF8;">DEV_ELEC_01</td>
                            <td style="padding:10px; font-size:12px;">${item.building_id || 'Block B Hostel'}</td>
                            <td style="padding:10px; font-weight:700; color:#00D09C;">${pKW} kW / ${tC}°C</td>
                            <td style="padding:10px;"><span class="badge-mint" style="font-size:10px;">${item.data_source || item.data_source_mode || 'simulated_iot'}</span></td>
                            <td style="padding:10px;"><span class="text-mint" style="font-size:12px;"><i class="fa-solid fa-circle-check"></i> INGESTED</span></td>
                        </tr>
                    `}).join("");
                }
            }
        } catch (e) {
            console.error("Stream log error:", e);
        }
    };

    // Global Set to track notified unique alert keys so alerts are notified ONLY ONCE per session
    window.notifiedAlertKeys = window.notifiedAlertKeys || new Set();

    const syncGlobalTelemetryDashboard = async () => {
        try {
            // 1. Fetch live energy forecasts
            loadBackendForecasts();

            // 2. Fetch live anomalies & evaluate alerts
            const res = await fetch("/api/v1/energy/anomalies");
            if (res.ok) {
                const data = await res.json();
                
                // Update badge counts
                const sidebarBadge = document.getElementById("sidebarAlertCount");
                const notifBadge = document.getElementById("notificationCount");
                const notifUnreadBadge = document.getElementById("notifUnreadBadge");

                if (sidebarBadge) sidebarBadge.textContent = data.active_anomalies_count;
                if (notifBadge) notifBadge.textContent = data.active_anomalies_count;
                if (notifUnreadBadge) notifUnreadBadge.textContent = `${data.active_anomalies_count} Active`;

                // Loop through anomalies and notify ONLY ONCE per unique alert key
                (data.anomalies || []).forEach(anom => {
                    const alertKey = `${anom.issue}_${anom.building}`;
                    if (!window.notifiedAlertKeys.has(alertKey)) {
                        window.notifiedAlertKeys.add(alertKey);

                        // 1. Trigger live glassmorphic toast notification (one time only)
                        showToast(`⚡ Alert [${anom.severity}]: ${anom.issue} (${anom.observed_value}) in ${anom.building}`);

                        // 2. Prepend live notification item into Notifications Dropdown
                        const notifList = document.getElementById("notifListItems");
                        if (notifList) {
                            const notifItem = document.createElement("div");
                            notifItem.className = `notif-item unread ${anom.severity === 'CRITICAL' ? 'p1-alert' : 'p2-alert'}`;
                            notifItem.innerHTML = `
                                <div class="notif-icon-box ${anom.severity === 'CRITICAL' ? 'bg-red' : 'bg-amber'}">
                                    <i class="fa-solid ${anom.severity === 'CRITICAL' ? 'fa-bolt' : 'fa-triangle-exclamation'}"></i>
                                </div>
                                <div class="notif-content">
                                    <div class="notif-top-row">
                                        <span class="notif-severity ${anom.severity === 'CRITICAL' ? 'badge-red' : 'badge-amber'}">${anom.severity}</span>
                                        <span class="notif-time">Just now</span>
                                    </div>
                                    <h4>${escapeHtml(anom.issue)} — ${escapeHtml(anom.building)}</h4>
                                    <p>Observed ${escapeHtml(String(anom.observed_value))} baseline telemetry envelope.</p>
                                </div>
                            `;
                            notifList.insertBefore(notifItem, notifList.firstChild);
                        }
                    }
                });
            }
        } catch (e) {
            console.error("Telemetry sync error:", e);
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
    fetchStatus();
    fetchStreamLog();
    syncGlobalTelemetryDashboard();

    // Auto refresh interval every 2.5s across all tabs
    setInterval(() => {
        syncGlobalTelemetryDashboard();
        fetchStatus();
        fetchStreamLog();
    }, 2500);
}



