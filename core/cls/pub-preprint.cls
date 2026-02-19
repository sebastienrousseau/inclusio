%% Copyright (c) 2026 Sebastien Rousseau
%% Licensed under the MIT License
%% See LICENSE file for details
%%
%% pub-preprint.cls — Single-column journal preprint class
%% Double-spaced, line-numbered, wide margins for reviewer annotations.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{pub-preprint}[2026/02/17 Publications Preprint Class]

%% ── Options ─────────────────────────────────────────────────────────────
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{pub-base}}
\ProcessOptions\relax
\LoadClass[serif,letterpaper,12pt]{pub-base}

%% ── Additional packages ────────────────────────────────────────────────
\RequirePackage{lineno}
\RequirePackage{setspace}
\RequirePackage{url}
\RequirePackage{booktabs}
\RequirePackage{amsmath}

%% ── Geometry: wide margins for reviewer annotations ─────────────────────
\geometry{
  paper=letterpaper,
  top=1in,
  bottom=1in,
  left=1.25in,
  right=1.25in,
  headheight=14pt,
  headsep=25pt,
  footskip=30pt
}

%% ── Double spacing + line numbers ───────────────────────────────────────
\AtBeginDocument{%
  \doublespacing
  \linenumbers
}

%% ── Running headers: author (L) / title (R) ────────────────────────────
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0.4pt}
\fancyhead[L]{\small\itshape\@author}
\fancyhead[R]{\small\itshape\@title}
\fancyfoot[C]{\thepage}

%% ── Semantic macros: preprint-specific ──────────────────────────────────
\newcommand{\affiliation}[1]{\par\textit{#1}}
\newcommand{\keywords}[1]{\par\noindent\textbf{Keywords:} #1}
\newcommand{\correspondingauthor}[1]{%
  \par\noindent\textbf{Corresponding author:} #1%
}
\newcommand{\journaltarget}[1]{%
  \par\noindent\textit{Target journal: #1}%
}

%% ── Abstract ────────────────────────────────────────────────────────────
\renewenvironment{abstract}{%
  \begin{center}
    {\large\bfseries\scshape Abstract}
  \end{center}
  \begin{quote}\singlespacing
}{%
  \end{quote}
}

\endinput
