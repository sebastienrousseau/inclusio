%% Copyright (c) 2026 Sebastien Rousseau
%% Licensed under the MIT License
%% See LICENSE file for details
%%
%% pub-arxiv.cls — Strict ArXiv-compliant paper class
%% Computer Modern only, ArXiv-safe packages, metadata macros.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{pub-arxiv}[2026/02/17 Publications ArXiv Class]

%% ── Options ─────────────────────────────────────────────────────────────
\newif\ifpub@twocol \pub@twocolfalse
\DeclareOption{twocolumn}{\pub@twocoltrue}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{pub-base}}
\ProcessOptions\relax

\ifpub@twocol
  \PassOptionsToClass{twocolumn}{article}
\fi
\LoadClass[serif,letterpaper,10pt]{pub-base}

%% ── Force Computer Modern fonts ─────────────────────────────────────────
\AtEndPreamble{%
  \renewcommand{\rmdefault}{cmr}%
  \renewcommand{\sfdefault}{cmss}%
  \renewcommand{\ttdefault}{cmtt}%
}

%% ── ArXiv-safe packages only ────────────────────────────────────────────
\RequirePackage{amsmath}
\RequirePackage{amsfonts}
\RequirePackage{amssymb}
\RequirePackage{booktabs}
\RequirePackage{url}
\RequirePackage{nicefrac}

%% ── Page geometry: same as pub-paper (6.5"×9" text area) ────────────────
\AtBeginDocument{%
  \newgeometry{
    textheight=9in,
    textwidth=6.5in,
    top=1in,
    headheight=14pt,
    headsep=25pt,
    footskip=30pt
  }%
}

%% ── General layout ─────────────────────────────────────────────────────
\widowpenalty=10000
\clubpenalty=10000
\flushbottom
\sloppy

%% ── Headers and footers ────────────────────────────────────────────────
\fancyhf{}
\pagestyle{fancy}
\renewcommand{\headrulewidth}{0pt}
\fancyheadoffset{0pt}
\cfoot{\thepage}

%% ── ArXiv metadata macros ───────────────────────────────────────────────
\def\@arxivid{}
\def\@primarycategory{}
\def\@secondarycategories{}

\newcommand{\arxivid}[1]{\def\@arxivid{#1}}
\newcommand{\primarycategory}[1]{\def\@primarycategory{#1}}
\newcommand{\secondarycategories}[1]{\def\@secondarycategories{#1}}

%% ── Title bar + abstract (ArXiv conventions) ────────────────────────────
\newcommand{\@toptitlebar}{%
  \hrule height 2\p@
  \vskip 0.25in
  \vskip -\parskip%
}
\newcommand{\@bottomtitlebar}{%
  \vskip 0.29in
  \vskip -\parskip
  \hrule height 2\p@
  \vskip 0.09in%
}

\renewcommand{\maketitle}{%
  \par
  \begingroup
    \thispagestyle{empty}
    \vbox{%
      \hsize\textwidth
      \linewidth\hsize
      \vskip 0.1in
      \@toptitlebar
      \centering
      {\LARGE\scshape \@title\par}
      \@bottomtitlebar
      \vskip 0.1in
      {\large \@author\par}
      \ifx\@arxivid\empty\else
        \vskip 0.5em
        {\small arXiv:\@arxivid\space[\@primarycategory]\par}
      \fi
      \vskip 0.4in
    }
  \endgroup
}

\renewenvironment{abstract}{%
  \centerline{\large\bfseries\scshape Abstract}
  \begin{quote}
}{%
  \end{quote}
}

%% ── Semantic aliases ────────────────────────────────────────────────────
\providecommand{\affiliation}[1]{\textit{#1}}
\providecommand{\keywords}[1]{\par\noindent\textbf{Keywords:} #1}

\endinput
