%% Copyright (c) 2026 Sebastien Rousseau
%% Licensed under the MIT License
%% See LICENSE file for details
%%
%% pub-paper.cls — arXiv-compatible research paper class
%% Extracted from papers/arxiv_style.sty (330 lines)
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{pub-paper}[2026/02/17 Publications Paper Class]

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
%% Bibliography: NOT loaded here — documents choose natbib OR biblatex.
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

%% ── Headers and footers ────────────────────────────────────────────────
\fancyhf{}
\pagestyle{fancy}
\renewcommand{\headrulewidth}{0pt}
\fancyheadoffset{0pt}
\cfoot{\thepage}

\fancypagestyle{firstpage}{%
  \fancyhf{}%
  \renewcommand{\footrulewidth}{0pt}%
}

%% ── Font sizes (arxiv-compatible) ───────────────────────────────────────
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

\providecommand{\paragraph}{}
\renewcommand{\paragraph}{%
  \@startsection{paragraph}{4}{\z@}%
    {1.5ex \@plus0.5ex \@minus0.2ex}%
    {-1em}%
    {\normalsize\bfseries}%
}

%% ── Float placement ────────────────────────────────────────────────────
\renewcommand{\topfraction}{0.85}
\renewcommand{\bottomfraction}{0.4}
\renewcommand{\textfraction}{0.1}
\renewcommand{\floatpagefraction}{0.7}

%% ── Captions ────────────────────────────────────────────────────────────
\newlength{\@abovecaptionskip}\setlength{\@abovecaptionskip}{7\p@}
\newlength{\@belowcaptionskip}\setlength{\@belowcaptionskip}{\z@}
\setlength{\abovecaptionskip}{\@abovecaptionskip}
\setlength{\belowcaptionskip}{\@belowcaptionskip}

\renewenvironment{table}
  {\setlength{\abovecaptionskip}{\@belowcaptionskip}%
   \setlength{\belowcaptionskip}{\@abovecaptionskip}%
   \@float{table}}
  {\end@float}

%% ── Footnotes ───────────────────────────────────────────────────────────
\setlength{\footnotesep}{6.65\p@}
\setlength{\skip\footins}{9\p@ \@plus4\p@ \@minus2\p@}
\renewcommand{\footnoterule}{\kern-3\p@ \hrule width 12pc \kern 2.6\p@}
\setcounter{footnote}{0}

%% ── Paragraph ───────────────────────────────────────────────────────────
\setlength{\parindent}{0pt}
\setlength{\parskip}{5.5\p@}

%% ── List formatting ─────────────────────────────────────────────────────
\setlength{\topsep}{4\p@ \@plus1\p@ \@minus2\p@}
\setlength{\partopsep}{1\p@ \@plus0.5\p@ \@minus0.5\p@}
\setlength{\itemsep}{2\p@ \@plus1\p@ \@minus0.5\p@}
\setlength{\parsep}{2\p@ \@plus1\p@ \@minus0.5\p@}
\setlength{\leftmargin}{3pc}
\setlength{\leftmargini}{\leftmargin}
\setlength{\leftmarginii}{2em}
\setlength{\leftmarginiii}{1.5em}
\setlength{\leftmarginiv}{1.0em}
\setlength{\leftmarginv}{0.5em}

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

\providecommand{\@maketitle}{}
\renewcommand{\@maketitle}{%
  \vbox{%
    \hsize\textwidth
    \linewidth\hsize
    \vskip 0.1in
    \@toptitlebar
    \centering
    {\LARGE\scshape \@title\par}
    \@bottomtitlebar
    \vskip 0.1in
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

%% ── Semantic aliases for paper macros ───────────────────────────────────
\newcommand{\affiliation}[1]{\textit{#1}}
\newcommand{\keywords}[1]{\par\noindent\textbf{Keywords:} #1}

\makeatother
\endinput
