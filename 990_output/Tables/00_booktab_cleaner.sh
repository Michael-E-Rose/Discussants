#!/usr/bin/env bash
# Enhance LaTeX tables: booktabs and subscript 2

# toprule
sed -i ':a;N;$!ba;s/\\\\\[-1\.8ex]\\hline \n\\hline \\\\\[-1\.8ex] /\\toprule/g' *.tex

# bottomrule
sed -i ':a;N;$!ba;s/\\hline \n\\hline \\\\\[-1\.8ex] /\\bottomrule/g' *.tex

# midrule
sed -i 's/\\hline \\\\\[-1\.8ex] /\\midrule/g' *.tex

# subscript 2
sed -i 's/\$2\$/\$^2\$/g' *.tex

# felm
sed -i 's/felm/OLS/g' *.tex

# AIC
sed -i 's/Akaike Inf. Crit./AIC/g' *.tex
