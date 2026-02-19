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

%% Optional PDF tagging support (non-breaking): if tagpdf is loaded by the
%% document/toolchain, apply baseline setup.
\IfFileExists{tagpdf.sty}{%
    \AtBeginDocument{%
    \@ifundefined{tagpdfsetup}{}{\tagpdfsetup{activate,interwordspace=true}}%
  }%
}{}

%% ── Common document variables ───────────────────────────────────────────
\def\@subtitle{}
\def\@documentversion{\documentVersion}
\newcommand{\subtitle}[1]{\def\@subtitle{#1}}
\newcommand{\setDocumentVersion}[1]{\def\@documentversion{#1}}

\endinput
