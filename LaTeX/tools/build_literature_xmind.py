"""
Build Literature_map_ECU_RV.xmind from XMind_template.xmind (XMind 24 JSON).

Horizontal map: central topic → pillars → sub-approaches → citation → summary.
Includes every research-relevant entry from sources.bib (RV / IoT / automotive /
trust / methodology). Legacy speech & cyberbullying template entries are omitted.
"""
from __future__ import annotations

import json
import shutil
import uuid
import zipfile
from pathlib import Path

# (sub-branch title, citation lines, summary) — order = appearance in map
PILLARS: list[tuple[str, list[tuple[str, str, str]]]] = [
    (
        "Survey, IoT & attestation",
        [
            (
                "IoT security landscape",
                "Williams et al. (2022)",
                "Internet Things",
                "Surveys IoT security with emphasis on emerging technologies. "
                "Contextualises attack surface and constrained devices for connected ECUs.",
            ),
            (
                "Formal FV&V for IoT",
                "Krichen (2023)",
                "Applied Sciences",
                "Taxonomy of formal verification and validation for IoT. Contrasts "
                "exhaustive analysis with lighter, runtime-oriented assurance.",
            ),
            (
                "Remote attestation (IoT)",
                "Kuang et al. (2021)",
                "Comput. Secur.",
                "Survey of remote attestation in IoT: attacks, countermeasures, and "
                "prospects; complements trust and integrity discussions for constrained nodes.",
            ),
        ],
    ),
    (
        "Runtime verification",
        [
            (
                "Automata & context-aware monitoring",
                "Zhang et al. (2024)",
                "J. Cloud Comput.",
                "Automata-theoretic context-aware online monitoring for autonomous "
                "vehicle safety; composes environment models with runtime checks.",
            ),
            (
                "Digital twin & rule-based RV",
                "de Hoz et al. (2022)",
                "LNCS",
                "IoT digital twin for cyber defence with rule-based runtime verification "
                "over parametric network events; selective observation, low overhead.",
            ),
            (
                "Algebraic monitoring framework",
                "Jaksic et al. (2018)",
                "arXiv",
                "Algebraic view of RV (monoidal/semiring structures); incremental and "
                "quantitative monitoring for evolving specifications.",
            ),
            (
                "Middleware & external oracles",
                "Saadat et al. (2024)",
                "EPTCS",
                "ROSMonitoring 2.0 extends RV to ROS services and ordered topics; "
                "composes middleware with external oracles such as LARVA.",
            ),
            (
                "Resource-constrained platforms",
                "Clemens et al. (2018)",
                "MILCOM",
                "Runtime state verification on resource-constrained platforms; "
                "relevant to lightweight monitors on ECU-class hardware.",
            ),
            (
                "IoT-focused RV solution",
                "Incki & Ari (2018)",
                "IEEE Access",
                "Novel runtime verification solution tailored to IoT systems; "
                "illustrates domain-specific monitoring architectures.",
            ),
            (
                "RV containers (pub/sub)",
                "Mehran & Ulus (2024)",
                "arXiv",
                "Runtime verification containers for publish/subscribe networks; "
                "composition and isolation of monitors in event-driven systems.",
            ),
            (
                "High-assurance RV challenges",
                "Goodloe (2023)",
                "Discussion paper",
                "Challenges in high-assurance runtime verification; frames rigour, "
                "assurance cases, and engineering trade-offs for monitors.",
            ),
        ],
    ),
    (
        "Automotive testing & hardware trust",
        [
            (
                "Cybersecurity V&V practice",
                "Ekert et al. (2021)",
                "J. UCS",
                "Automotive cybersecurity V&V testing; structured campaigns, norms, "
                "and network/ECU-focused assurance.",
            ),
            (
                "HTA authentication",
                "Lorych & Plappert (2024)",
                "ARES",
                "Hardware trust anchor authentication for updatable IoT devices; "
                "secure update and authentication under resource constraints.",
            ),
            (
                "Automotive HTA evaluation",
                "Plappert et al. (2023)",
                "Comput. Secur.",
                "Evaluates HTA designs against automotive requirements for "
                "constrained controllers.",
            ),
            (
                "Hybrid remote attestation",
                "Aman et al. (2020)",
                "IEEE IoT J.",
                "HAtt: hybrid remote attestation for IoT with high availability; "
                "PUF-oriented checks and energy-aware protocols.",
            ),
        ],
    ),
    (
        "Tools, trustworthy RV & methods",
        [
            (
                "LARVA (monitoring tool)",
                "Colombo et al. (2009)",
                "SEFM",
                "LARVA: safer monitoring of real-time Java; foundational oracle for "
                "timed, specification-driven runtime verification.",
            ),
            (
                "RV for trustworthy computing",
                "Abela et al. (2023)",
                "AREA",
                "Trustworthy RV including ROSMonitoring with LARVA as oracle; "
                "event forwarding and TEE-oriented robotic security context.",
            ),
            (
                "Research methodology (onion)",
                "Saunders et al. (2016)",
                "Pearson (book)",
                "Research Methods for Business Students; frames research onion, "
                "aims, and quasi-experimental study structure.",
            ),
        ],
    ),
]


def uid() -> str:
    return str(uuid.uuid4())


def summary_child(text: str, x: float, y: float) -> dict:
    return {
        "id": uid(),
        "title": f"Summary:\n{text}",
        "position": {"x": x, "y": y},
    }


def paper(title: str, summary_text: str, paper_xy: tuple[float, float], sum_xy: tuple[float, float]) -> dict:
    return {
        "id": uid(),
        "title": title,
        "position": {"x": paper_xy[0], "y": paper_xy[1]},
        "children": {"attached": [summary_child(summary_text, sum_xy[0], sum_xy[1])]},
    }


def sub_branch(title: str, papers: list[dict], sub_xy: tuple[float, float]) -> dict:
    sx, sy = sub_xy
    return {
        "id": uid(),
        "title": title,
        "position": {"x": sx, "y": sy},
        "children": {"attached": papers},
    }


def pillar(title: str, sub_branches: list[dict], pillar_xy: tuple[float, float]) -> dict:
    px, py = pillar_xy
    return {
        "id": uid(),
        "title": title,
        "position": {"x": px, "y": py},
        "children": {"attached": sub_branches},
    }


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    template_zip = Path(r"c:\Users\brama\Downloads\XMind_template.xmind")
    out_xmind = repo.parent / "Literature_map_ECU_RV.xmind"
    work = repo / "tools" / "_xmind_build"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    with zipfile.ZipFile(template_zip, "r") as zf:
        zf.extractall(work)

    with open(work / "content.json", encoding="utf-8") as f:
        template = json.load(f)

    sheet = template[0]
    theme = sheet.get("theme")
    extensions = sheet.get("extensions")

    X1, X2, X3, X4 = -620, -380, -120, 200
    pillar_x = -620
    pillar_spacing_y = 115

    attached_pillars: list[dict] = []

    for pillar_title, items in PILLARS:
        n = len(items)
        total_height = (n - 1) * pillar_spacing_y
        y0 = -total_height / 2
        sub_branches: list[dict] = []
        for i, (sub_title, pline, venue, summ) in enumerate(items):
            y = y0 + i * pillar_spacing_y
            cite_title = f"{pline}\n{venue}"
            sub_branches.append(
                sub_branch(
                    sub_title,
                    [paper(cite_title, summ, (X3, y), (X4, y))],
                    (X2, y),
                )
            )
        mid_y = (sub_branches[0]["position"]["y"] + sub_branches[-1]["position"]["y"]) / 2
        attached_pillars.append(pillar(pillar_title, sub_branches, (pillar_x, mid_y)))

    # Spread pillars vertically so branches do not overlap between pillars
    offsets = [-520, -80, 380, -980]
    for i, p in enumerate(attached_pillars):
        dy = offsets[i]
        p["position"]["y"] += dy
        for sb in p["children"]["attached"]:
            sb["position"]["y"] += dy
            for pap in sb["children"]["attached"]:
                pap["position"]["y"] += dy
                for sc in pap["children"]["attached"]:
                    sc["position"]["y"] += dy

    root_id = uid()
    root = {
        "id": root_id,
        "class": "topic",
        "title": (
            "Minimal, resource-bounded runtime verification\n"
            "for a safety-critical automotive ECU"
        ),
        "titleUnedited": False,
        "structureClass": "org.xmind.ui.logic.right",
        "children": {"attached": attached_pillars},
    }

    if extensions:
        for ext in extensions:
            if ext.get("provider") == "org.xmind.ui.skeleton.structure.style":
                ext.setdefault("content", {})["centralTopic"] = "org.xmind.ui.logic.right"

    sheet["id"] = uid()
    sheet["class"] = "sheet"
    sheet["rootTopic"] = root
    sheet["relationships"] = []
    sheet["title"] = "Literature map — full bibliography (RV/IoT)"
    sheet["topicOverlapping"] = "overlap"
    sheet["topicPositioning"] = "free"
    if extensions is not None:
        sheet["extensions"] = extensions
    if theme is not None:
        sheet["theme"] = theme

    with open(work / "content.json", "w", encoding="utf-8") as f:
        json.dump([sheet], f, ensure_ascii=False, indent=2)

    with zipfile.ZipFile(out_xmind, "w", zipfile.ZIP_DEFLATED) as zout:
        for p in sorted(work.rglob("*")):
            if p.is_file() and p.suffix != ".xmind":
                zout.write(p, arcname=p.relative_to(work).as_posix())

    shutil.rmtree(work)
    print(f"Wrote: {out_xmind} ({sum(len(p[1]) for p in PILLARS)} sources)")


if __name__ == "__main__":
    main()
