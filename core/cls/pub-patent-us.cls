%% Copyright (c) 2026 Sebastien Rousseau
%% Licensed under the MIT License
%% See LICENSE file for details
%%
%% pub-patent-us.cls — Enhanced USPTO patent class (continuation/divisional/CIP)
%% First sibling-to-sibling inheritance: inherits from pub-patent.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{pub-patent-us}[2026/02/17 Publications USPTO Enhanced Patent Class]

%% ── Options ─────────────────────────────────────────────────────────────
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{pub-patent}}
\ProcessOptions\relax
\LoadClass[letterpaper]{pub-patent}

%% ── Application type flags ──────────────────────────────────────────────
\newif\ifPatentContinuation  \PatentContinuationfalse
\newif\ifPatentDivisional    \PatentDivisionalfalse
\newif\ifPatentCIP           \PatentCIPfalse

\newcommand{\setContinuation}{\PatentContinuationtrue}
\newcommand{\setDivisional}{\PatentDivisionaltrue}
\newcommand{\setCIP}{\PatentCIPtrue}

%% ── Parent application data ─────────────────────────────────────────────
\def\@parentapplication{}
\def\@parentfilingdate{}
\def\@provisionalapplication{}
\def\@provisionalfilingdate{}

\newcommand{\setParentApplication}[1]{\def\@parentapplication{#1}}
\newcommand{\setParentFilingDate}[1]{\def\@parentfilingdate{#1}}
\newcommand{\setProvisionalApplication}[1]{\def\@provisionalapplication{#1}}
\newcommand{\setProvisionalFilingDate}[1]{\def\@provisionalfilingdate{#1}}

%% ── Cross-reference boilerplate generators ──────────────────────────────

% \priorityClaim — generates CROSS-REFERENCE TO RELATED APPLICATIONS
\newcommand{\priorityClaim}{%
  \patentSection{Cross-Reference to Related Applications}%
  \patentParagraph{%
    This application is a
    \ifPatentContinuation continuation\fi
    \ifPatentDivisional divisional\fi
    \ifPatentCIP continuation-in-part\fi
    \space of U.S. Patent Application No.\ \@parentapplication,
    filed \@parentfilingdate,
    the entire disclosure of which is incorporated herein by reference.%
  }%
}

% \provisionalClaim — generates provisional application reference
\newcommand{\provisionalClaim}{%
  \patentParagraph{%
    This application claims the benefit of U.S. Provisional Patent
    Application No.\ \@provisionalapplication,
    filed \@provisionalfilingdate,
    the entire disclosure of which is incorporated herein by reference.%
  }%
}

%% ── Utility: application type string ────────────────────────────────────
\newcommand{\applicationTypeString}{%
  \ifPatentContinuation Continuation Application%
  \else\ifPatentDivisional Divisional Application%
  \else\ifPatentCIP Continuation-in-Part Application%
  \else Utility Patent Application%
  \fi\fi\fi
}

%% ── Description of Drawings environment ────────────────────────────────
\newenvironment{descriptionOfDrawings}{%
  \patentSection{Brief Description of the Drawings}%
}{%
  \par
}

\newcommand{\drawingDescription}[2]{%
  \patentParagraph{FIG.~\ref{#1} #2}%
}

%% ── Enhanced claims per 37 CFR § 1.52 ──────────────────────────────────
\newcounter{usclaim}
\setcounter{usclaim}{0}

\newenvironment{usclaims}{%
  \newpage
  \section*{CLAIMS}%
  \addcontentsline{toc}{section}{CLAIMS}%
  \setcounter{usclaim}{0}%
}{%
  \par
}

\newcommand{\independentClaim}[2][]{%
  \stepcounter{usclaim}%
  \par\vspace{0.5em}%
  \noindent\textbf{\arabic{usclaim}.}~%
  \ifx\\#1\\\else\label{cla:#1}\fi
  #2\par
}

\newcommand{\dependentClaim}[3][]{%
  \stepcounter{usclaim}%
  \par\vspace{0.5em}%
  \noindent\textbf{\arabic{usclaim}.}~%
  \ifx\\#1\\\else\label{cla:#1}\fi
  #2 of claim~\ref{cla:#3}, #2\par
}

%% ── Oath/Declaration boilerplate ───────────────────────────────────────
\newcommand{\inventorDeclaration}{%
  \patentSection{Declaration and Signature}%
  \patentParagraph{%
    I hereby declare that all statements made herein of my own knowledge
    are true and that all statements made on information and belief are
    believed to be true; and further that these statements were made with
    the knowledge that willful false statements and the like so made are
    punishable by fine or imprisonment, or both, under 18 U.S.C. 1001
    and that such willful false statements may jeopardize the validity
    of the application or any patent issued thereon.%
  }%
}

%% ── IDS reference ──────────────────────────────────────────────────────
\newcommand{\idsReference}[1]{%
  \patentParagraph{%
    Information Disclosure Statement reference: #1%
  }%
}

\endinput
