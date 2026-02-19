%% Copyright (c) 2026 Sebastien Rousseau
%% Licensed under the MIT License
%% See LICENSE file for details
%%
%% pub-cv.cls — ATS-optimized CV class with golden ratio layout
%% Extracted from cvs/cv.cls (184 lines)
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{pub-cv}[2026/02/17 Publications CV Class]

%% ── Load base ───────────────────────────────────────────────────────────
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{pub-base}}
\ProcessOptions\relax
\PassOptionsToPackage{colorlinks}{hyperref}
\LoadClass[sans,a4paper,11pt]{pub-base}

%% ── Additional packages ────────────────────────────────────────────────
\RequirePackage{fontawesome5}
\RequirePackage{ragged2e}
\RequirePackage[export]{adjustbox}

%% ── Geometry: golden ratio proportions ──────────────────────────────────
\geometry{
  paper=a4paper,
  left=2.25cm,
  right=2.25cm,
  top=1.5cm,
  bottom=1.5cm,
  headheight=13pt,
  headsep=8pt,
  includefoot
}
\linespread{1.05}

%% ── Page style ──────────────────────────────────────────────────────────
\AtBeginDocument{%
  \pagestyle{fancy}%
  \thispagestyle{plain}%
  \renewcommand{\headrulewidth}{0pt}%
  \renewcommand{\footrulewidth}{0pt}%
}

%% ── Footer with address ────────────────────────────────────────────────
\newcommand{\footeraddress}[1]{%
  \newcommand{\footerfontsize}{8.4pt}%
  \newcommand{\footerbaseheight}{13.596pt}%
  \fancyhf{}%
  \fancyfoot[L]{%
    {\fontsize{\footerfontsize}{\footerbaseheight}\selectfont \color{subColor} #1}%
  }%
  \fancyfoot[R]{%
    {\fontsize{\footerfontsize}{\footerbaseheight}\selectfont \color{subColor} \thepage}%
  }%
  \fancypagestyle{plain}{%
    \fancyhf{}%
    \fancyfoot[L]{%
      {\fontsize{\footerfontsize}{\footerbaseheight}\selectfont \color{subColor} #1}%
    }%
    \fancyfoot[R]{%
      {\fontsize{\footerfontsize}{\footerbaseheight}\selectfont \color{subColor} \thepage}%
    }%
  }%
}

%% ── List settings ───────────────────────────────────────────────────────
\setlist{topsep=4pt plus 2pt,
         parsep=0pt,
         itemsep=4pt plus 2pt,
         partopsep=0pt}

%% ── Semantic macros: CV sections ────────────────────────────────────────

% Section title formatting
\titleformat{\section}
  {\Large\bfseries\color{headingColor}}
  {}
  {0pt}
  {}
  [\vspace{\goldenratioxs em}\titlerule]

\titlespacing*{\section}
  {0pt}
  {1.2\baselineskip plus 2pt minus 2pt}
  {0.8\baselineskip plus 2pt minus 2pt}

% CV section entry: \cvsection[logo]{title}{date}
\newcommand{\cvsection}[3][]{%
  \vspace{0.618\baselineskip}
  {\fontsize{12}{19.416}\selectfont
   \raggedright
   \ifx\\#1\\
     {\color{black}\textbf{#2}\hfill\color{subColor}#3\par}
   \else
     \IfFileExists{#1}{%
       \includegraphics[height=\goldenratio em,valign=c]{#1}~{\color{subColor}#2}\par
     }{%
       {\color{black}\textbf{#2}\hfill\color{subColor}#3\par}%
     }%
   \fi
  }
}

% Name block
\newcommand{\name}[2]{%
  \vspace*{-2em}%
  {\fontsize{22}{35.596}\selectfont\bfseries\raggedright #1 #2\par}
  \vspace{\goldenratiosm em}
}

% Role / job title
\newcommand{\role}[1]{%
  {\fontsize{13.6}{22}\selectfont\color{subColor}\raggedright #1\par}
  \vspace{0.2em}
}

% Contact info
\newcommand{\contact}[4]{%
  {\fontsize{11pt}{17.798}\selectfont\color{subColor}
  \begin{flushright}
    \faPhone\ #1\par
    \faEnvelope\ #2\par
  \end{flushright}
  \vspace{\goldenratiosm em}}
}

% Education entry: \cveducation[logo]{year/title}{institution}{location}{date}
\newcommand{\cveducation}[5][]{%
  {\fontsize{11pt}{17.798}\selectfont\raggedright
  \ifx\\#1\\
    \textbf{#2} #3\hfill\textcolor{darkgray}{#4 #5}%
  \else
    \IfFileExists{#1}{%
      \includegraphics[height=\goldenratio em,valign=c]{#1}~\textbf{#2} #3\hfill\textcolor{darkgray}{#4 #5}%
    }{%
      \textbf{#2} #3\hfill\textcolor{darkgray}{#4 #5}%
    }%
  \fi\par}
  \vspace{\goldenratiosm em}
}

% Wider quad
\renewcommand{\quad}{\hspace{1.8em}}

%% ── Hyperlink styling ───────────────────────────────────────────────────
\AtBeginDocument{%
  \hypersetup{
    urlcolor=linkColor,
    linkcolor=linkColor
  }%
}

\endinput
