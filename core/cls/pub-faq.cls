%% Copyright (c) 2026 Sebastien Rousseau
%% Licensed under the MIT License
%% See LICENSE file for details
%%
%% pub-faq.cls — FAQ document class with Q&A environments
%% Extracted from faqs/faqs.cls (231 lines)
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{pub-faq}[2026/02/17 Publications FAQ Class]

%% ── Options ─────────────────────────────────────────────────────────────
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{pub-base}}
\ProcessOptions\relax
\PassOptionsToPackage{colorlinks}{hyperref}
\LoadClass[sans,letterpaper,11pt]{pub-base}

%% ── Geometry ────────────────────────────────────────────────────────────
\geometry{
  paper=letterpaper,
  top=1.25in,
  bottom=1.25in,
  left=1.25in,
  right=1.25in,
  includehead,
  includefoot
}

\setlength{\parskip}{1ex}
\setlength{\parindent}{0pt}

%% ── Section formatting ─────────────────────────────────────────────────
\titleformat{\section}
  {\huge\bfseries\color{black}}
  {\thesection}
  {1em}
  {}
  [\vspace{0.5ex}{\color{lightgray}\hrule height 0.5pt}\vspace{1.5ex}]

\titlespacing{\section}
  {0pt}
  {3.5ex plus 1ex minus .2ex}
  {2.3ex plus .2ex}

\titleformat{\subsection}
  {\Large\bfseries\color{black}}
  {\thesubsection}
  {1em}
  {}

%% ── Document variables ─────────────────────────────────────────────────
\def\@faqtitle{}
\newcommand{\faqtitle}[1]{\def\@faqtitle{#1}}

%% ── Semantic macros: FAQ-specific aliases live in pub-common.sty ───────

%% ── FAQ environment ────────────────────────────────────────────────────
\newenvironment{faq}[1]{%
  \vspace{2ex}%
  \noindent
  {\Large\bfseries\color{black}Q: #1\par}%
  \vspace{1.5ex}%
  \color{darkgray}%
}{%
  \par\vspace{2ex}%
  {\color{lightgray}\hrule height 0.25pt}%
  \vspace{2ex}%
}

%% ── Answer environment ─────────────────────────────────────────────────
\newenvironment{answer}{%
  \par\vspace{0.5ex}%
  \noindent
  {\bfseries\color{black}A: }\ignorespaces
}{%
  \par\vspace{0.5ex}
}

%% ── FAQ note box ────────────────────────────────────────────────────────
\newtcolorbox{faqnote}{
  pub-common,
  colback=lightgray,
  colframe=red
}

%% ── List settings ───────────────────────────────────────────────────────
%% leftmargin=* (enumitem's "compute from labelwidth + labelsep")
%% interacted with the sec-latex testphase + tagpdf list tagging in
%% TeX Live 2026 to raise "Missing number, treated as zero" on the
%% first \item — replaced with an explicit length so the lists tag
%% reliably under the new kernel sectioning interface.
\setlist{
  leftmargin=2em,
  itemsep=0.5ex,
  parsep=0.25ex,
  listparindent=0pt,
  itemindent=0pt
}
\setlist[itemize]{label=\textbullet}

%% ── Header / footer ────────────────────────────────────────────────────
\pagestyle{fancy}
\fancyhf{}
\setlength{\headheight}{14pt}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.25pt}

\fancyhead[L]{\color{darkgray}\small\rightmark}
\fancyfoot[L]{\color{darkgray}\small\@title}
\fancyfoot[R]{\color{darkgray}\small\thepage}

%% ── Hyperlink settings ─────────────────────────────────────────────────
\AtBeginDocument{%
  \hypersetup{
    linkcolor=black,
    urlcolor=black,
    linktoc=all,
  }%
}

%% ── Title page + TOC ───────────────────────────────────────────────────
\renewcommand{\maketitle}{%
  \thispagestyle{empty}
  \vspace*{-1cm}
  \begin{flushright}
    \IfFileExists{figures/logo.png}{%
      \includegraphics[width=2.5cm]{figures/logo}%
    }{}
  \end{flushright}
  \vspace*{2cm}
  \begin{center}
    {\huge\textcolor{black}{Frequently Asked Questions}\par}
    \vspace{1cm}
    {\Huge\bfseries\textcolor{black}{\@title}\par}
    \ifx\@subtitle\empty\else
      \vspace{0.5cm}
      {\Large\textcolor{darkgray}{\@subtitle}\par}
    \fi
  \end{center}
  \clearpage
  \thispagestyle{fancy}%
  \fancyhead[L]{\color{gray}CONTENTS}%
  \tableofcontents
  \clearpage
  \fancyhead[L]{\color{gray}\rightmark}
}

%% Force sections to start on new pages
\pretocmd{\section}{\clearpage}{}{}

%% ── Section name in header ─────────────────────────────────────────────
\renewcommand{\sectionmark}[1]{\markright{\MakeUppercase{#1}}}
\renewcommand{\subsectionmark}[1]{}

\endinput
