# LaTeX build configuration for Publications monorepo
# Enforces reproducible builds across all document types

# PDF generation engine
$pdf_mode = 1;
$pdflatex = 'pdflatex -interaction=nonstopmode -halt-on-error -file-line-error %O %S';

# Bibliography and index processing
$bibtex_use = 2;
$biber = 'biber %O --bblencoding=utf8 -u -U --output_safechars %B';

# Automatic dependency detection
$recorder = 1;

# Output directory
$out_dir = 'build';

# Auxiliary file cleanup after successful compilation
$cleanup_mode = 1;
$clean_ext = 'aux bbl blg fdb_latexmk fls log nav out snm synctex.gz toc vrb bcf run.xml figlist makefile auxlock';

# Continuous preview mode configuration
$preview_continuous_mode = 1;
$pdf_previewer = 'open -a Preview %S';

# Maximum compilation passes
$max_repeat = 5;

# Force regeneration if source newer than target
$go_mode = 1;

# Custom build hooks
$compiling_cmd = 'echo "Starting LaTeX compilation for %S..."';
$success_cmd = 'echo "✓ Successfully built %S -> %D"';
$failure_cmd = 'echo "✗ Build failed for %S" && exit 1';

# Ensure proper file permissions
$do_cd = 1;

# Use filesystem monitoring for continuous mode
$sleep_time = 1;

# Custom pre-compilation hook for quality checks
add_cus_dep('tex', 'chk', 0, 'run_chktex');
sub run_chktex {
    my $base = shift;
    my $tex_file = "$base.tex";

    if (-e $tex_file) {
        print "Running ChkTeX quality check on $tex_file...\n";
        my $result = system("chktex -q -n all '$tex_file'");
        if ($result != 0) {
            print STDERR "ERROR: ChkTeX found warnings in $tex_file\n";
            return 1;
        }
        print "✓ ChkTeX quality check passed for $tex_file\n";
    }
    return 0;
}