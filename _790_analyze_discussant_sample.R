#!/usr/bin/Rscript
setwd("/home/panther/Science/Projects/discussants")

#
# Variables
#
masterfile = "./780_discussant_sample/master.csv"
out_folder = "./990_output/"

style = "qje"  # For tables
font = "Utopia"  # For graphs
omit_stats = c("chi2", 'll', 'theta', 'ser', 'f', "adj.rsq")  # Drop summary stats

var = list()
var$auth = c("euclid.max_auth", "experience.max_auth", "sq_exp")
attr(var$auth, "names") = c("Author max. Euclid",
                            "Author max. experience",
                            "Author max. experience$2$")
var$paper = c("num_auth")
attr(var$paper, "names") = c("\\# of authors")
var$has = c("has_discussion")
attr(var$has, "names") = "Has discussion"
var$reg_ols = c("euclid_dis", "coauth_neighborhood_55", "informal_neighborhood_55")
attr(var$reg_ols, "names") = c("Discussant Euclid",
                               "Discussant coauthor neighborhood",
                               "Discussant informal neighborhood")
var$reg_negbin = c("experience_dis")
attr(var$reg_negbin, "names") = c("Discussant experience")
var$reg_logit = c("top_dis")
attr(var$reg_logit, "names") = c("Discussant top affiliation")
var$other = c("year")

#
# Load packages
#
suppressPackageStartupMessages({
  require(Hmisc)
  require(stargazer)
  require(mfx)
  require(plyr)
  require(rms)
  require(stringi)
  require(extrafont)
  require(ggplot2)
})

#
# Functions
#
get_summary = function(x){
  do.call(data.frame,
          list(N=apply(x, 2, function(x) length(which(!is.na(x)))),
               Mean=round(apply(x, 2, mean, na.rm=T), 2),
               Median=round(apply(x, 2, median, na.rm=T), 2),
               "Std Dev."=round(apply(x, 2, sd, na.rm=T), 2),
               Min=round(apply(x, 2, min, na.rm=T), 2),
               Max=round(apply(x, 2, max, na.rm=T), 2)))
}

#
#  Read in
#
Master = read.csv(masterfile, stringsAsFactors=T)
Master = within(Master, {
  year = as.factor(year)
  year = relevel(year, ref='2000')})
Master['sq_exp'] = Master['experience.sum_auth']^2

# ########### #
# TYPE SAMPLE #
# ########### #
Master = Master[!is.na(Master[[var$reg_negbin]]),]
var_groups = grep("group_", names(Master), value=TRUE)
var$other = c(var$other, var_groups)

# SUMMARY STATISTICS
varlist = c(var$reg_negbin, var$reg_logit, var$reg_ols, var$auth[1:2], var$paper)
temp.sum = Master[, names(Master) %in% varlist]
summary = get_summary(temp.sum[, varlist])
rownames(summary) = c(attr(varlist, "names"))
w = latex(summary, rowlabel="", booktabs=T, table.env=F,
          file=paste0(out_folder, "Tables/dis_summary.tex"))

# REGRESSIONS
# Preparation
est = list()

# NegBin regression
base = paste(c(var$auth, var$paper, var$other), collapse="+")
f = paste(var$reg_negbin, base, sep="~")
est[["dis_experience"]] = negbinmfx(f, data=Master, atmean=F)$fit

# Logit regression
f = paste(var$reg_logit, base, sep="~")
est[["dis_top"]] = glm(f, data=Master, family="binomial")

# OLS regressions
for (centr in var$reg_ols) {
  f = paste(centr, base, sep="~")
  est[[centr]] = lm(f, data=Master)
}

# LaTeX table
lines = list(c("Discussion year FE", rep("\\checkmark", length(est))),
             c("NBER group FE", rep("\\checkmark", length(est))))
stargazer(est, report="vc*p", header=F,
          out=paste0(out_folder, "Tables/dis_reg.tex"),
          omit=var$other, omit.stat=omit_stats, add.lines=lines, style=style,
          covariate.labels=attr(c(var$auth, var$paper), "names"), model.numbers=T,
          column.labels=attr(c(var$reg_negbin, var$logit, var$reg_ols), "names"),
          omit.table.layout="n", dep.var.labels.include=F, align=T, float=F)
