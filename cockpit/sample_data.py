"""Sample fixtures so the Cockpit can be built and demoed before `jf auth`.

These mimic the shape of the real connector outputs. Jobs use them only when
connectors are unauthenticated (config.guardrails.fall_back_to_sample). Every
sample is clearly fictional and marked sample=True so the UI can badge it.
"""

from __future__ import annotations

SAMPLE_CALENDAR = [
    {"start": "09:30", "summary": "Portal Cockpit sync", "location": "Zoom",
     "attendees": ["maher@meta.com", "boz@meta.com"]},
    {"start": "11:00", "summary": "Ads creative review", "location": "MPK 21 / 2-Lovelace",
     "attendees": ["team-ads@meta.com"]},
    {"start": "13:00", "summary": "1:1 with manager", "location": "Zoom", "attendees": ["manager@meta.com"]},
    {"start": "15:30", "summary": "Llama productivity guild", "location": "Workplace Room",
     "attendees": ["guild@meta.com"]},
]

SAMPLE_TOMORROW = [
    {"start": "10:00", "summary": "Design review: Cockpit tabs", "location": "Zoom", "attendees": []},
    {"start": "14:00", "summary": "Beehive + Cockpit demo to Saba", "location": "MPK", "attendees": []},
]

SAMPLE_UNREAD = [
    {"id": "sample1", "from": "Maher Saba <maher@meta.com>",
     "subject": "Re: Portal vibe-coding — can you demo Friday?",
     "snippet": "Loved the bee monitor. Could you show the productivity cockpit on a Portal this Friday?",
     "date": "07:42"},
    {"id": "sample2", "from": "Calendar <calendar@meta.com>",
     "subject": "Invitation: Ads creative review @ 11am",
     "snippet": "You have been invited to Ads creative review.", "date": "07:10"},
    {"id": "sample3", "from": "Workplace <noreply@meta.com>",
     "subject": "3 key updates from leadership", "snippet": "Boz posted a key update in RL FYI…",
     "date": "06:55"},
    {"id": "sample4", "from": "Jana Park <jana@meta.com>",
     "subject": "Quick question on the Atlas pitch deck",
     "snippet": "Do you have the latest numbers for the SMB market map?", "date": "Yesterday"},
]

SAMPLE_AWAITING = [
    {"id": "sent1", "to": "legal@meta.com", "subject": "Approval for personal-data policy note",
     "snippet": "Following up — do we have sign-off?", "sent": "3 days ago"},
    {"id": "sent2", "to": "jana@meta.com", "subject": "Atlas SMB numbers",
     "snippet": "Sent you the market map — let me know if it works.", "sent": "4 days ago"},
]

SAMPLE_DOCS = [
    {"name": "Portal_Productivity_Cockpit_Strategy.md", "owner": "Jo",
     "modifiedTime": "overnight", "webViewLink": "https://docs.google.com/document/d/strategy"},
    {"name": "Q3 planning — RL productivity", "owner": "manager@meta.com",
     "modifiedTime": "overnight", "webViewLink": "https://docs.google.com/document/d/q3"},
]

# A couple of past Top of Mind posts to learn the voice from (placeholder until
# Jo provides her real ones + the group).
SAMPLE_TOM_EXAMPLES = [
    "Top of Mind — week of June 9\n\nThis week was all about shipping the bee monitor end to end. "
    "Three things on my mind:\n1) Local-first AI is finally practical — Llama on-device handled the "
    "vision work with zero cloud.\n2) The Portal is a surprisingly good ambient surface.\n3) Next: "
    "turning the same pattern on my own workflow.\n\nGrateful to the RL FYI crowd for the nudge. More soon. 🐝",
    "Top of Mind — week of June 2\n\nShort one this week. Spent it heads-down on Atlas. Biggest "
    "lesson: pick the smallest demo that proves the whole pipeline, then widen. Onward.",
]

SAMPLE_MEETING_THREADS = [
    {"subject": "Re: Portal vibe-coding — can you demo Friday?", "from": "Maher Saba <maher@meta.com>"},
    {"subject": "Cockpit tab layout — feedback", "from": "Boz <boz@meta.com>"},
]

# A6 — weekly Workplace digest inputs
SAMPLE_KEY_UPDATES = [
    {"author": "Boz", "group": "RL FYI", "title": "Portal, possible again",
     "summary": "Reviving Portal as a home-hub; ADB access open to FTEs for vibe-coding."},
    {"author": "Maher Saba", "group": "Claude Code Community", "title": "The 'Joe' build",
     "summary": "Portal front-end ⇄ Mac brain, fully local, ADB deploy."},
    {"author": "Leadership", "group": "RL Org", "title": "H2 priorities",
     "summary": "Doubling down on local-first AI experiences across RL surfaces."},
]
SAMPLE_TOP_POSTS = [
    {"author": "Jana Park", "group": "AI Productivity", "reactions": 142,
     "title": "How I cut my meeting load 30% with a local agent"},
    {"author": "Design Systems", "group": "RL Design", "reactions": 98,
     "title": "Ambient surfaces: a pattern library for home devices"},
]

# A8 — notification triage inputs (mix of action-needed and FYI)
SAMPLE_NOTIFICATIONS = [
    {"kind": "mention", "from": "Maher Saba", "context": "RL FYI", "action": True,
     "text": "@Jo can you demo the cockpit Friday?"},
    {"kind": "comment", "from": "Boz", "context": "Cockpit tab layout doc", "action": True,
     "text": "Left 2 comments — can you take a look before Thu?"},
    {"kind": "reaction", "from": "12 people", "context": "your bee monitor post", "action": False,
     "text": "reacted to your post"},
    {"kind": "group_post", "from": "AI Productivity", "context": "weekly roundup", "action": False,
     "text": "New weekly roundup posted"},
]

# A10 — doc → action items (sample doc text to extract from)
SAMPLE_DOC_TEXT = (
    "Cockpit planning notes — 2026-06-18\n\n"
    "Decisions: ship the morning brief slice first; keep everything local on Llama.\n"
    "Jo will confirm the Top of Mind group by Friday. Maher to share the Portal ADB guide. "
    "Boz approved the home-hub direction. Next: wire real connectors after jf auth, then add "
    "the weekly Workplace digest. Open question: voice layer now or later (deferred)."
)
