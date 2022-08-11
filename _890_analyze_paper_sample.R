#!/usr/bin/Rscript
setwd("/home/panther/Science/Projects/discussants")
#
# Variables
#
masterfile = "./880_paper_samples/main.csv"
out_folder = "./990_output/"

font = "Utopia"  # For graphs
style = "qje"  # For tables
omit_stats = c("chi2", 'll', 'theta', 'ser', 'adj.rsq')  # Drop summary stats

var = list()
# Dependent variables
var$publication = "published"
attr(var$publication, "names") = "Published"
var$dep_journal = 'SJR'
attr(var$dep_journal, "names") = "SJR indicator"
var$dep_class = "top"
attr(var$dep_class, "names") = "Top publication"
var$dep_cit = "total_citations"
attr(var$dep_cit, "names") = "Total citations"
var$dep = c(var$dep_cit, var$dep_class, var$dep_journal)
# Controls
var$paper = c("num_pages", "num_auth", "age", "agesq")
attr(var$paper, "names") = c("\\# of pages", "\\# of authors", "Age", 'Age$^2$')
var$auth = c("euclid_auth", "statusmin_auth", "statusmax_auth")
attr(var$auth, "names") = c("Author total Euclid", "Experience of youngest author",
                            "Experience of oldest author")
var$group = c("euclid.mean_group", "euclid.max_group")
attr(var$group, "names") = c("Group avg. Euclid", "Group max. Euclid")
var$other = c("pub_year")
# Variables of interest
var$main = "has_discussion"
attr(var$main, "names") = "Discussion"
var$dis = c("euclid_dis", "experience_dis", "female_dis", "practitioner_dis", "editor_dis")
attr(var$dis, "names") = c("Discussant Euclid", "Discussant experience",
                           "Female discussant",  "Discussant is practitioner",
                           "Discussant is editor")
var$centr = c('coauth_neighborhood_45_dis', 'informal_neighborhood_45_dis')
attr(var$centr, "names") = c("Discussant co-author neighborhood",
                             "Discussant informal neighborhood")

lags = 0:13; # Number of lags for citation regressions
eighty_cutoff = 11 # Lag beyond which less than 80% of obs are available


#
# Load packages
#
suppressPackageStartupMessages({
  require(stringi)
  require(plyr)
  require(Hmisc)
  require(extrafont)
  require(arm)
  require(stargazer)
  require(mfx)
  require(lfe)
  require(ggplot2)
  require(interactions)
  require(ggpubr)
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
compute_correlation = function(df, varlist) {
  m = cor(df[, varlist], use="pairwise.complete.obs", method="pearson")
  colnames(m) = rownames(m) = attr(varlist, "names")
  spear = cor(df[, varlist], use="pairwise.complete.obs", method="spearman")
  m[upper.tri(m)] = spear[upper.tri(spear)]
  diag(m) = NA
  return(m)
}
make_coefplot_centr = function(temp, base, network, label) {
  coefs = c()
  stds = c()
  for (att in seq(5, 95, by=10)) {
    v = paste(network, "neighborhood", att, "dis", sep="_")
    f = paste0(base, "+", v, "|0|0|group")
    x = felm(eval(parse(text=f)), data=temp)
    coefs = cbind(coefs, summary(x)$coefficients[v, "Estimate"])
    stds = cbind(stds, summary(x)$coefficients[v, "Cluster s.e."])
  }
  pdf(paste0(out_folder, "Figures/coefplot-", label, "_", network, ".pdf"),
      width=8, height=5, family=font)
  coefplot(coefs[1,], stds[1,], vertical=F, varnames=seq(0.05, 0.95, by=0.1),
           var.las=1, main="", upper.conf.bounds=coefs[1,] + 1.645*stds[1,],
           lower.conf.bounds=coefs[1,] - 1.645*stds[1,])
  dev.off()
}


#
#  Read in
#
Master = read.csv(masterfile, stringsAsFactors=T)
Master = within(Master, {
  pub_year = as.factor(pub_year)
  journal = relevel(journal, ref='Journal of Finance')
})
Master['top'] = pmax(Master$top_finance, Master$top_econ)
Master['agesq'] = Master['age']^2
Master['euclidsq_dis'] = Master['euclid_dis']^2
Master['statusmin_auth'] = relevel(Master[['statusmin_auth']], ref="7-15")
Master['statusmax_auth'] = relevel(Master[['statusmax_auth']], ref="7-15")
Master["wp"] = !is.na(Master["nber_wp"])
Master["cit_log"] = log(1+Master[["total_citations"]])
var_groups = grep("group_", names(Master), value=TRUE)
var$other = c(var$other, var_groups)
var$jel = grep("JEL_", names(Master), value=TRUE)
var$jel = var$jel[2:length(var$jel)]  # Drop JEL_B
Master[var$jel] <- lapply(Master[var$jel], factor)


# #################### #
# PRESENTATIONS SAMPLE #
# #################### #
temp = Master
varlist = c(var$publication, var$main)
temp.sum = Master[, names(Master) %in% varlist]
summary_pres = get_summary(temp.sum[, varlist])
rownames(summary_pres) = c(attr(varlist, "names"))
w = latex(summary_pres, rowlabel="", booktabs=T, table.env=F,
          file=paste0(out_folder, "Tables/publication_summary.tex"))

# REGRESSION ON PUBLICATION
temp[["num_auth"]] = as.factor(temp[["num_auth"]])
est_pub = list()
f = paste(var$publication, paste(var$main, var$paper[2], sep="+"), sep="~")
est_pub[["dis"]] = logitmfx(f, data=temp)$fit
f = paste(f, "wp", sep="+")
est_pub[["type"]] = logitmfx(f, data=temp)$fit
labels = c(attr(var$main, "names"), "NBER Working Paper")
lines = list(c("\\# of authors FE", rep("\\checkmark", length(est_pub))))
stargazer(est_pub, report="vc*p", header=F,
          out=paste0(out_folder, "Tables/publication_reg.tex"),
          omit.table.layout="n", omit.stat=omit_stats, align=T, float=F,
          omit=var$paper, covariate.labels=labels,
          dep.var.labels="Published", style=style, add.lines=lines)


# ############## #
# JOURNAL SAMPLE #
# ############## #
temp = Master[Master[["type"]] == 'Journal',]

# SUMMARY STATISTICS
varlist = c(var$dep, var$paper[1:3], var$auth[1], "expmin_auth", "expmax_auth", var$main)
attr(varlist, "names")[8] = "Youngest author experience"
attr(varlist, "names")[9] = "Oldest author experience"
temp.sum = temp[, names(temp) %in% varlist]
summary_dis = get_summary(temp.sum[, varlist])
rownames(summary_dis) = attr(varlist, "names")
print(mean(temp[[var$dep_class]]))
w = latex(summary_dis, rowlabel="", booktabs=T, table.env=F,
          file=paste0(out_folder, "Tables/discussion_summary.tex"))

# CORRELATION
cor_matrix = compute_correlation(temp.sum, varlist)
w = latex(cor_matrix, file=paste0(out_folder, "Tables/discussion_correlation.tex"),
          booktabs=T, dec=2, colheads=F, table.env=F)

# COEFPLOT FOR CITATION COUNT IN DIFFERENT YEARS
temp[["num_auth"]] = as.factor(temp[["num_auth"]])
f_base = paste0(paste(c(var$paper, var$auth, var$main, var$group[1], var$other[1], "SJR", var$jel), collapse="+"),
                "|0|0|group")
# Base regression
f = paste("cit_log", f_base, sep="~")
est = felm(eval(parse(text=f)), data=temp)
coefs = cbind(summary(est)$coefficients[var$main, "Estimate"])
stds = cbind(summary(est)$coefficients[var$main, "Cluster s.e."])
# Yearly Regressions
for (lag in lags) {
  var_name = paste0("citcount_", lag)
  subset = temp[!is.na(temp[[var_name]]),]
  subset["cit_log"] = log(1+subset[[var_name]])
  x = felm(eval(parse(text=f)), data=subset)
  coefs = cbind(coefs, summary(x)$coefficients["has_discussion", "Estimate"])
  stds = cbind(stds, summary(x)$coefficients["has_discussion", "Cluster s.e."])
}
pdf(paste0(out_folder, "Figures/coefplot-citations_discussion.pdf"),
    width=8, height=5, family=font)
coefplot(coefs[1,], stds[1,], vertical=F, varnames=c("base", lags), var.las=1,
         main="", xlab="Years since publication",
         upper.conf.bounds=coefs[1,] + 1.645*stds[1,],
         lower.conf.bounds=coefs[1,] - 1.645*stds[1,])
dev.off()


# ################## #
# DISCUSSANTS SAMPLE #
# ################## #
temp = Master[(Master[["type"]] == 'Journal') & (!is.na(Master[["experience_dis"]])),]

# SUMMARY STATISTICS
varlist = c(var$dep, var$paper[1:length(var$paper)-1], var$auth[1],
            var$dis, var$centr)
temp.sum = temp[, names(temp) %in% varlist]
print(mean(temp[[var$dep_class]]))
summary_type = get_summary(temp.sum[, varlist])
rownames(summary_type) = attr(varlist, "names")
w = latex(summary_type, rowlabel="", booktabs=T, table.env=F,
          file=paste0(out_folder, "Tables/type_summary.tex"))

# CORRELATION
cor_matrix = compute_correlation(temp.sum, varlist)
w = latex(cor_matrix, file=paste0(out_folder, "Tables/type_correlation.tex"),
          booktabs=T, dec=2, colheads=F, table.env=F)

# CENTRALITY REGRESSION
base = paste(c(var$paper, var$auth, var_groups, "euclid_dis", "female_dis", "status_dis", var$jel),
             collapse="+")
f = paste("cit_log", paste(base, var$dep_journal, sep="+"), sep="~")
make_coefplot_centr(temp, f, "coauth", "citations")
make_coefplot_centr(temp, f, "informal", "citations")
make_coefplot_centr(temp, f, "coauth", "sjr")
make_coefplot_centr(temp, f, "informal", "sjr")
