%% Copyright (c) 2026 Sebastien Rousseau
%% Licensed under the MIT License
%% See LICENSE file for details
%%
%% pub-bio.cls — Academic biography / speaker profile class
%% Photo + name layout, contact block with icons, publications list.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{pub-bio}[2026/02/17 Publications Biography Class]

%% ── Options ─────────────────────────────────────────────────────────────
\newif\ifbio@doublespace \bio@doublespacefalse
\newif\ifbio@linenumbers \bio@linenumbersfalse
\DeclareOption{doublespace}{\bio@doublespacetrue}
\DeclareOption{linenumbers}{\bio@linenumberstrue}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{pub-base}}
\ProcessOptions\relax
\LoadClass[sans,a4paper,11pt]{pub-base}

%% ── Additional packages ────────────────────────────────────────────────
\RequirePackage{wrapfig}
\RequirePackage{fontawesome5}
\RequirePackage{setspace}
\ifbio@linenumbers
  \RequirePackage{lineno}
\fi

%% ── Conditional spacing / line numbers ──────────────────────────────────
\ifbio@doublespace
  \AtBeginDocument{\doublespacing}
\fi
\ifbio@linenumbers
  \AtBeginDocument{\linenumbers}
\fi

%% ── Geometry ────────────────────────────────────────────────────────────
\geometry{
  paper=a4paper,
  top=2cm,
  bottom=2cm,
  left=2.5cm,
  right=2.5cm,
  headheight=14pt,
  headsep=12pt
}

\linespread{1.15}

%% ── titlesec defaults ──────────────────────────────────────────────────
%% pub-base loads titlesec but provides no defaults. Calling the
%% unstarred \section{...} from user TeX (or from the per-class
%% tagged-PDF smoke tests) raises "Package titlesec Error: No format
%% for this command." pub-bio doesn't ship its own sectioning macros,
%% so provide sensible defaults for downstream authors.
\titleformat{\section}{\Large\bfseries}{\thesection}{1em}{}
\titleformat{\subsection}{\large\bfseries}{\thesubsection}{1em}{}
\titleformat{\subsubsection}{\normalsize\bfseries\itshape}{\thesubsubsection}{1em}{}

%% ── Headers / footers ──────────────────────────────────────────────────
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.4pt}
\fancyfoot[L]{\small\itshape\@author}
\fancyfoot[R]{\small\thepage}

%% ── Bio header: \bioheader[photo]{Name}{Title}{Affiliation} ─────────────
\newcommand{\bioheader}[4][]{%
  \begin{minipage}[t]{0.99\textwidth}
    \ifx\\#1\\%
      % No photo
      {\fontsize{24}{30}\selectfont\bfseries #2\par}
      \vspace{0.3em}
      {\large\color{subColor} #3\par}
      \vspace{0.2em}
      {\normalsize\color{subColor}\itshape #4\par}
    \else
      % With photo
      \begin{minipage}[t]{0.22\textwidth}
        \includegraphics[width=\linewidth]{#1}
      \end{minipage}\hfill
      \begin{minipage}[t]{0.74\textwidth}
        {\fontsize{24}{30}\selectfont\bfseries #2\par}
        \vspace{0.3em}
        {\large\color{subColor} #3\par}
        \vspace{0.2em}
        {\normalsize\color{subColor}\itshape #4\par}
      \end{minipage}
    \fi
  \end{minipage}
  \vspace{1em}
  \par\noindent\rule{\textwidth}{0.4pt}
  \vspace{0.5em}
}

%% ── Contact block: \biocontact{email}{url}{orcid} ──────────────────────
\newcommand{\biocontact}[3]{%
  \par\noindent
  \begin{tabular}{@{}ll@{}}
    \faEnvelope & \href{mailto:#1}{#1} \\
    \faGlobe    & \url{#2} \\
    \ifx\\#3\\%
    \else
      \faOrcid  & \href{https://orcid.org/#3}{#3} \\
    \fi
  \end{tabular}
  \vspace{1em}\par
}

%% ── Publications list ───────────────────────────────────────────────────
\newenvironment{publications}{%
  \begin{enumerate}[label={[\arabic*]}, leftmargin=*, itemsep=0.5em]
}{%
  \end{enumerate}
}

% \pub{authors}{title}{venue}{year}
\newcommand{\pub}[4]{%
  \item #1. \textit{#2}. #3, #4.
}

%% ── Research interests ──────────────────────────────────────────────────
\newcommand{\researchinterests}[1]{%
  \par\noindent\textbf{Research Interests:} #1\par
  \vspace{0.5em}
}

%% ── Short bio environment ───────────────────────────────────────────────
\newenvironment{shortbio}{%
  \par\vspace{0.5em}
  \noindent\itshape
}{%
  \par\vspace{0.5em}
}

%% ── Subject area tags (BioArXiv preprint) ───────────────────────────────
\newcommand{\subjectarea}[1]{%
  \tcbox[on line, colback=mainColor!10, colframe=mainColor,
    size=small, arc=2pt, boxrule=0.5pt]{%
    \small\sffamily #1%
  }%
}

\newcommand{\subjectareas}[1]{%
  \par\noindent\textbf{Subject Areas:}\quad #1\par
  \vspace{0.5em}
}

%% ── Preprint URL ───────────────────────────────────────────────────────
\newcommand{\preprinturl}[1]{%
  \par\noindent\textbf{Preprint:}\quad\url{#1}\par
  \vspace{0.5em}
}

%% ── Competing interests ────────────────────────────────────────────────
\newenvironment{competinginterests}{%
  \par\vspace{1em}
  \noindent\textbf{Competing Interests}\par\smallskip
  \noindent
}{%
  \par\vspace{0.5em}
}

\endinput
