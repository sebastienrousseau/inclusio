%% Copyright (c) 2026 Sebastien Rousseau
%% Licensed under the MIT License
%% See LICENSE file for details
%%
%% pub-guide.cls — User guide / documentation class with tcolorbox environments
%% Extracted from guides/user-guide.cls (481 lines)
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{pub-guide}[2026/02/17 Publications Guide Class]

%% ── Options ─────────────────────────────────────────────────────────────
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{pub-base}}
\ProcessOptions\relax
\LoadClass[sans,letterpaper,11pt]{pub-base}

%% ── Additional packages ────────────────────────────────────────────────
\RequirePackage{datetime2}
\RequirePackage{listings}
\RequirePackage{textcomp}
\RequirePackage{caption}

%% ── Geometry ────────────────────────────────────────────────────────────
\geometry{
  paper=letterpaper,
  top=1.25in,
  bottom=1.25in,
  left=1.25in,
  right=1.25in,
  includehead,
  includefoot,
  heightrounded
}

\setlength{\parskip}{1ex}
\setlength{\parindent}{0pt}
\linespread{1.2}

%% ── Document variables ─────────────────────────────────────────────────
\def\@logopath{figures/logo}
\def\@logowidth{2.5cm}
\def\@logoheight{1.5cm}
\def\@doctype{User Guide}
\def\@companyname{}

\newcommand{\setCompanyName}[1]{\def\@companyname{#1}}
\newcommand{\setLogoPath}[1]{\def\@logopath{#1}}
\newcommand{\setLogoWidth}[1]{\def\@logowidth{#1}}
\newcommand{\setLogoHeight}[1]{\def\@logoheight{#1}}
\newcommand{\setDocType}[1]{\def\@doctype{#1}}
\newcommand{\setLanguage}[1]{\selectlanguage{#1}}

%% ── Section formatting ─────────────────────────────────────────────────
\titleformat{\section}
  {\huge\bfseries\sffamily\color{red}}
  {\thesection}
  {1em}
  {}

\titlespacing{\section}
  {0pt}
  {4ex plus 1ex minus .2ex}
  {2.5ex plus .2ex}

\titleformat{\subsection}
  {\Large\bfseries\sffamily\color{black}}
  {\thesubsection}
  {1em}
  {}
  [\vspace{0.5ex}]

\titlespacing{\subsection}
  {0pt}
  {3.25ex plus 1ex minus .2ex}
  {1.5ex plus .2ex}

\titleformat{\subsubsection}
  {\large\bfseries\sffamily\color{gray}}
  {\thesubsubsection}
  {1em}
  {}

\titlespacing{\subsubsection}
  {0pt}
  {3ex plus 1ex minus .2ex}
  {1.5ex plus .2ex}

%% ── Guide-specific semantic aliases live in pub-common.sty ─────────────

%% ── Code listing settings ──────────────────────────────────────────────
\lstset{
  basicstyle=\ttfamily\small,
  breaklines=true,
  breakatwhitespace=true,
  frame=single,
  numbers=left,
  numberstyle=\tiny\color{gray},
  backgroundcolor=\color{lightgray},
  keywordstyle=\color{blue},
  commentstyle=\color{gray},
  stringstyle=\color{red},
  showstringspaces=false,
  tabsize=4,
  captionpos=b,
  keepspaces=true,
  columns=flexible,
  inputencoding=utf8,
  extendedchars=true,
  upquote=true
}

\newcommand{\setCodeLanguage}[1]{\lstset{language=#1}}

%% ── List settings ───────────────────────────────────────────────────────
%% leftmargin=* (enumitem's "compute from labelwidth + labelsep")
%% conflicts with the sec-latex testphase + tagpdf list tagging in
%% TeX Live 2026 — replaced with an explicit length so the lists
%% tag reliably under the new kernel sectioning interface.
\setlist{
  leftmargin=2em,
  itemsep=0.5ex,
  parsep=0.25ex,
  listparindent=0pt,
  itemindent=0pt,
  topsep=0.5ex,
  partopsep=0.25ex
}
\setlist[itemize]{label=\textbullet}

%% ── Header / footer ────────────────────────────────────────────────────
\pagestyle{fancy}
\fancyhf{}
\setlength{\headheight}{28pt}
\renewcommand{\headrulewidth}{0.25pt}
\renewcommand{\footrulewidth}{0.25pt}

\fancyhead[L]{\color{textgray}\small\rightmark}
\fancyfoot[L]{\color{textgray}\small\textit{\@title}}
\fancyfoot[R]{\color{textgray}\small\thepage}

%% ── Title page + TOC ───────────────────────────────────────────────────
\renewcommand{\maketitle}{%
  \thispagestyle{empty}
  \vspace*{-1cm}
  \begin{flushright}
    \IfFileExists{\@logopath}{%
      \includegraphics[width=\@logowidth,height=\@logoheight,keepaspectratio]{\@logopath}%
    }{}
  \end{flushright}
  \vspace*{2cm}
  \begin{center}
    {\huge\textcolor{black}{\@doctype}\par}
    \vspace{1cm}
    {\Huge\bfseries\textcolor{red}{\@title}\par}
    \ifx\@subtitle\empty\else
      \vspace{0.5cm}
      {\Large\textcolor{gray}{\@subtitle}\par}
    \fi
    \vspace{1cm}
    {\large\textcolor{gray}{\@companyname}\par}
    \vfill
    {\large\textcolor{gray}{Version \@documentversion}\par}
  \end{center}
  \clearpage
  \thispagestyle{fancy}
  \fancyhead[L]{\color{textgray}CONTENTS}
  \tableofcontents
  \clearpage
  \fancyhead[L]{\color{textgray}\rightmark}
}

%% Force sections to start on new pages
\pretocmd{\section}{\clearpage}{}{}

%% ── Section names in header ────────────────────────────────────────────
\renewcommand{\sectionmark}[1]{\markright{\MakeUppercase{#1}}}
\renewcommand{\subsectionmark}[1]{}

\endinput
