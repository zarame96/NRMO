# Makefile for NRMO Complete System v5.5

LATEX = pdflatex -shell-escape -interaction=nonstopmode
DOC = NRMO_Complete_v5_5
BIB = bibtex

.PHONY: all clean quick

all: $(DOC).pdf

$(DOC).pdf: $(DOC).tex frontmatter/*.tex chapters/*.tex parts/*.tex appendices/*.tex references.bib
	$(LATEX) $(DOC).tex
	-$(BIB) $(DOC)
	-makeindex $(DOC).idx
	$(LATEX) $(DOC).tex
	$(LATEX) $(DOC).tex

# Quick build without bib/index regen
quick:
	$(LATEX) $(DOC).tex

clean:
	rm -f *.aux *.log *.toc *.lof *.lot *.idx *.ilg *.ind *.bbl *.blg *.out *.synctex.gz
	rm -f frontmatter/*.aux chapters/*.aux parts/*.aux appendices/*.aux

distclean: clean
	rm -f $(DOC).pdf
