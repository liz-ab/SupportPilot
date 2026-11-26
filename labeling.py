"""Shared text cleaning and rule definitions used to build and audit the dataset."""
import re

CATEGORIES = ["Network", "VPN", "Password", "Software", "Hardware", "System"]
SEVERITIES = ["Critical", "High", "Medium", "Low"]

# Whole-word patterns that identify the main problem area of a ticket.
CATEGORY_RULES = {
    "VPN": r"\b(vpn|globalprotect|anyconnect|pulse secure|forticlient|remote access tunnel)\b",
    "Password": (
        r"\b(password|passwords|passwort|kennwort|passcode|pwd|credentials?|account (is )?locked|"
        r"locked out|unlock (my |the )?account|account unlock|password reset|reset (my |the )?(password|pin))\b"
    ),
    "Network": (
        r"\b(wifi|wi-fi|wlan|wireless|lan|ethernet|network|internet|dns|dhcp|ip address|router|"
        r"bandwidth|latency|connectivity|no connection|cannot connect to the (network|internet)|"
        r"firewall|packet loss|network drive)\b"
    ),
    "Hardware": (
        r"\b(laptop|desktop|monitor|keyboard|mouse|printer|printers|scanner|docking station|headset|"
        r"battery|screen|hard drive|toner|projector|webcam|usb|charger|speaker|microphone|cable|"
        r"hardware|touchpad|display|cartridge|handset|bluetooth)\b"
    ),
    "Software": (
        r"\b(install|installation|installed|software|license|licence|outlook|excel|word|powerpoint|office|"
        r"application|app|update|upgrade|plugin|browser|chrome|firefox|sap|erp|crm|teams|skype|"
        r"sharepoint|crashes|crashing|error message)\b"
    ),
    "System": (
        r"\b(operating system|windows|boot|booting|startup|blue screen|bsod|reboot|restart|freezes|"
        r"freezing|frozen|hangs|hanging|server|servers|memory|cpu|disk space|patch|bios|virtual machine|"
        r"vm|system (down|crash|error|failure)|slow(ness)?|performance|kernel|reimage|re-image|"
        r"crash(ed)? on startup)\b"
    ),
}

SEVERITY_RULES = {
    "Critical": (
        r"\b(outage|outages|down for (all|everyone)|all users|entire (company|office|site|team|department)|"
        r"company[- ]wide|production (is )?down|server (is )?down|site (is )?down|website downtime|downtime|"
        r"ransomware|malware|virus|security (breach|incident)|hacked|data loss|multiple (users|services)|"
        r"whole (office|team)|complete failure|total failure|hard down|overheating|"
        r"business critical|major incident|are down|severe (event|disruption|incident))\b"
    ),
    "High": (
        r"\b(urgent|urgently|asap|immediately|importance high|high priority|priority|cannot work|can ?not work|"
        r"can'?t work|unable to work|not able to work|blocked|blocking|client meeting|customer meeting|presentation|"
        r"deadline|critical|important|impacting (several|multiple)|right now|emergency|business stopped|full production|losing|stolen|"
        r"disk space|stopped|restart the server|please restart)\b"
    ),
    "Medium": (
        r"\b(error|issue|issues|problem|problems|not working|doesn'?t work|does not work|not work|failed|failing|"
        r"failure|slow|slowness|cannot|can'?t|can not|unable|broken|crash|crashes|freezes|stuck|not responding|"
        r"intermittent|disconnects?|disconnected|dropping|drops|invalid|not able|timeouts?|lag|delays?|"
        r"will not|won'?t|not allow|locked)\b"
    ),
}

# Routine service requests (resets, unlocks, installs) are low severity when nothing is reported broken.
ROUTINE_REQUEST = (r"\b(reset|unlock|install|installation|upgrade|activate|activation|create|creation|replace|"
                   r"replacement|provide|request|requested|need|needed|add|change|expired|expiring|expires|"
                   r"forgot|forgotten|update)\b")

_NOISE = [
    (r"_x000d_", " "),
    (r"\\n|\\r", " "),
    (r"received from:\s*\S+", " "),
    (r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", " "),
    (r"https?://\S+|www\.\S+", " "),
    (r"\{[^}]*\}|<[^>]+>", " "),
    (r"\b(dear|hello|hi|hallo|good (morning|afternoon)|thanks|thank you|best regards|kind regards|regards|"
     r"greetings|sincerely|team|support team|customer support)\b", " "),
    (r"\b[a-z]{2,}\d{4,}\b|\b\d{5,}\b", " "),
    (r"\b(sent|re|fw|fwd)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", " "),
    (r"\bsent (monday|tuesday|wednesday|thursday|friday)\b", " "),
]


def clean_text(text):
    """Normalise raw ticket text: strip mail headers, addresses, greetings and ids."""
    text = str(text).lower()
    for pattern, repl in _NOISE:
        text = re.sub(pattern, repl, text)
    text = re.sub(r"[^a-z0-9'\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return dedupe_halves(text)


def dedupe_halves(text):
    """Many helpdesk tickets repeat the title inside the body; drop the repeat."""
    words = text.split()
    n = len(words)
    for size in range(n // 2, 2, -1):
        if words[:size] == words[size:2 * size]:
            return " ".join(words[:size] + words[2 * size:])
    return text


_ENGLISH = set("the a an is are was were to of and in on for with my i it not cannot can this that have has "
               "be please you we me when after from at but no do does am our your".split())


def is_english(text):
    words = text.split()
    if len(words) < 4:
        return False
    hits = sum(w in _ENGLISH for w in words)
    return hits / len(words) >= 0.18


def match_categories(text):
    return [name for name, pat in CATEGORY_RULES.items() if re.search(pat, text)]


def rule_category(text, headline_chars=220):
    """Return a category only when the ticket headline points to exactly one area."""
    found = match_categories(text[:headline_chars])
    if len(found) == 1:
        return found[0]
    # VPN and Password are specific enough to win over generic network wording.
    for specific in ("VPN", "Password"):
        if specific in found:
            return specific
    return None


STRONG_PROBLEM = (r"\b(error|not working|doesn'?t work|does not work|not work|failed|failing|failure|cannot|can'?t|"
                  r"can not|unable|broken|crash|crashes|freezes|stuck|not responding|disconnects?|disconnected|"
                  r"invalid|not able|timeouts?|slow|slowness|will not|won'?t|not allow|dropping|intermittent)\b")
WEAK_PROBLEM = r"\b(issue|issues|problem|problems|locked|lag|delays?|drops)\b"


def rule_severity(text):
    if re.search(SEVERITY_RULES["Critical"], text):
        return "Critical"
    if re.search(SEVERITY_RULES["High"], text):
        return "High"
    if re.search(STRONG_PROBLEM, text):
        return "Medium"
    if re.search(ROUTINE_REQUEST, text):
        return "Low"
    if re.search(WEAK_PROBLEM, text):
        return "Medium"
    return "Low"


# Tickets about these business areas are not IT-support issues; they are dropped.
OFF_DOMAIN = (r"\b(medical|hospital|healthcare|health care|patient|marketing|campaign|investment|financial|"
              r"finance firm|saas|analytics|branding|seo|brand|hearing aid|agency|revenue|pricing|quote|"
              r"data breach|data leak|data security)\b")


def is_off_domain(text):
    return bool(re.search(OFF_DOMAIN, text))
