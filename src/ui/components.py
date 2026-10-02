"""
UI/UX Components & Visual Design System Engine.
Provides Lucide SVG icons, custom Command Center CSS stylesheets, top bar application shell,
premium KPI metric cards, trust badges, and dark-theme chart wrappers.
"""

import streamlit as st
import plotly.graph_objects as go
from typing import Optional, Dict, Any

# ==============================================================================
# 1. LUCIDE SVG ICON SYSTEM (NO EMOJIS)
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
    "SlidersHorizontal": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/></svg>'
}

def get_icon(name: str, color: str = "currentColor", size: int = 18) -> str:
    """Returns SVG string for named Lucide icon."""
    template = LUCIDE_ICONS.get(name, LUCIDE_ICONS["Activity"])
    return template.format(color=color, size=size)

# ==============================================================================
# 2. GLOBAL COMMAND CENTER CSS STYLESHEET
# ==============================================================================
COMMAND_CENTER_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Main Background & Padding */
    .stApp {
        background-color: #0B132B;
        color: #F8FAFC;
    }
    
    /* Hide Default Header Elements */
    header[data-testid="stHeader"] {
        background: transparent;
    }
    
    /* Top Bar Application Shell */
    .cmd-topbar {
        background: linear-gradient(180deg, #151E33 0%, #0F172A 100%);
        border: 1px solid #2A3857;
        border-radius: 12px;
        padding: 12px 20px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .cmd-topbar-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #F8FAFC;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .cmd-status-pill {
        background: rgba(34, 197, 94, 0.15);
        border: 1px solid #22C55E;
        color: #4ADE80;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .cmd-status-pill-attention {
        background: rgba(245, 158, 11, 0.15);
        border: 1px solid #F59E0B;
        color: #FBBF24;
    }
    .cmd-user-badge {
        background: #1E293B;
        border: 1px solid #334155;
        color: #94A3B8;
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    /* Sidebar Customization */
    section[data-testid="stSidebar"] {
        background-color: #0F172A;
        border-right: 1px solid #1E293B;
    }
    .sidebar-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #38BDF8;
        padding: 10px 0;
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 1px solid #1E293B;
        margin-bottom: 15px;
    }
    .sidebar-section-label {
        font-size: 0.75rem;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-top: 18px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    /* Hide Native Streamlit Radio Inputs & Red Dots Completely */
    div[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label input[type="radio"] {
        display: none !important;
    }

    /* Sidebar Radio Options Card Styling & Micro-Interactions */
    div[data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 6px !important;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label {
        background: #151E33 !important;
        border: 1px solid #2A3857 !important;
        border-radius: 8px !important;
        padding: 8px 14px !important;
        color: #CBD5E1 !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
    }
    
    /* Hover Micro-Interaction */
    div[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: #1E293B !important;
        border-color: #0EA5E9 !important;
        color: #F8FAFC !important;
        transform: translateX(4px) !important;
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.25) !important;
    }
    
    /* Active Navigation Item Effect */
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.22) 0%, rgba(15, 23, 42, 0.95) 100%) !important;
        border: 1px solid #38BDF8 !important;
        color: #38BDF8 !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 16px rgba(14, 165, 233, 0.3), inset 0 0 10px rgba(56, 189, 248, 0.12) !important;
        transform: translateX(6px) !important;
    }

    /* Blue Structure Lucide SVG Icons for Every Navigation Item */
    div[data-testid="stSidebar"] div[role="radiogroup"] label::before {
        content: "";
        display: inline-block;
        width: 18px;
        height: 18px;
        min-width: 18px;
        margin-right: 10px;
        vertical-align: middle;
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(1)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><rect width='7' height='9' x='3' y='3' rx='1'/><rect width='7' height='5' x='14' y='3' rx='1'/><rect width='7' height='9' x='14' y='12' rx='1'/><rect width='7' height='5' x='3' y='16' rx='1'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(2)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M14.1 5.55a2 2 0 0 0-1.78 0l-3.65 1.83L4 5.1v13.8l4.3 2.15a2 2 0 0 0 1.79 0l3.65-1.83L18 20.9V7.1z'/><path d='M14 5.75v13.5'/><path d='M9 7.75v13.5'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(3)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polygon points='13 2 3 14 12 14 11 22 21 10 12 10 13 2'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(4)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M7 16.3c2.2 0 4-1.83 4-4.05 0-1.16-.57-2.26-1.71-3.19S7.29 6.75 7 5.3c-.29 1.45-1.29 2.84-2.29 3.76S3 11.09 3 12.25c0 2.22 1.8 4.05 4 4.05z'/><path d='M12.56 6.6A10.97 10.97 0 0 0 14 3c.5 2.5 2 4.9 4 6.5s3 3.5 3 5.5a7 7 0 0 1-14 0c0-1.15.28-2.35.84-3.5'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(5)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M7 19H4.8a1.8 1.8 0 0 1-1.6-.9 1.8 1.8 0 0 1 0-1.8L7.2 9.5'/><path d='M11 19h8.2a1.8 1.8 0 0 0 1.6-1 1.8 1.8 0 0 0-.1-1.8l-3.3-5.7'/><path d='m14 13-3-5.2a1.8 1.8 0 0 0-1.6-1h-6.8'/><path d='M14 16.5 11.5 21l-2.5-4.5'/><path d='M4 14.5 1.5 10l5-1'/><path d='M18.5 7.5 21 12l-5 1'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(6)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2'/><path d='M9.6 4.6A2 2 0 1 1 11 8H2'/><path d='M12.6 19.4A2 2 0 1 0 14 16H2'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(7)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.5 2.8C1.4 11.3 1 12.1 1 13v3c0 .6.4 1 1 1h2'/><circle cx='7' cy='17' r='2'/><circle cx='17' cy='17' r='2'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(8)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><rect width='18' height='18' x='3' y='3' rx='2'/><path d='M9 17V7h4a3 3 0 0 1 0 6H9'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(9)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20 7h-9'/><path d='M14 17H5'/><circle cx='17' cy='17' r='3'/><circle cx='7' cy='7' r='3'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(10)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z'/><path d='m9 12 2 2 4-4'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(11)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z'/><path d='M17 18h1'/><path d='M12 18h1'/><path d='M7 18h1'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(12)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.4 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z'/><path d='M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(13)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9'/><path d='M10.3 21a1.94 1.94 0 0 0 3.4 0'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(14)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='m12 3-1.9 5.8a2 2 0 0 1-1.28 1.28L3 12l5.8 1.9a2 2 0 0 1 1.28 1.28L12 21l1.9-5.8a2 2 0 0 1 1.28-1.28L21 12l-5.8-1.9a2 2 0 0 1-1.28-1.28Z'/><path d='M5 3v4'/><path d='M19 17v4'/><path d='M3 5h4'/><path d='M17 19h4'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(15)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M10 2v7.527a2 2 0 0 1-.211.896L4.72 20.55A1 1 0 0 0 5.607 22h12.786a1 1 0 0 0 .886-1.45l-5.069-10.127A2 2 0 0 1 14 9.527V2'/><path d='M8.5 2h7'/><path d='M7 16h10'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(16)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><ellipse cx='12' cy='5' rx='9' ry='3'/><path d='M3 5V19A9 3 0 0 0 21 19V5'/><path d='M3 12A9 3 0 0 0 21 12'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(17)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z'/><path d='M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z'/><path d='M15 13a3 3 0 1 0-6 0'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(18)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z'/><path d='m9 12 2 2 4-4'/></svg>");
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(19)::before {
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338BDF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M2 3h20'/><path d='M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3'/><path d='m7 21 5-5 5 5'/></svg>");
    }
    
    /* Card Container */
    .cmd-card {
        background: #151E33;
        border: 1px solid #2A3857;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .cmd-card:hover {
        border-color: #38BDF8;
    }
    
    /* KPI Card */
    .kpi-title {
        font-size: 0.82rem;
        font-weight: 600;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 4px;
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
        padding: 2px 8px;
        border-radius: 6px;
    }
    .trend-up { background: rgba(239, 68, 68, 0.15); color: #F87171; }
    .trend-down { background: rgba(34, 197, 94, 0.15); color: #4ADE80; }
    .trend-neutral { background: rgba(148, 163, 184, 0.15); color: #94A3B8; }
    
    /* Trust Badges */
    .trust-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-left: 8px;
    }
    .badge-observed { background: #1E293B; color: #38BDF8; border: 1px solid #0EA5E9; }
    .badge-predicted { background: rgba(139, 92, 246, 0.15); color: #C084FC; border: 1px solid #8B5CF6; }
    .badge-simulated { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid #F59E0B; }
    .badge-synthetic { background: rgba(100, 116, 139, 0.2); color: #94A3B8; border: 1px solid #64748B; }
    
    /* AI Insights Container */
    .ai-insight-box {
        background: linear-gradient(135deg, rgba(21, 30, 51, 0.9) 0%, rgba(30, 41, 59, 0.9) 100%);
        border: 1px solid #8B5CF6;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 16px;
    }
    .ai-insight-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #C084FC;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
    }
</style>
"""

def inject_custom_css():
    """Injects the global Command Center CSS styling."""
    st.markdown(COMMAND_CENTER_CSS, unsafe_allow_html=True)

def render_top_bar(campus_name: str = "GEC Smart Campus", status: str = "ATTENTION", user_role: str = "Administrator View"):
    """Renders top application shell bar."""
    status_class = "cmd-status-pill-attention" if status == "ATTENTION" else "cmd-status-pill"
    status_icon = get_icon("TriangleAlert", "#FBBF24", 14) if status == "ATTENTION" else get_icon("CircleCheck", "#4ADE80", 14)
    status_text = "● ATTENTION REQUIRED" if status == "ATTENTION" else "● SYSTEM OPERATIONAL"
    
    icon_dashboard = get_icon("LayoutDashboard", "#38BDF8", 22)
    
    st.markdown(f"""
    <div class="cmd-topbar">
        <div class="cmd-topbar-title">
            {icon_dashboard}
            <span>{campus_name} — AI Facility Command Center</span>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <div class="{status_class}">
                {status_icon} {status_text}
            </div>
            <div class="cmd-user-badge">
                {user_role}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

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

def render_kpi_card(title: str, value: str, unit: str = "", trend: str = "", trend_direction: str = "neutral", icon_name: str = "Activity", icon_color: str = "#38BDF8"):
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
    """Applies cohesive dark-navy command center styling to Plotly figures."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(21, 30, 51, 0.75)",
        plot_bgcolor="rgba(15, 23, 42, 0.75)",
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
