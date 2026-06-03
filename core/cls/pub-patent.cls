%% Copyright (c) 2026 Sebastien Rousseau
%% Licensed under the MIT License
%% See LICENSE file for details
%%
%% pub-patent.cls — USPTO-compliant patent application class
%% Extracted from patents/patent.cls (168 lines)
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{pub-patent}[2026/02/17 Publications Patent Class]

%% ── Options ─────────────────────────────────────────────────────────────
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{pub-base}}
\ProcessOptions\relax
\LoadClass[serif,letterpaper,12pt]{pub-base}

%% ── Additional packages ────────────────────────────────────────────────
\RequirePackage{booktabs}
\RequirePackage{textcase}
\RequirePackage{setspace}
\RequirePackage{lineno}

%% ── Geometry: USPTO standard (1" margins) ───────────────────────────────
\geometry{
  paper=letterpaper,
  top=1in,
  bottom=1in,
  left=1in,
  right=1in,
  headheight=24pt,
  headsep=0.5in,
  footskip=0.5in
}

%% ── Spacing: USPTO 1.5-line spacing ────────────────────────────────────
\setlength{\parindent}{0.5in}
\setlength{\parskip}{12pt}
\renewcommand{\normalsize}{\fontsize{12}{18}\selectfont}
\AtBeginDocument{\onehalfspacing}
\raggedbottom

%% ── titlesec defaults ──────────────────────────────────────────────────
%% pub-base loads titlesec but provides no defaults; without these,
%% calling the unstarred \section{...} from user TeX (or from the
%% per-class tagged-PDF smoke tests) raises "Package titlesec Error:
%% No format for this command." The patent class itself routes through
%% \patentSection/\patentSubSection (starred), which dodges the
%% requirement, but plain \section must work for downstream authors.
\titleformat{\section}{\large\bfseries\MakeUppercase}{\thesection}{1em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection}{1em}{}
\titleformat{\subsubsection}{\normalsize\bfseries\itshape}{\thesubsubsection}{1em}{}

%% ── Patent mode flags ──────────────────────────────────────────────────
\newif\ifPatentOfficeMode
\PatentOfficeModetrue

\newcommand{\setPrintingModeApplication}{\PatentOfficeModetrue}
\newcommand{\setPrintingModeDraft}{\PatentOfficeModefalse}

%% ── Document variables ─────────────────────────────────────────────────
\def\@docketnumber{}
\def\@otherinventor{}

\newcommand{\setDocketNumber}[1]{\def\@docketnumber{#1}}
\newcommand{\setOtherInventor}[1]{\def\@otherinventor{#1}}

%% ── Title page ──────────────────────────────────────────────────────────
\newcommand{\makesubtitle}{%
  \ifx\@subtitle\empty\else
    {\large\@subtitle\par}
  \fi
}

\renewcommand{\maketitle}{%
  \hypersetup{pageanchor=false}%
  \begin{titlepage}
  \begin{center}
    \vspace*{1in}
    {\Large\bfseries\MakeUppercase{\@title}\par}
    \vspace{2em}
    \makesubtitle
    \vspace{2em}
    {\large\bfseries By\par}
    \vspace{1em}
    {\large\bfseries\@author\par}
    \ifx\@otherinventor\empty\else
      \vspace{1em}
      {\large\bfseries\@otherinventor\par}
    \fi
    \vspace{1em}
    \@date
  \end{center}
  \end{titlepage}
  \hypersetup{pageanchor=true}%
}

%% ── Paragraph numbering [NNNN] ─────────────────────────────────────────
\newcounter{parnum}
\setcounter{parnum}{1}

\newcommand{\paddedParnum}{%
  \ifnum\value{parnum}<1000 0\fi
  \ifnum\value{parnum}<100 0\fi
  \ifnum\value{parnum}<10 0\fi
  \arabic{parnum}%
}

\newcommand{\patentParagraph}[1]{%
  \par\vspace{1em}%
  \noindent[\textbf{\paddedParnum}]~\stepcounter{parnum}#1\par
}

%% ── Semantic section commands ───────────────────────────────────────────
\newcommand{\patentSection}[1]{%
  \section*{\MakeUppercase{#1}}%
  \phantomsection
  \addcontentsline{toc}{section}{#1}%
  \vspace{0.5em}
}

\newcommand{\patentSubSection}[1]{%
  \subsection*{\MakeUppercase{#1}}%
  \phantomsection
  \addcontentsline{toc}{subsection}{#1}%
  \vspace{0.5em}
}

\newcommand{\patentSubSubSection}[1]{%
  \subsubsection*{#1}%
  \phantomsection
  \addcontentsline{toc}{subsubsection}{#1}%
  \vspace{0.5em}
}

%% ── Claims environment ─────────────────────────────────────────────────
\newcommand{\patentClaimsStart}{%
  \newpage
  \section*{CLAIMS}
  \addcontentsline{toc}{section}{CLAIMS}%
  \begin{enumerate}
}

\newcommand{\patentClaimsEnd}{%
  \end{enumerate}
}

\newcommand{\beginClaim}[2]{\item \label{cla:#1} #2}
\newcommand{\claimRef}[1]{claim \ref{cla:#1}}

%% ── Headers / footers ──────────────────────────────────────────────────
\fancyhf{}
\fancyhead[R]{\@docketnumber}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0pt}
\setlength{\headheight}{24pt}
\pagestyle{fancy}

%% ── Figure reference macro ─────────────────────────────────────────────
\newcommand{\figureReference}[1]{FIG.~\ref{#1}}

\endinput
