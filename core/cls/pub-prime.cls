%% Copyright (c) 2026 Sebastien Rousseau
%% Licensed under the MIT License
%% See LICENSE file for details
%%
%% pub-prime.cls — AI conference paper class ("Modernized NIPS")
%% Inherits from pub-base like pub-paper.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{pub-prime}[2026/02/17 Publications AI Conference Paper Class]

%% ── Options ─────────────────────────────────────────────────────────────
\newif\ifpub@twocol \pub@twocolfalse
\DeclareOption{twocolumn}{\pub@twocoltrue}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{pub-base}}
\ProcessOptions\relax

\ifpub@twocol
  \PassOptionsToClass{twocolumn}{article}
\fi
\LoadClass[serif,letterpaper,10pt]{pub-base}

%% ── Additional packages ────────────────────────────────────────────────
\RequirePackage{url}
\RequirePackage{booktabs}
\RequirePackage{amsfonts}
\RequirePackage{nicefrac}
\RequirePackage{textcomp}
\RequirePackage{setspace}

\makeatletter

%% ── Page geometry ───────────────────────────────────────────────────────
\AtBeginDocument{%
  \newgeometry{
    textheight=9in,
    textwidth=6.5in,
    top=1in,
    headheight=14pt,
    headsep=25pt,
    footskip=30pt,
    marginparsep=10pt,
    marginparwidth=50pt
  }%
}

%% ── General layout ─────────────────────────────────────────────────────
\widowpenalty=10000
\clubpenalty=10000
\flushbottom
\sloppy

%% ── Conference metadata macros ──────────────────────────────────────────
\def\@conferencename{Conference}
\def\@conferenceyear{2026}
\def\@shorttitle{}
\def\@citeas{}

\newcommand{\conferencename}[1]{\def\@conferencename{#1}}
\newcommand{\conferenceyear}[1]{\def\@conferenceyear{#1}}
\newcommand{\shorttitle}[1]{\def\@shorttitle{#1}}
\newcommand{\citeas}[1]{\def\@citeas{#1}}

%% ── Running headers ────────────────────────────────────────────────────
\fancyhf{}
\pagestyle{fancy}
\renewcommand{\headrulewidth}{0.4pt}
\fancyhead[L]{\small\itshape\@conferencename~\@conferenceyear}
\fancyhead[R]{\small\itshape\@shorttitle}
\fancyheadoffset{0pt}
\cfoot{\thepage}

\fancypagestyle{firstpage}{%
  \fancyhf{}%
  \renewcommand{\headrulewidth}{0pt}%
  \renewcommand{\footrulewidth}{0pt}%
}

%% ── Font sizes (arxiv-compatible) ─────────────────────────────────────
\def\@xpt{10pt}
\def\@xipt{11pt}
\def\@ixpt{9pt}
\def\@viipt{7pt}
\def\@viiipt{8pt}
\def\@vipt{5pt}
\def\@xxpt{20pt}
\def\@xivpt{14pt}
\def\@xviipt{17pt}
\def\@xxvpt{25pt}

\renewcommand{\normalsize}{%
  \@setfontsize\normalsize\@xpt\@xipt
  \abovedisplayskip      7\p@ \@plus2\p@ \@minus5\p@
  \abovedisplayshortskip \z@ \@plus3\p@
  \belowdisplayskip      \abovedisplayskip
  \belowdisplayshortskip 4\p@ \@plus3\p@ \@minus3\p@
}
\normalsize

\renewcommand{\small}{%
  \@setfontsize\small\@ixpt\@xpt
  \abovedisplayskip      6\p@ \@plus1.5\p@ \@minus4\p@
  \abovedisplayshortskip \z@ \@plus2\p@
  \belowdisplayskip      \abovedisplayskip
  \belowdisplayshortskip 3\p@ \@plus2\p@ \@minus2\p@
}

\renewcommand{\footnotesize}{\@setfontsize\footnotesize\@ixpt\@xpt}
\renewcommand{\scriptsize}{\@setfontsize\scriptsize\@viipt\@viiipt}
\renewcommand{\tiny}{\@setfontsize\tiny\@vipt\@viipt}
\renewcommand{\large}{\@setfontsize\large\@xiipt{14}}
\renewcommand{\Large}{\@setfontsize\Large\@xivpt{16}}
\renewcommand{\LARGE}{\@setfontsize\LARGE\@xviipt{20}}
\renewcommand{\huge}{\@setfontsize\huge\@xxpt{23}}
\renewcommand{\Huge}{\@setfontsize\Huge\@xxvpt{28}}

%% ── Section headings ───────────────────────────────────────────────────
\providecommand{\section}{}
\renewcommand{\section}{%
  \@startsection{section}{1}{\z@}%
    {-2.0ex \@plus -0.5ex \@minus -0.2ex}%
    {1.5ex \@plus 0.3ex \@minus 0.2ex}%
    {\large\bfseries\raggedright}%
}

\providecommand{\subsection}{}
\renewcommand{\subsection}{%
  \@startsection{subsection}{2}{\z@}%
    {-1.8ex \@plus -0.5ex \@minus -0.2ex}%
    {0.8ex \@plus 0.2ex}%
    {\normalsize\bfseries\raggedright}%
}

\providecommand{\subsubsection}{}
\renewcommand{\subsubsection}{%
  \@startsection{subsubsection}{3}{\z@}%
    {-1.5ex \@plus -0.5ex \@minus -0.2ex}%
    {0.5ex \@plus 0.2ex}%
    {\normalsize\bfseries\raggedright}%
}

%% ── Title ───────────────────────────────────────────────────────────────
\providecommand{\maketitle}{}
\renewcommand{\maketitle}{%
  \par
  \begingroup
    \renewcommand{\thefootnote}{\fnsymbol{footnote}}
    \renewcommand{\@makefnmark}{\hbox to \z@{$^{\@thefnmark}$\hss}}
    \long\def\@makefntext##1{%
      \parindent 1em\noindent
      \hbox to 1.8em{\hss $^{\@thefnmark}$}##1
    }
    \thispagestyle{firstpage}
    \@maketitle
    \@thanks
  \endgroup
  \let\maketitle\relax
  \let\thanks\relax
}

\providecommand{\@maketitle}{}
\renewcommand{\@maketitle}{%
  \vbox{%
    \hsize\textwidth
    \linewidth\hsize
    \vskip 0.1in
    \centering
    {\LARGE\scshape \@title\par}
    \vskip 0.2in
    \def\And{%
      \end{tabular}\hfil\linebreak[0]\hfil%
      \begin{tabular}[t]{c}\bfseries\rule{\z@}{24\p@}\ignorespaces%
    }
    \def\AND{%
      \end{tabular}\hfil\linebreak[4]\hfil%
      \begin{tabular}[t]{c}\bfseries\rule{\z@}{24\p@}\ignorespaces%
    }
    \begin{tabular}[t]{c}\bfseries\rule{\z@}{24\p@}\@author\end{tabular}%
    \vskip 0.4in
  }
}

%% ── Abstract ────────────────────────────────────────────────────────────
\renewenvironment{abstract}
{%
  \centerline{\large \bfseries \scshape Abstract}
  \begin{quote}
}
{%
  \end{quote}
}

%% ── Citation rule ──────────────────────────────────────────────────────
\newcommand{\makeciteas}{%
  \ifx\@citeas\empty\else
    \par\vspace{0.5em}
    \noindent\fbox{%
      \parbox{0.95\linewidth}{%
        \small\textbf{Cite as:} \@citeas
      }%
    }
    \par\vspace{0.5em}
  \fi
}

%% ── Semantic aliases ───────────────────────────────────────────────────
\newcommand{\affiliation}[1]{\textit{#1}}
\newcommand{\keywords}[1]{\par\noindent\textbf{Keywords:} #1}

\makeatother
\endinput
