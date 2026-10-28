#!/usr/bin/env python3
"""
card_generator.py
Autonomous Branded Visual Card Generator for Pinterest (1000x1500 px, 2:3 vertical aspect ratio).
Produces elegant editorial graphic cards for aviperera.com articles,
ensuring 100% brand consistency, copyright safety, and high Pinterest click-through rates.
"""

import html
import textwrap
from typing import Dict, Optional

def generate_svg_card(
    title: str,
    category: str = "AI ETHICS & SOCIETY",
    excerpt: str = "",
    author: str = "Avi Perera",
    domain: str = "aviperera.com"
) -> str:
    """
    Generates a high-resolution, modern dark-mode editorial SVG card (1000x1500).
    Renders cleanly without external graphic design dependencies.
    """
    clean_title = html.escape(title.strip())
    clean_category = html.escape(category.upper().strip())
    clean_excerpt = html.escape(excerpt.strip()[:180])
    if clean_excerpt and not clean_excerpt.endswith("."):
        clean_excerpt += "..."
        
    # Wrap title into lines of ~26 characters for optimal 1000px width typography
    title_lines = textwrap.wrap(clean_title, width=24)
    if len(title_lines) > 4:
        title_lines = title_lines[:3] + [title_lines[3] + "..."]

    # Calculate vertical start offset based on title line count
    line_height = 70
    total_title_height = len(title_lines) * line_height
    start_y = 520 - (total_title_height // 2)

    title_tps = []
    for idx, line in enumerate(title_lines):
        y_pos = start_y + (idx * line_height)
        title_tps.append(f'<tspan x="500" y="{y_pos}" text-anchor="middle">{line}</tspan>')
    title_svg = "\n        ".join(title_tps)

    # Wrap excerpt
    excerpt_lines = textwrap.wrap(clean_excerpt, width=42)
    excerpt_start_y = start_y + total_title_height + 60
    excerpt_tps = []
    for idx, eline in enumerate(excerpt_lines[:3]):
        y_pos = excerpt_start_y + (idx * 38)
        excerpt_tps.append(f'<tspan x="500" y="{y_pos}" text-anchor="middle">{eline}</tspan>')
    excerpt_svg = "\n        ".join(excerpt_tps)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
    <defs>
        <linearGradient id="bg-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0B0F19" />
            <stop offset="50%" stop-color="#111827" />
            <stop offset="100%" stop-color="#1F2937" />
        </linearGradient>
        <linearGradient id="accent-grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#38BDF8" />
            <stop offset="100%" stop-color="#818CF8" />
        </linearGradient>
        <filter id="card-shadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="16" stdDeviation="24" flood-color="#000000" flood-opacity="0.6"/>
        </filter>
    </defs>

    <!-- Deep Minimalist Canvas Background -->
    <rect width="1000" height="1500" fill="url(#bg-grad)" />

    <!-- Subtle Geometric Grid / Framing Accent -->
    <rect x="50" y="50" width="900" height="1400" rx="32" fill="none" stroke="#334155" stroke-width="2" opacity="0.4" />
    <circle cx="500" cy="180" r="140" fill="#38BDF8" opacity="0.04" />
    <circle cx="500" cy="750" r="400" fill="#818CF8" opacity="0.03" />

    <!-- Header Badge Pill -->
    <g transform="translate(500, 160)">
        <rect x="-180" y="-24" width="360" height="48" rx="24" fill="#1E293B" stroke="#475569" stroke-width="1.5" />
        <text x="0" y="7" text-anchor="middle" fill="#38BDF8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="16" font-weight="700" letter-spacing="3">{clean_category}</text>
    </g>

    <!-- Center Card Enclosure -->
    <rect x="90" y="260" width="820" height="840" rx="24" fill="#0F172A" fill-opacity="0.85" stroke="#1E293B" stroke-width="2" filter="url(#card-shadow)" />

    <!-- Decorative Accent Line -->
    <rect x="430" y="320" width="140" height="4" rx="2" fill="url(#accent-grad)" />

    <!-- Article Main Title -->
    <text font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Georgia', serif" font-size="52" font-weight="800" fill="#F8FAFC" letter-spacing="-0.5">
        {title_svg}
    </text>

    <!-- Article Excerpt / Thesis Synopsis -->
    <text font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="24" font-weight="400" fill="#94A3B8" opacity="0.95">
        {excerpt_svg}
    </text>

    <!-- Bottom Call-To-Action Container -->
    <g transform="translate(500, 1220)">
        <!-- Read More Button -->
        <rect x="-210" y="-32" width="420" height="64" rx="32" fill="url(#accent-grad)" />
        <text x="0" y="9" text-anchor="middle" fill="#0F172A" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="20" font-weight="700" letter-spacing="1">READ FULL DOSSIER →</text>
    </g>

    <!-- Footer Branding & Author Verification -->
    <text x="500" y="1360" text-anchor="middle" fill="#E2E8F0" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="22" font-weight="600" letter-spacing="1">{domain.upper()}</text>
    <text x="500" y="1395" text-anchor="middle" fill="#64748B" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="16" font-weight="400">Research &amp; Analysis by {author}</text>
</svg>"""
    return svg

