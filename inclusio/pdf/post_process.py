# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Post-process a compiled PDF: XMP metadata, accessibility, encryption.

The public surface here is three functions:

- `build_xmp_xml(...)` — assemble a hand-crafted XMP packet with all
  Sprint-1 fields (Adobe-compatible). Used only on the legacy
  untagged path; the Sprint-5 tagged path trusts the kernel's XMP.
- `apply_encryption(pdf, pdf_path, content_hash)` — save *pdf* with
  AES-256 + accessibility-friendly permission flags. Opt-in via
  `secure_pdf: true` in `meta.documents.<id>`.
- `post_process_pdf(pdf_path, doc_id, doc_config, meta)` — the
  orchestrator. Inspects the PDF, dispatches to the tagged or
  legacy path, and saves.

All three are pikepdf-dependent at call time but the module is
importable without pikepdf installed; `post_process_pdf` simply
returns early when the import fails, leaving the LaTeX-written
metadata in place.
"""

from __future__ import annotations

import hashlib


def build_xmp_xml(
    title,
    author_name,
    subject,
    description,
    keywords,
    copyright_text,
    copyright_url,
    author_role,
    producer,
    ai_disclosure="",
):
    """Build a properly formatted XMP XML packet for Adobe compatibility.

    Uses explicit namespace declarations on rdf:Description and proper
    RDF containers (rdf:Alt for language alternatives, rdf:Seq for
    ordered lists, rdf:Bag for unordered sets) so that Adobe Acrobat
    reads every field correctly.

    Sprint 5 (S5.1): when *ai_disclosure* is non-empty, it is appended
    to the dc:description text after a separator, per the STM Sept-2025
    Generative-AI Disclosure classification. STM portals expected to
    enforce this 2026-Q4 onward — emitting the field early gives papers
    a smooth migration path without re-stamping the PDF.
    """
    from xml.sax.saxutils import escape

    t = escape(title)
    a = escape(author_name)
    s = escape(subject)
    # Append AI disclosure to description when present. Separator chosen
    # so Adobe's Description panel renders both lines cleanly.
    if ai_disclosure:
        description = f"{description}\n\nAI disclosure: {ai_disclosure}".strip()
    d = escape(description)
    k = escape(keywords)
    cr = escape(copyright_text)
    cu = escape(copyright_url) if copyright_url else ""
    ar = escape(author_role)
    p = escape(producer)

    web_stmt = (f"      <xmpRights:WebStatement>{cu}</xmpRights:WebStatement>\n") if cu else ""

    xmp = (
        '<?xpacket begin="\xef\xbb\xbf" '
        'id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        "  <rdf:RDF xmlns:rdf="
        '"http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '    <rdf:Description rdf:about=""\n'
        '        xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
        '        xmlns:pdf="http://ns.adobe.com/pdf/1.3/"\n'
        '        xmlns:xmp="http://ns.adobe.com/xap/1.0/"\n'
        "        xmlns:xmpRights="
        '"http://ns.adobe.com/xap/1.0/rights/"\n'
        "        xmlns:photoshop="
        '"http://ns.adobe.com/photoshop/1.0/"\n'
        "        xmlns:pdfuaid="
        '"http://www.aiim.org/pdfua/ns/id/">\n'
        "      <dc:title>\n"
        "        <rdf:Alt>\n"
        f'          <rdf:li xml:lang="x-default">{t}</rdf:li>\n'
        "        </rdf:Alt>\n"
        "      </dc:title>\n"
        "      <dc:creator>\n"
        "        <rdf:Seq>\n"
        f"          <rdf:li>{a}</rdf:li>\n"
        "        </rdf:Seq>\n"
        "      </dc:creator>\n"
        "      <dc:subject>\n"
        "        <rdf:Bag>\n"
        f"          <rdf:li>{s}</rdf:li>\n"
        "        </rdf:Bag>\n"
        "      </dc:subject>\n"
        "      <dc:description>\n"
        "        <rdf:Alt>\n"
        f'          <rdf:li xml:lang="x-default">{d}</rdf:li>\n'
        "        </rdf:Alt>\n"
        "      </dc:description>\n"
        "      <dc:rights>\n"
        "        <rdf:Alt>\n"
        f'          <rdf:li xml:lang="x-default">{cr}</rdf:li>\n'
        "        </rdf:Alt>\n"
        "      </dc:rights>\n"
        f"      <pdf:Keywords>{k}</pdf:Keywords>\n"
        f"      <pdf:Producer>{p}</pdf:Producer>\n"
        "      <xmp:CreatorTool>LaTeX with hyperref"
        "</xmp:CreatorTool>\n"
        "      <xmpRights:Marked>True</xmpRights:Marked>\n"
        f"{web_stmt}"
        f"      <photoshop:AuthorsPosition>{ar}"
        f"</photoshop:AuthorsPosition>\n"
        f"      <photoshop:CaptionWriter>{a}"
        f"</photoshop:CaptionWriter>\n"
        "      <pdfuaid:part>1</pdfuaid:part>\n"
        "    </rdf:Description>\n"
        "  </rdf:RDF>\n"
        "</x:xmpmeta>\n" + " " * 2048 + "\n"
        '<?xpacket end="w"?>'
    )
    return xmp


def post_process_pdf(pdf_path, doc_id, doc_config, meta):
    """Apply metadata, accessibility tagging, and encryption in one pass.

    Writes XMP as explicit XML (not via pikepdf's open_metadata) so that
    Adobe Acrobat reads every field — Author Title, Description Writer,
    Copyright Status/Notice/URL, PDF/UA compliance.
    """
    try:
        import pikepdf
    except ImportError:
        return  # pikepdf optional — metadata from hyperref still works

    author = meta.get("author", {})
    author_name = author.get("name", "")
    author_role = author.get("role", "")
    copyright_text = author.get("copyright", "")
    copyright_url = author.get("copyright_url", "")
    producer = author.get("publisher", author_name)
    title = doc_config.get("title", doc_id)
    subject = doc_config.get("subject", "")
    description = doc_config.get("description", "")
    keywords = doc_config.get("keywords", "")
    # Sprint 5 (S5.1): optional AI-disclosure metadata per STM Sept-2025.
    # Accepted at doc-config OR meta level (per-doc wins). Empty string
    # is the silent default — no AI assistance to declare.
    ai_disclosure = doc_config.get("ai_disclosure") or meta.get("ai_disclosure") or ""

    content_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16]

    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        # Sprint 5 (S5.4): when the PDF is structurally tagged (i.e. the
        # LaTeX kernel's tagging project ran via \DocumentMetadata), the
        # kernel already wrote a fully PDF/UA-2 + PDF/A-4f compliant XMP
        # packet. Overwriting it with our Sprint-1-era build_xmp_xml()
        # strips the kernel's pdfaid:part=4 + pdfuaid:part=2 markers and
        # the audit fails on every flavour. Detect this case and skip
        # the XMP + docinfo overwrites entirely — the kernel owns
        # metadata in the tagged path.
        is_tagged_pdf = "/StructTreeRoot" in pdf.Root

        # ── 1. XMP metadata as hand-crafted XML (legacy path only) ────
        if is_tagged_pdf:
            # Tagged path: trust the kernel's XMP + docinfo. We still
            # apply AES-256 if explicitly opted in, but skip every other
            # write so the PDF/UA-2 + PDF/A-4f conformance survives.
            if doc_config.get("secure_pdf", False):
                apply_encryption(pdf, pdf_path, content_hash)
            else:
                pdf.save(pdf_path)
            return

        xmp_xml = build_xmp_xml(
            title,
            author_name,
            subject,
            description,
            keywords,
            copyright_text,
            copyright_url,
            author_role,
            producer,
            ai_disclosure=ai_disclosure,
        )
        pdf.Root["/Metadata"] = pdf.make_indirect(
            pikepdf.Stream(pdf, xmp_xml.encode("utf-8")),
        )
        pdf.Root["/Metadata"]["/Type"] = pikepdf.Name("/Metadata")
        pdf.Root["/Metadata"]["/Subtype"] = pikepdf.Name("/XML")

        # ── 2. Document info dictionary (legacy, read by Adobe) ─────
        pdf.docinfo["/Title"] = title
        pdf.docinfo["/Author"] = author_name
        pdf.docinfo["/Subject"] = subject
        pdf.docinfo["/Keywords"] = keywords
        pdf.docinfo["/Creator"] = "LaTeX with hyperref"
        pdf.docinfo["/Producer"] = producer

        # ── 3. Accessibility catalog entries ────────────────────────
        # Only advertise logical tagging when a structure tree exists.
        if "/StructTreeRoot" not in pdf.Root and "/MarkInfo" in pdf.Root:
            del pdf.Root["/MarkInfo"]
        if "/Lang" not in pdf.Root:
            pdf.Root["/Lang"] = pikepdf.String("en")
        if "/ViewerPreferences" not in pdf.Root:
            pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(
                {
                    "/DisplayDocTitle": True,
                }
            )

        # ── 4. Encryption (AES-256) ────────────────────────────────
        # Default changed from True → False in Sprint 5 (S5.4): AES-256
        # encryption is incompatible with PDF/A-4f and PDF/UA-2 (the
        # archival standards forbid /Encrypt in the trailer), so the
        # tagged-PDF gate fails on every encrypted artefact. Documents
        # that genuinely need encryption (internal-only patents,
        # protected drafts) must opt in via `secure_pdf: true` in
        # meta.documents.<id>. The private content repo already sets
        # this explicitly on every doc that needs it.
        if doc_config.get("secure_pdf", False):
            apply_encryption(pdf, pdf_path, content_hash)
        else:
            pdf.save(pdf_path)


def apply_encryption(pdf, pdf_path, content_hash):
    """Save *pdf* with AES-256 encryption + standard accessibility perms.

    Extracted from `post_process_pdf` so the tagged-PDF early-return
    path can share the encryption logic. Permissions are tuned for
    a published archival doc: highres + lowres print allowed, extract
    + modify denied, accessibility allowed (so screen readers can
    still read the document text).
    """
    import pikepdf  # local import keeps the module pikepdf-optional

    perms = pikepdf.Permissions(
        print_highres=True,
        print_lowres=True,
        extract=False,
        modify_annotation=False,
        modify_form=False,
        modify_assembly=False,
        modify_other=False,
        accessibility=True,
    )
    pdf.save(
        pdf_path,
        encryption=pikepdf.Encryption(
            owner=content_hash,
            user="",
            R=6,
            allow=perms,
            metadata=False,
        ),
    )
