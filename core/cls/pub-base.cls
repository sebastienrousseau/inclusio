%% Copyright (c) 2026 Sebastien Rousseau
%% Licensed under the MIT License
%% See LICENSE file for details
%%
%% pub-base.cls — Publications Base Class
%% All formatting decisions originate here. Content files use semantic macros only.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{pub-base}[2026/02/17 Publications Base Class]

%% ── Build mode options ──────────────────────────────────────────────────
\newif\ifdraftmode   \draftmodefalse
\newif\ifsubmissionmode \submissionmodefalse
\newif\iffinalmode   \finalmodefalse

\DeclareOption{draft}{\draftmodetrue}
\DeclareOption{submission}{\submissionmodetrue}
\DeclareOption{final}{\finalmodetrue}

%% ── Tagging / accessibility options ─────────────────────────────────────
%% [tagged] is a contract assertion: the author has called
%% \DocumentMetadata{...} BEFORE \documentclass, and expects this build
%% to emit a tagged PDF/UA-2 + PDF/A-4 artefact. If \DocumentMetadata
%% was not called, the class errors loudly rather than silently
%% producing an untagged PDF.
%%
%% [final-untagged] is the explicit opt-out for documents that haven't
%% migrated yet. Use it during the Sprint 2 retrofit window only.
\newif\ifpub@tagged    \pub@taggedfalse
\newif\ifpub@untagged  \pub@untaggedfalse
\DeclareOption{tagged}{\pub@taggedtrue}
\DeclareOption{final-untagged}{\pub@untaggedtrue\finalmodetrue}

%% Snapshot whether \DocumentMetadata was called BEFORE \documentclass.
%% This must happen as early as possible because pdfx (loaded later by
%% pub-metadata.sty's legacy branch) internally invokes \DocumentMetadata
%% as part of its setup, which would flip \IfDocumentMetadataTF from
%% FALSE to TRUE and silently disarm the [tagged] contract check.
\providecommand\IfDocumentMetadataTF[2]{#2}
\newif\ifpub@hadDocumentMetadata \pub@hadDocumentMetadatafalse
\IfDocumentMetadataTF{\pub@hadDocumentMetadatatrue}{}

%% ── Typography options (forwarded to pub-typography) ────────────────────
\newif\ifpub@serif \pub@seriffalse
\DeclareOption{sans}{\pub@seriffalse}
\DeclareOption{serif}{\pub@seriftrue}

%% ── Paper size options ──────────────────────────────────────────────────
\newif\ifpub@letter \pub@letterfalse
\DeclareOption{a4paper}{\pub@letterfalse}
\DeclareOption{letterpaper}{\pub@lettertrue}

%% ── Font size option ────────────────────────────────────────────────────
\def\pub@fontsize{11pt}
\DeclareOption{10pt}{\def\pub@fontsize{10pt}}
\DeclareOption{11pt}{\def\pub@fontsize{11pt}}
\DeclareOption{12pt}{\def\pub@fontsize{12pt}}

%% Pass everything else to article
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax

%% ── Load base class ─────────────────────────────────────────────────────
\ifpub@letter
  \LoadClass[\pub@fontsize,letterpaper]{article}
\else
  \LoadClass[\pub@fontsize,a4paper]{article}
\fi

%% ── Ensure images and links render even in draft mode ─────────────────
%% Global "draft" leaks to graphicx (bounding boxes only) and hyperref
%% (disabled links).  Force both to "final" so images and links always work.
\PassOptionsToPackage{final}{graphicx}
\PassOptionsToPackage{final}{hyperref}

%% ── Load core style packages ────────────────────────────────────────────
\RequirePackage{pub-colors}

\ifpub@serif
  \RequirePackage[serif]{pub-typography}
\else
  \RequirePackage[sans]{pub-typography}
\fi

\RequirePackage{pub-buildmodes}
\RequirePackage{pub-metadata}
\RequirePackage{pub-common}

%% ── Common packages ─────────────────────────────────────────────────────
\RequirePackage{geometry}
\RequirePackage{fix-cm}         % Allow arbitrary font sizes (avoids substitution warnings)
\IfFileExists{microtype.sty}{\RequirePackage{microtype}}{} % Better kerning/protrusion when available
\RequirePackage[american]{babel}
\RequirePackage{listings}       % Code listings — loaded after babel for French ldf support
\RequirePackage{etoolbox}
\RequirePackage{xpatch}
\RequirePackage{array}
\RequirePackage{titlesec}

%% ── tagpdf version advisory ────────────────────────────────────────────
%% tagpdf v1.0b (2026-04-24) is the first non-beta candidate release; it
%% gates ~1000 extension packages as accessibility-tested. Earlier 0.x
%% releases have known bugs in PDF/UA-2 structure trees that surface as
%% silent FAILs in veraPDF.
%%
%% We do NOT \RequirePackage{tagpdf} here: tagpdf must only be loaded
%% by \DocumentMetadata (kernel-engaged path), otherwise it errors with
%% "PDF resource management is no active". Instead, this AtBeginDocument
%% hook emits a clear warning when an old tagpdf rev was engaged by
%% \DocumentMetadata. The veraPDF audit (`make audit --strict`) is the
%% authoritative gate; the warning here is a developer-time canary.
\AtBeginDocument{%
  \ifpub@tagged
    \@ifpackagelater{tagpdf}{2026/04/24}{}{%
      \PackageWarning{pub-base}{%
        Outdated tagpdf detected. Sprint-3 PDF/UA-2 gate expects
        tagpdf v1.0 (2026-04-24) or later.\MessageBreak
        Upgrade via `tlmgr update tagpdf` to avoid silent veraPDF
        FAILs on structure-tree edge cases%
      }%
    }%
  \fi
}

%% ── Tagged-PDF contract check ──────────────────────────────────────────
%% Use the EARLY snapshot (\ifpub@hadDocumentMetadata) taken at option
%% processing time, not a live re-query of \IfDocumentMetadataTF.
%% pdfx (loaded by pub-metadata.sty on the legacy branch) calls
%% \DocumentMetadata internally, which would otherwise mask the missing
%% explicit-author call.
\ifpub@tagged
  \ifpub@hadDocumentMetadata
    %% Author engaged \DocumentMetadata. Trust the kernel's tagging.
    \AtBeginDocument{%
      \@ifundefined{tagpdfsetup}{}{%
        \tagpdfsetup{activate,interwordspace=true}%
      }%
    }%
  \else
    \ClassError{pub-base}{%
      Class option [tagged] requires \string\DocumentMetadata{...} before
      \string\documentclass{...}.\MessageBreak
      Add a preamble such as:\MessageBreak
      \space\space\string\DocumentMetadata{lang=en-GB, pdfstandard=ua-2,
        pdfstandard=a-4}\MessageBreak
      \space\space\string\documentclass[final,tagged]{pub-paper}\MessageBreak
      Or remove [tagged] and use [final-untagged] during migration.%
    }{See docs/tagged-pdf.md in the inclusio repository.}%
  \fi
\else
  %% Legacy / non-tagged path. If tagpdf happens to be loaded later by
  %% the document, still apply baseline setup (non-breaking).
  \IfFileExists{tagpdf.sty}{%
    \AtBeginDocument{%
      \@ifundefined{tagpdfsetup}{}{\tagpdfsetup{activate,interwordspace=true}}%
    }%
  }{}%
\fi

%% ── Common document variables ───────────────────────────────────────────
\def\@subtitle{}
\def\@documentversion{\documentVersion}
\newcommand{\subtitle}[1]{\def\@subtitle{#1}}
\newcommand{\setDocumentVersion}[1]{\def\@documentversion{#1}}

\endinput
