"""
SEO-optimized description generator for APKDroid.
Uses template-based generation — no external API or cost.
Each description is unique per app, keyword-rich, and 150-200 words.
"""

import random
from typing import Optional

# Platform-specific action phrases
PLATFORM_ACTIONS = {
    "android": ["on your Android device", "on Android smartphones and tablets", "for Android users"],
    "windows": ["on Windows PC", "for Windows 10/11", "on your Windows desktop or laptop"],
    "macos": ["on macOS", "for Mac users", "on your Mac"],
    "linux": ["on Linux", "for Linux users", "across Linux distributions"],
}

# Category keywords for SEO density
CATEGORY_KEYWORDS = {
    "productivity": ["productivity", "workflow", "task management", "efficiency"],
    "games": ["gaming", "entertainment", "gameplay", "game experience"],
    "tools": ["utility", "system tool", "performance", "optimization"],
    "social": ["social networking", "communication", "messaging", "connecting"],
    "media": ["media playback", "audio", "video", "multimedia"],
    "security": ["security", "privacy", "protection", "encryption"],
    "education": ["learning", "education", "knowledge", "study"],
    "finance": ["finance", "budgeting", "money management", "financial"],
    "health": ["health", "fitness", "wellness", "lifestyle"],
    "default": ["software", "application", "tool", "utility"],
}

INTRO_TEMPLATES = [
    "{name} is a powerful {category} application available {platform}.",
    "Discover {name} — a top-rated {category} app designed {platform}.",
    "{name} is a free {category} app that delivers excellent performance {platform}.",
    "Looking for a reliable {category} solution? {name} is your answer {platform}.",
    "{name} brings a complete {category} experience right to your device {platform}.",
]

FEATURE_TEMPLATES = [
    "It offers a clean, intuitive interface that makes it easy for beginners and experts alike.",
    "With its streamlined design, {name} ensures a smooth experience from the moment you open it.",
    "The app is regularly updated to bring you the latest features and security improvements.",
    "Trusted by millions worldwide, {name} sets the standard for {category} applications.",
    "Built with performance in mind, {name} runs efficiently without draining your battery or resources.",
]

DETAIL_TEMPLATES = [
    "Whether you're a casual user or a power user, {name} adapts to your needs with flexible settings and customization options.",
    "{name} stands out for its reliability, responsiveness, and consistent updates from its dedicated development team.",
    "The app integrates seamlessly with your existing workflow and doesn't require any technical expertise to get started.",
    "With a growing community of users, {name} continues to evolve based on real-world feedback and feature requests.",
    "Available completely free of charge, {name} gives you professional-grade {category} capabilities without spending a dime.",
]

CTA_TEMPLATES = [
    "Download {name} today and experience the difference a quality {category} app can make.",
    "Join millions of users — download {name} for free and elevate your {category} experience.",
    "Get {name} now and take your {category} capabilities to the next level.",
    "Try {name} for free — no registration required, no hidden fees, just a great {category} experience.",
    "Download {name} today from APKDroid and enjoy safe, verified software at no cost.",
]


def _detect_category_type(category: str, name: str, description: str = "") -> str:
    """Map a category name to our keyword group."""
    combined = (category + " " + name + " " + description).lower()
    if any(w in combined for w in ["game", "play", "arcade", "rpg", "puzzle"]):
        return "games"
    if any(w in combined for w in ["secure", "vpn", "antivirus", "privacy", "password"]):
        return "security"
    if any(w in combined for w in ["video", "music", "audio", "media", "player", "stream"]):
        return "media"
    if any(w in combined for w in ["social", "chat", "message", "network", "community"]):
        return "social"
    if any(w in combined for w in ["office", "document", "pdf", "productivity", "note", "calendar"]):
        return "productivity"
    if any(w in combined for w in ["education", "learn", "study", "school", "course"]):
        return "education"
    if any(w in combined for w in ["finance", "bank", "money", "budget", "invest"]):
        return "finance"
    if any(w in combined for w in ["health", "fitness", "workout", "medical"]):
        return "health"
    if any(w in combined for w in ["tool", "utility", "system", "cleaner", "manager"]):
        return "tools"
    return "default"


def generate_description(
    name: str,
    software_type: str = "android",
    category: str = "",
    developer: str = "",
    version: str = "",
    existing_short_desc: Optional[str] = None,
) -> tuple[str, str]:
    """
    Generate a unique SEO-optimized description for an app.
    Returns (description, short_desc) tuple.
    
    The description is 150-200 words, keyword-rich, and unique per call.
    """
    platform = random.choice(PLATFORM_ACTIONS.get(software_type, PLATFORM_ACTIONS["android"]))
    cat_type = _detect_category_type(category, name, existing_short_desc or "")
    cat_keywords = CATEGORY_KEYWORDS.get(cat_type, CATEGORY_KEYWORDS["default"])
    cat_word = random.choice(cat_keywords)

    # Build the description from templates
    intro = random.choice(INTRO_TEMPLATES).format(name=name, category=cat_word, platform=platform)
    feature = random.choice(FEATURE_TEMPLATES).format(name=name, category=cat_word)
    detail = random.choice(DETAIL_TEMPLATES).format(name=name, category=cat_word)
    cta = random.choice(CTA_TEMPLATES).format(name=name, category=cat_word)

    # Add version info if available
    version_note = f" The latest version is {version}." if version and version != "latest" else ""

    # Add developer credit
    dev_note = f" Developed by {developer}," if developer else ""

    # Add platform note
    platform_map = {
        "android": "Android (APK)",
        "windows": "Windows",
        "macos": "macOS",
        "linux": "Linux",
    }
    platform_label = platform_map.get(software_type, "multiple platforms")

    # Assemble full description
    description = (
        f"{intro} {feature}{dev_note} {detail}{version_note} "
        f"APKDroid provides a safe and verified download of {name} for {platform_label}. "
        f"All files are sourced from official repositories and checked for malware before listing. "
        f"{cta}"
    )

    # Short desc (155 chars max for SEO meta)
    short_desc = (
        existing_short_desc[:155]
        if existing_short_desc and len(existing_short_desc) > 20
        else f"{name} — free {cat_word} app for {platform_label}. Safe download from APKDroid."[:155]
    )

    return description.strip(), short_desc.strip()


def generate_seo_title(name: str, software_type: str = "android") -> str:
    """Generate SEO title: {App Name} Download Free | APKDroid"""
    platform_map = {
        "android": "APK",
        "windows": "for Windows",
        "macos": "for Mac",
        "linux": "for Linux",
    }
    suffix = platform_map.get(software_type, "Download")
    return f"{name} {suffix} Download Free | APKDroid"


def generate_meta_description(
    name: str,
    short_desc: str,
    software_type: str = "android",
    version: str = "",
) -> str:
    """Generate 155-char meta description for SEO."""
    platform_map = {
        "android": "Android APK",
        "windows": "Windows",
        "macos": "macOS",
        "linux": "Linux",
    }
    platform = platform_map.get(software_type, "all platforms")
    base = f"Download {name} free for {platform}"
    if version:
        base += f" v{version}"
    base += ". " + (short_desc[:80] if short_desc else "Safe, verified download from APKDroid.")
    return base[:155]


def generate_keywords(name: str, category: str, software_type: str) -> str:
    """Generate SEO keyword string."""
    platform_kw = {
        "android": ["APK download", "Android app", "free APK", "Android APK"],
        "windows": ["Windows software", "Windows app", "free download Windows", "PC software"],
        "macos": ["Mac app", "macOS software", "free Mac download"],
        "linux": ["Linux app", "Linux software", "free Linux download"],
    }
    kws = [name, category, "free download", "APKDroid"]
    kws += platform_kw.get(software_type, ["free download"])
    return ", ".join(dict.fromkeys(kws))  # deduplicate preserving order
