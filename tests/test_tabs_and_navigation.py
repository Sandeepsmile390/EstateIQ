import re
import pytest

def test_index_html_tab_containers_exist():
    with open("web/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    expected_tabs = [
        "contentOverview",
        "contentSuggestions",
        "contentEnergy",
        "contentWater",
        "contentWaste",
        "contentMobility",
        "contentSimulator",
        "contentIotMonitor",
        "contentResourceSimulator",
        "contentFaq",
        "contentEsg",
        "contentBilling",
        "contentAiAssistant",
        "contentWorkOrders"
    ]

    for tab_id in expected_tabs:
        pattern = rf'id=[\"\']{tab_id}[\"\']'
        assert re.search(pattern, html), f"Tab container '{tab_id}' not found in index.html"

def test_no_nested_tabs():
    """Verify that none of the tabs are nested inside another tab-content container."""
    with open("web/index.html", "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_open_tab = None
    stack = 0
    for idx, line in enumerate(lines):
        m = re.search(r'<div[^>]*class=[\"\'][^\"\']*tab-content[^\"\']*[\"\'][^>]*id=[\"\']([^\"\']+)[\"\']', line)
        if m:
            assert current_open_tab is None, f"Found nested tab '{m.group(1)}' inside '{current_open_tab}' at line {idx+1}!"
            current_open_tab = m.group(1)
            stack = 1
            continue

        if current_open_tab:
            opens = len(re.findall(r'<div[\s>]', line))
            closes = len(re.findall(r'</div[\s>]', line))
            stack += opens - closes
            if stack <= 0:
                current_open_tab = None

    assert current_open_tab is None, f"Tab '{current_open_tab}' was never closed!"

def test_tab_buttons_and_nav_match():
    with open("web/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    required_navs = [
        "resource-simulator",
        "iot-monitor",
        "ai-assistant",
        "faq",
        "esg",
        "billing",
        "work-orders"
    ]

    for nav in required_navs:
        assert f'data-tab="{nav}"' in html, f'Button data-tab="{nav}" not found in index.html'
        assert f'data-tab-nav="{nav}"' in html, f'Sidebar data-tab-nav="{nav}" not found in index.html'

def test_app_js_tab_aliases_and_permissions():
    with open("web/js/app.js", "r", encoding="utf-8") as f:
        js = f.read()

    assert "resource-simulator" in js
    assert "TAB_ALIASES" in js
    assert '"copilot": "ai-assistant"' in js
    assert '"subscription": "billing"' in js
    assert '"workorder": "work-orders"' in js

def test_live_iot_monitor_contains_schematic_device_map():
    with open("web/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    with open("web/js/app.js", "r", encoding="utf-8") as f:
        js = f.read()

    assert 'id="liveDeviceMap"' in html
    assert 'id="liveDeviceMapMarkers"' in html
    assert "SCHEMATIC" in html and "not GPS" in html
    assert "renderLiveDeviceMap(devices)" in js

def test_html_tag_balance():
    with open("web/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    tag_pattern = re.compile(r'<(/?[a-zA-Z0-9]+)([^>]*)>')
    void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    stack = []
    for line_idx, line in enumerate(html.splitlines()):
        for m in tag_pattern.finditer(line):
            tag_name = m.group(1).lower()
            full_match = m.group(0)
            if tag_name in void_tags or full_match.endswith('/>'):
                continue
            if tag_name.startswith('/'):
                closing_name = tag_name[1:]
                if closing_name in void_tags:
                    continue
                assert len(stack) > 0, f"Unexpected closing tag </{closing_name}> at line {line_idx+1}"
                top_tag, top_line = stack.pop()
                assert top_tag == closing_name, f"Mismatch at line {line_idx+1}: expected </{top_tag}> from line {top_line}, got </{closing_name}>"
            else:
                stack.append((tag_name, line_idx+1))

    assert len(stack) == 0, f"Unclosed tags at end of document: {stack}"

