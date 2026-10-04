Output .github/demo.gif

Set FontSize 14
Set Width 1200
Set Height 600
Set Padding 20
Set Theme "Catppuccin Mocha"

Type "python3 -m inclusio.mcp.server --help"
Sleep 500ms
Enter
Sleep 2s

Type "python3 -c 'from inclusio.mcp.server import _list_docs_impl; print(_list_docs_impl()[0])'"
Sleep 500ms
Enter
Sleep 3s
