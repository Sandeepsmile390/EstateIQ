"""
UI/UX Components & Visual Design System Engine.
Provides Lucide SVG icons, custom Command Center CSS stylesheets, top bar application shell,
hero metric cards, trust badges, dark-theme chart wrappers, and Liquid-Glass Canva design tokens.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import Optional, Dict, Any

# ==============================================================================
# 1. LUCIDE SVG ICON SYSTEM
# ==============================================================================
LUCIDE_ICONS: Dict[str, str] = {
    "LayoutDashboard": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>',
    "Map": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.106 5.553a2 2 0 0 0-1.788 0l-3.647 1.824L4 5.105v13.79l4.316 2.158a2 2 0 0 0 1.788 0l3.647-1.824L18 20.895V7.105l-3.894-1.952z"/><path d="M14 5.75v13.5"/><path d="M9 7.75v13.5"/></svg>',
    "Bell": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
    "Zap": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    "Droplets": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 16.3c2.2 0 4-1.83 4-4.05 0-1.16-.57-2.26-1.71-3.19S7.29 6.75 7 5.3c-.29 1.45-1.29 2.84-2.29 3.76S3 11.09 3 12.25c0 2.22 1.8 4.05 4 4.05z"/><path d="M12.56 6.6A10.97 10.97 0 0 0 14 3c.5 2.5 2 4.9 4 6.5s3 3.5 3 5.5a7 7 0 0 1-14 0c0-1.15.28-2.35.84-3.5"/></svg>',
    "Recycle": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 19H4.815a1.83 1.83 0 0 1-1.57-.881 1.785 1.785 0 0 1-.004-1.784L7.196 9.5"/><path d="M11 19h8.2a1.8 1.8 0 0 0 1.6-1 1.8 1.8 0 0 0-.1-1.8l-3.3-5.7"/><path d="m14 13-3-5.2a1.8 1.8 0 0 0-1.6-1h-6.8"/><path d="M14 16.5 11.5 21l-2.5-4.5"/><path d="M4 14.5 1.5 10l5-1"/><path d="M18.5 7.5 21 12l-5 1"/></svg>',
    "Wind": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/><path d="M12.6 19.4A2 2 0 1 0 14 16H2"/></svg>',
    "Car": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.5 2.8C1.4 11.3 1 12.1 1 13v3c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/></svg>',
    "ParkingSquare": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 17V7h4a3 3 0 0 1 0 6H9"/></svg>',
    "Settings2": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 7h-9"/><path d="M14 17H5"/><circle cx="17" cy="17" r="3"/><circle cx="7" cy="7" r="3"/></svg>',
    "ShieldCheck": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></svg>',
    "Factory": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M17 18h1"/><path d="M12 18h1"/><path d="M7 18h1"/></svg>',
    "Leaf": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.4 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/></svg>',
    "Sparkles": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.28 1.28L3 12l5.8 1.9a2 2 0 0 1 1.28 1.28L12 21l1.9-5.8a2 2 0 0 1 1.28-1.28L21 12l-5.8-1.9a2 2 0 0 1-1.28-1.28Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/></svg>',
    "FlaskConical": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 2v7.527a2 2 0 0 1-.211.896L4.72 20.55A1 1 0 0 0 5.607 22h12.786a1 1 0 0 0 .886-1.45l-5.069-10.127A2 2 0 0 1 14 9.527V2"/><path d="M8.5 2h7"/><path d="M7 16h10"/></svg>',
    "Database": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/></svg>',
    "BrainCircuit": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/><path d="M15 13a3 3 0 1 0-6 0"/></svg>',
    "BadgeCheck": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z"/><path d="m9 12 2 2 4-4"/></svg>',
    "Presentation": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h20"/><path d="M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3"/><path d="m7 21 5-5 5 5"/></svg>',
    "Search": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
    "CircleCheck": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>',
    "TriangleAlert": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>',
    "Activity": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
    "UserCheck": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="16 11 18 13 22 9"/></svg>',
    "Radio": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9"/><path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5"/><circle cx="12" cy="12" r="2"/><path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/><path d="M19.1 4.9c3.9 3.9 3.9 10.3 0 14.2"/></svg>',
    "SlidersHorizontal": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/></svg>',
    "Cpu": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="15" x2="23" y2="15"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="15" x2="4" y2="15"/></svg>',
    "Crown": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/></svg>',
    "Location": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>',
    "Lightbulb": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1.3.5 2.6 1.5 3.5.8.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/></svg>',
    "Trash2": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>'
}

def get_icon(name: str, color: str = "currentColor", size: int = 18) -> str:
    """Returns SVG string for named Lucide icon."""
    template = LUCIDE_ICONS.get(name, LUCIDE_ICONS["Activity"])
    return template.format(color=color, size=size)

# ==============================================================================
# 2. GLOBAL LIQUID-GLASS & WEB UI DESIGN SYSTEM CSS
# ==============================================================================
COMMAND_CENTER_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --brand-primary: #124B3E;
        --brand-mint: #2BB49B;
        --brand-teal: #1E7A68;
        --brand-accent: #00D09C;
        --brand-gold: #F5C577;
        --brand-amber: #D97706;
        --brand-red: #EF4444;
        --bg-app: #0B132B;
        --bg-sidebar: #0E3D32;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Global Background */
    .stApp {
        background-color: #0B132B;
        color: #F8FAFC;
    }
    
    /* Hide Default Streamlit Header Line */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    
    /* --- TOP HEADER APPLICATION SHELL (EXACT MATCH TO WEB UI) --- */
    .web-top-header {
        background: linear-gradient(135deg, #0E3D32 0%, #0F172A 100%);
        border: 1px solid rgba(43, 180, 155, 0.25);
        border-radius: 16px;
        padding: 14px 22px;
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08);
        gap: 16px;
        flex-wrap: wrap;
    }

    .brand-group {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .brand-logo-icon {
        width: 38px;
        height: 38px;
        background: linear-gradient(135deg, #2BB49B 0%, #104F40 100%);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #FFFFFF;
        box-shadow: 0 4px 14px rgba(43, 180, 155, 0.4);
    }

    .brand-logo-text {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.4rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.5px;
    }

    .brand-logo-text .highlight {
        color: #2BB49B;
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .plan-badge-pill {
        background: rgba(245, 197, 119, 0.12);
        border: 1px solid #F5C577;
        color: #F5C577;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .user-persona-pill {
        background: #124B3E;
        border: 1px solid #2BB49B;
        color: #FFFFFF;
        padding: 5px 14px;
        border-radius: 10px;
        font-size: 0.82rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .persona-avatar {
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: #2BB49B;
        color: #0E3D32;
        font-weight: 800;
        font-size: 0.75rem;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* --- STATUS BANNER --- */
    .web-status-banner {
        background: linear-gradient(90deg, rgba(18, 75, 62, 0.85) 0%, rgba(15, 23, 42, 0.85) 100%);
        border: 1px solid #2BB49B;
        border-radius: 12px;
        padding: 10px 18px;
        margin-bottom: 22px;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 0.86rem;
        color: #E2E8F0;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }
    .banner-notice-tag {
        background: #2BB49B;
        color: #0E3D32;
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.5px;
    }

    /* --- SIDEBAR NAV CUSTOMIZATION --- */
    section[data-testid="stSidebar"] {
        background-color: #0E3D32 !important;
        border-right: 1px solid rgba(43, 180, 155, 0.2);
    }

    /* Hide Native Radio Buttons */
    div[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label input[type="radio"] {
        display: none !important;
    }

    /* Sleek Nav Buttons */
    div[data-testid="stSidebar"] div[role="radiogroup"] label {
        background: rgba(18, 75, 62, 0.4) !important;
        border: 1px solid rgba(43, 180, 155, 0.2) !important;
        border-radius: 10px !important;
        padding: 9px 14px !important;
        color: #A3C9BE !important;
        font-size: 0.86rem !important;
        font-weight: 600 !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        cursor: pointer !important;
        margin-bottom: 4px !important;
        width: 100% !important;
    }
    
    div[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: #124B3E !important;
        border-color: #2BB49B !important;
        color: #FFFFFF !important;
        transform: translateX(4px) !important;
    }
    
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
        background: linear-gradient(135deg, #124B3E 0%, #1E7A68 100%) !important;
        border: 1px solid #00D09C !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 16px rgba(0, 208, 156, 0.3) !important;
        transform: translateX(6px) !important;
    }

    /* --- HERO TOP METRICS CARDS (MATCHING WEB UI TOP ROW) --- */
    .hero-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }

    .hero-card-dark-green {
        background: linear-gradient(135deg, #124B3E 0%, #0E3D32 100%);
        border: 1px solid #2BB49B;
        border-radius: 16px;
        padding: 20px;
        color: #FFFFFF;
        box-shadow: 0 8px 24px rgba(18, 75, 62, 0.4);
        position: relative;
        overflow: hidden;
    }

    .hero-score-val {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 3rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1;
        margin: 10px 0 6px 0;
    }

    .hero-card-glass {
        background: rgba(21, 30, 51, 0.85);
        border: 1px solid #2A3857;
        border-radius: 16px;
        padding: 18px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
    }

    /* KPI Card styling */
    .cmd-card {
        background: linear-gradient(135deg, rgba(21, 30, 51, 0.9) 0%, rgba(15, 23, 42, 0.9) 100%);
        backdrop-filter: blur(10px);
        border: 1px solid #2A3857;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
        transition: all 0.25s ease;
    }
    .cmd-card:hover {
        border-color: #2BB49B;
        box-shadow: 0 8px 24px rgba(43, 180, 155, 0.2);
        transform: translateY(-2px);
    }
    
    .kpi-title {
        font-size: 0.82rem;
        font-weight: 700;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .kpi-value {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.85rem;
        font-weight: 800;
        color: #F8FAFC;
        margin-bottom: 6px;
        line-height: 1.2;
    }
    .kpi-unit {
        font-size: 0.9rem;
        font-weight: 400;
        color: #64748B;
        margin-left: 4px;
    }
    .kpi-trend {
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        border-radius: 6px;
    }
    .trend-up { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .trend-down { background: rgba(34, 197, 94, 0.15); color: #4ADE80; border: 1px solid rgba(34, 197, 94, 0.3); }
    .trend-neutral { background: rgba(148, 163, 184, 0.15); color: #94A3B8; border: 1px solid rgba(148, 163, 184, 0.3); }

    /* Trust Badges */
    .trust-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin-left: 8px;
    }
    .badge-observed { background: #1E293B; color: #38BDF8; border: 1px solid #0EA5E9; }
    .badge-predicted { background: rgba(139, 92, 246, 0.15); color: #C084FC; border: 1px solid #8B5CF6; }
    .badge-simulated { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid #F59E0B; }
    .badge-synthetic { background: rgba(100, 116, 139, 0.2); color: #94A3B8; border: 1px solid #64748B; }

    .pill-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.4px;
    }
    .badge-green { background: rgba(34, 197, 94, 0.15); color: #4ADE80; border: 1px solid #22C55E; }
    .badge-amber { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid #F59E0B; }
    .badge-red { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid #EF4444; }
    .badge-teal { background: rgba(43, 180, 155, 0.15); color: #2BB49B; border: 1px solid #2BB49B; }
    .badge-gold { background: rgba(245, 197, 119, 0.15); color: #F5C577; border: 1px solid #F5C577; }

    /* AI Insight Container */
    .ai-insight-box {
        background: linear-gradient(135deg, rgba(18, 75, 62, 0.9) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid #2BB49B;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 8px 24px rgba(43, 180, 155, 0.15);
    }
    .ai-insight-header {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.1rem;
        font-weight: 800;
        color: #2BB49B;
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
    }
</style>
"""

def inject_custom_css():
    """Injects the global Command Center CSS styling."""
    st.markdown(COMMAND_CENTER_CSS, unsafe_allow_html=True)

def render_top_bar(campus_name: str = "Main Campus - All Blocks", status: str = "ATTENTION", user_role: str = "RS Administrator"):
    """Renders top header application shell exactly matching EstateIQ Web UI."""
    icon_leaf = get_icon("Leaf", "#2BB49B", 22)
    icon_crown = get_icon("Crown", "#F5C577", 14)
    
    # Initials for avatar
    initials = "RS"
    role_title = "Facility Lead & Admin"
    if "Alex" in user_role or "Engineer" in user_role:
        initials = "AC"
        role_title = "Operations Engineer"
    elif "Priya" in user_role or "Auditor" in user_role:
        initials = "PS"
        role_title = "ESG Auditor"
    elif "Sam" in user_role or "Stakeholder" in user_role or "Viewer" in user_role:
        initials = "ST"
        role_title = "Campus Stakeholder"

    st.markdown(f"""
    <div class="web-top-header">
        <div class="brand-group">
            <div class="brand-logo-icon">
                {icon_leaf}
            </div>
            <div class="brand-logo-text">
                Estate<span class="highlight">IQ</span>
            </div>
        </div>
        <div class="header-actions">
            <div class="plan-badge-pill">
                {icon_crown}
                <span>Enterprise Pro</span>
            </div>
            <div class="user-persona-pill">
                <div class="persona-avatar">{initials}</div>
                <div>
                    <div>{user_role}</div>
                    <div style="font-size: 0.7rem; color: #A3C9BE;">{role_title}</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_status_banner(active_role: str = "RS Administrator", suggestions_count: int = 3):
    """Renders status notice banner matching web UI."""
    st.markdown(f"""
    <div class="web-status-banner">
        <span class="banner-notice-tag">NOTICE</span>
        <span>Campus Grid Live: Logged in as <strong>{active_role}</strong> • <strong>{suggestions_count} AI Suggestions</strong> active</span>
    </div>
    """, unsafe_allow_html=True)

def render_hero_metrics_grid(hero_score: int = 87, energy_val: str = "7.42 MWh", water_val: str = "12,480 kL", aqi_val: int = 68):
    """Renders Row 1 Key Metrics Cards (Exact Canva Design Pattern from Web UI)."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="hero-card-dark-green">
            <div style="display:flex; justify-shadow:space-between; justify-content:space-between; align-items:center;">
                <span style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.6px; color:#A3C9BE; font-weight:700;">Overall Facility Score</span>
                <span class="pill-badge badge-gold">Gold Grade</span>
            </div>
            <div class="hero-score-val">{hero_score}<span style="font-size:1.2rem; color:#A3C9BE;">/100</span></div>
            <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.78rem;">
                <span style="color:#4ADE80;">● Optimal Efficiency</span>
                <span style="color:#2BB49B;">+4.2% vs last mo</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        render_kpi_card("Energy Consumption", energy_val, "", "Target: 74%", "down", "Zap", "#F5C577")

    with col3:
        render_kpi_card("Water / Air Quality", water_val, f" | AQI {aqi_val}", "Water: On Track", "neutral", "Droplets", "#2BB49B")

    with col4:
        render_kpi_card("Weekly Load Profile", "-8.4%", " vs baseline", "Efficiency Gain", "down", "Activity", "#00D09C")

def render_badge(badge_type: str = "observed") -> str:
    """Returns HTML for trust badges."""
    badge_map = {
        "observed": ('badge-observed', 'OBSERVED DATA'),
        "predicted": ('badge-predicted', 'ML PREDICTION'),
        "simulated": ('badge-simulated', 'SIMULATED SCENARIO'),
        "synthetic": ('badge-synthetic', 'SYNTHETIC IoT DATA')
    }
    css_cls, label = badge_map.get(badge_type.lower(), badge_map["observed"])
    return f'<span class="trust-badge {css_cls}">{label}</span>'

def render_kpi_card(title: str, value: str, unit: str = "", trend: str = "", trend_direction: str = "neutral", icon_name: str = "Activity", icon_color: str = "#2BB49B"):
    """Renders custom dark mode KPI metric card."""
    icon_svg = get_icon(icon_name, icon_color, 20)
    trend_cls = f"trend-{trend_direction}"
    
    st.markdown(f"""
    <div class="cmd-card">
        <div class="kpi-title">
            <span>{title}</span>
            {icon_svg}
        </div>
        <div class="kpi-value">
            {value}<span class="kpi-unit">{unit}</span>
        </div>
        {f'<div class="kpi-trend {trend_cls}">{trend}</div>' if trend else ''}
    </div>
    """, unsafe_allow_html=True)

def apply_plotly_theme(fig: go.Figure) -> go.Figure:
    """Applies cohesive dark-navy & emerald command center styling to Plotly figures."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(21, 30, 51, 0.85)",
        plot_bgcolor="rgba(15, 23, 42, 0.85)",
        font=dict(family="Inter, sans-serif", color="#F8FAFC", size=12),
        margin=dict(l=30, r=30, t=40, b=30),
        legend=dict(
            bgcolor="rgba(15, 23, 42, 0.8)",
            bordercolor="#2A3857",
            borderwidth=1,
            font=dict(color="#94A3B8")
        ),
        xaxis=dict(
            gridcolor="#1E293B",
            zerolinecolor="#334155",
            showline=True,
            linecolor="#2A3857"
        ),
        yaxis=dict(
            gridcolor="#1E293B",
            zerolinecolor="#334155",
            showline=True,
            linecolor="#2A3857"
        )
    )
    return fig
