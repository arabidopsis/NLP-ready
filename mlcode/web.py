import webbrowser
import sys
doi = sys.argv[1]
webbrowser.open_new_tab('http://doi.org/' + doi)
