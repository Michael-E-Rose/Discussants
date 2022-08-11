log using ".\990_output\891_log.smcl", replace

* Read in
import delimited ".\880_paper_samples\main.csv", clear

drop if type != "Journal"

* Compute variables
encode statusmin_auth, gen(statusmin_a)
encode statusmax_auth, gen(statusmax_a)
encode status_dis, gen(status_d)
encode journal, gen(journal_f)

gen ln_sjr = ln(sjr)
gen ln_avg_citations = ln(avg_citations)
gen ln_hindex = ln(hindex)
gen ln_total_citations = ln(1+total_citations)
gen asinh_total_citations = asinh(total_citations)
gen top_field = top_g + top_e
gen top = top_econ + top_finance

gen group_main = group
replace group_main = "RISK" if group == "AP-RISK"
replace group_main = "RISK" if group == "CF-RISK"
replace group_main = "IFM" if group == "EFEL-IFM"

* Label variables
label variable has_discussion "Discussion"
label variable pres_gunningfog "Readability"

label variable top_e "Top (E)"
label variable top_g "Top (G)"
label variable top_f "Top (F)"
label variable top_field "Top (Field)"
label variable top_finance "Top (Finance)"
label variable top_econ "Top (Econ)"
label variable top "Top (Econ+Finance)"
label variable sjr "SJR"
label variable ln_sjr "log(SJR)"
label variable avg_citations "Avg. citations"
label variable ln_avg_citations "log(Avg. citations)"
label variable hindex "h-index"
label variable ln_hindex "log(h-index)"
label variable total_citations "Total citations"
label variable ln_total_citations "log(1+Total citations)"
label variable asinh_total_citations "asinh(Total citations)"

label variable euclid_dis "Discussant Euclid"
label variable status_d "Discussant Experience"
label variable female_dis "Female Discussant"
label variable tilburg_rank_weighted_dis "Discussant affiliation rank"
label variable editor_dis "Discussant is editor"
label variable practitioner_dis "Discussant is practitioner"

* Main regressions
** Top journals
eststo: qui logit top_finance i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, vce(cluster group)
eststo: qui logit top_finance i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, vce(cluster group)
eststo: qui logit top i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, vce(cluster group)
eststo: qui logit top i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, vce(cluster group)
esttab using ./990_output/Tables/discussion_reg-class, replace label ///
    alignment(D{.}{.}{-1}) p star(* 0.1 ** 0.05 *** 0.01) delimiter(_tab "&") booktabs ///
	nolegend nonote stats(N r2_p aic, labels("\textit{N}" "Pseudo R$^{2}$" "AIC")) ///
	wrap varwidth(20) modelwidth(15) drop(*.num_auth *age* *.statusmin_a *.statusmax_a) ///
    indicate("Paper controls=num_pages" "Author controls=euclid_auth" "Group control=euclidmean_group" "JEL categories=jel_*", labels("\multicolumn{1}{c}{$\checkmark$}" ""))
estimates clear

ritest has_discussion _b[has_discussion], cluster(group_main) reps(1022) seed(42): ///
	logit top_finance i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, vce(cluster group)
ritest has_discussion _b[has_discussion], cluster(group_main) reps(1022) seed(42): ///
	logit top_finance i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, vce(cluster group)
ritest has_discussion _b[has_discussion], cluster(group_main) reps(1022) seed(42): ///
	logit top i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, vce(cluster group)
ritest has_discussion _b[has_discussion], cluster(group_main) reps(1022) seed(42): ///
	logit top i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, vce(cluster group)

** Journal quality
eststo: qui regress sjr i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, cluster(group)
eststo: qui regress sjr i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, cluster(group)
eststo: qui regress avg_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, cluster(group)
eststo: qui regress avg_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, cluster(group)
eststo: qui regress hindex i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, cluster(group)
eststo: qui regress hindex i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, cluster(group)
esttab using ./990_output/Tables/discussion_reg-journal, replace label ///
    alignment(D{.}{.}{-1}) p star(* 0.1 ** 0.05 *** 0.01) delimiter(_tab "&") booktabs ///
	nolegend nonote stats(N r2, labels("\textit{N}" "R$^{2}$")) ///
	wrap varwidth(20) modelwidth(15) drop(*.num_auth *age* *.statusmin_a *.statusmax_a) ///
    indicate("Paper controls=num_pages" "Author controls=euclid_auth" "Group control=euclidmean_group" "JEL categories=jel_*", labels("\multicolumn{1}{c}{$\checkmark$}" ""))
estimates clear

ritest has_discussion _b[has_discussion], cluster(group_main) reps(1022) seed(42): ///
	regress sjr i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, cluster(group)
ritest has_discussion _b[has_discussion], cluster(group_main) reps(1022) seed(42): ///
	regress sjr i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, cluster(group)
ritest has_discussion _b[has_discussion], cluster(group_main) reps(1022) seed(42): ///
	regress avg_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, cluster(group)
ritest has_discussion _b[has_discussion], cluster(group_main) reps(1022) seed(42): ///
	regress avg_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, cluster(group)
ritest has_discussion _b[has_discussion], cluster(group_main) reps(1022) seed(42): ///
	regress hindex i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, cluster(group)
ritest has_discussion _b[has_discussion], cluster(group_main) reps(1022) seed(42): ///
	regress hindex i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, cluster(group)

** Citation count (log-transformed)
eststo: qui regress ln_total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group i.pub_year, cluster(group)
eststo: qui regress ln_total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group i.pub_year jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, cluster(group)
eststo: qui regress ln_total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group i.pub_year jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z sjr, cluster(group)
eststo: qui regress ln_total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group i.pub_year jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z i.journal_f, cluster(group)
esttab using ./990_output/Tables/discussion_reg-citations, replace label ///
    alignment(D{.}{.}{-1}) p star(* 0.1 ** 0.05 *** 0.01) delimiter(_tab "&") booktabs ///
	nolegend nonote stats(N r2, labels("\textit{N}" "R$^{2}$")) ///
	wrap varwidth(20) modelwidth(15) drop(*.num_auth *age* *.statusmin_a *.statusmax_a) ///
    indicate("Paper controls=num_pages" "Author controls=euclid_auth" "Group control=euclidmean_group" "Publication year FE=*pub_year*" "JEL categories=jel_*" "Journal control=sjr" "Journal FE=*journal_f*", labels("\multicolumn{1}{c}{$\checkmark$}" ""))
estimates clear

* Robustness checks
** log of journal quality measures
eststo: qui regress ln_sjr i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, cluster(group)
eststo: qui regress ln_sjr i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, cluster(group)
eststo: qui regress ln_avg_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, cluster(group)
eststo: qui regress ln_avg_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, cluster(group)
eststo: qui regress ln_hindex i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, cluster(group)
eststo: qui regress ln_hindex i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, cluster(group)
esttab using ./990_output/Tables/discussion_reg-journal-log, replace label ///
    alignment(D{.}{.}{-1}) p star(* 0.1 ** 0.05 *** 0.01) delimiter(_tab "&") booktabs ///
	nolegend nonote stats(N r2, labels("\textit{N}" "R$^{2}$")) ///
	wrap varwidth(20) modelwidth(15) drop(*.num_auth *age* *.statusmin_a *.statusmax_a) ///
    indicate("Paper controls=num_pages" "Author controls=euclid_auth" "Group control=euclidmean_group" "JEL categories=jel_*", labels("\multicolumn{1}{c}{$\checkmark$}" ""))
estimates clear

** Negative Binomial citation
eststo: qui nbreg total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group i.pub_year, cluster(group)
eststo: qui nbreg total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group i.pub_year jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, cluster(group)
eststo: qui nbreg total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group i.pub_year jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z sjr, cluster(group)
esttab using ./990_output/Tables/discussion_reg-citations-negbin, replace label ///
    alignment(D{.}{.}{-1}) p star(* 0.1 ** 0.05 *** 0.01) delimiter(_tab "&") booktabs ///
	nolegend nonote stats(N r2_p aic, labels("\textit{N}" "Pseudo R$^{2}$" "AIC")) ///
	wrap varwidth(20) modelwidth(15) drop(*.num_auth *age* *.statusmin_a *.statusmax_a lnalpha) ///
    indicate("Paper controls=num_pages" "Author controls=euclid_auth" "Group control=euclidmean_group" "Publication year FE=*pub_year*" "JEL categories=jel_*" "Journal control=sjr", labels("\multicolumn{1}{c}{$\checkmark$}" ""))
estimates clear

** asinh-transformed citation count
eststo: qui regress asinh_total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group i.pub_year, cluster(group)
eststo: qui regress asinh_total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group i.pub_year jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z, cluster(group)
eststo: qui regress asinh_total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group i.pub_year jel_c jel_d jel_e jel_f jel_g jel_h jel_i jel_j jel_k jel_k jel_l jel_m jel_n jel_o jel_p jel_q jel_r jel_z sjr, cluster(group)
esttab using ./990_output/Tables/discussion_reg-citations-asinh, replace label ///
    alignment(D{.}{.}{-1}) p star(* 0.1 ** 0.05 *** 0.01) delimiter(_tab "&") booktabs ///
	nolegend nonote stats(N r2, labels("\textit{N}" "R$^{2}$")) ///
	wrap varwidth(20) modelwidth(15) drop(*.num_auth *age* *.statusmin_a *.statusmax_a) ///
    indicate("Paper controls=num_pages" "Author controls=euclid_auth" "Group control=euclidmean_group" "Publication year FE=*pub_year*" "JEL categories=jel_*" "Journal control=sjr", labels("\multicolumn{1}{c}{$\checkmark$}" ""))
estimates clear

** Readability control
preserve
drop if pres_gunningfog == .
eststo: qui logit top i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, vce(cluster group)
eststo: qui logit top i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group pres_gunningfog, vce(cluster group)
eststo: qui regress sjr i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, cluster(group)
eststo: qui regress sjr i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group pres_gunningfog, cluster(group)
eststo: qui regress ln_total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group i.pub_year sjr, cluster(group)
eststo: qui regress ln_total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group pres_gunningfog i.pub_year sjr, cluster(group)
esttab using ./990_output/Tables/discussion_reg-readability, replace label ///
    alignment(D{.}{.}{-1}) p star(* 0.1 ** 0.05 *** 0.01) delimiter(_tab "&") booktabs ///
	nolegend nonote stats(N r2 r2_p aic, labels("\textit{N}" "R$^{2}$" "Pseudo R$^{2}$" "AIC")) ///
	wrap varwidth(20) modelwidth(15) drop(*.num_auth *age* *.statusmin_a *.statusmax_a) ///
    indicate("Paper controls=num_pages" "Author controls=euclid_auth" "Group control=euclidmean_group" "Publication year FE=*pub_year*" "Journal control=sjr", labels("\multicolumn{1}{c}{$\checkmark$}" ""))
estimates clear
restore

** Monetary sample regressions
preserve
keep if group_main == "ME" | group_main == "EFCE" | group_main == "EFEL" | group_main == "IFM"

eststo: qui logit top i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, vce(cluster group)
eststo: qui regress sjr i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group, cluster(group)
eststo: qui regress ln_total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a has_discussion euclidmean_group i.pub_year sjr, cluster(group)
esttab using ./990_output/Tables/discussion_reg-monetary, replace label ///
    alignment(D{.}{.}{-1}) p star(* 0.1 ** 0.05 *** 0.01) delimiter(_tab "&") booktabs ///
	nolegend nonote stats(N r2 r2_p aic, labels("\textit{N}" "R$^{2}$" "Pseudo R$^{2}$" "AIC")) ///
	wrap varwidth(20) modelwidth(15) drop(*.num_auth *age* *.statusmin_a *.statusmax_a) ///
    indicate("Paper controls=num_pages" "Author controls=euclid_auth" "Group control=euclidmean_group" "Publication year FE=*pub_year*" "Journal control=sjr", labels("\multicolumn{1}{c}{$\checkmark$}" ""))
estimates clear
restore

* Channel explorations
drop if experience_dis == .

** Discussant status
eststo: qui logit top i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a euclid_dis i.status_d i.female_dis tilburg_rank_weighted_dis group_amre group_ap group_cf group_efce group_efel group_effe group_ifm group_me group_pere group_risk, vce(cluster group)
eststo: qui logit top i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a euclid_dis i.status_d i.female_dis i.practitioner_dis i.editor_dis group_amre group_ap group_cf group_efce group_efel group_effe group_ifm group_me group_pere group_risk, vce(cluster group)
eststo: qui reg sjr i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a euclid_dis i.status_d i.female_dis tilburg_rank_weighted_dis group_amre group_ap group_cf group_efce group_efel group_effe group_ifm group_me group_pere group_risk, vce(cluster group)
eststo: qui reg sjr i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a euclid_dis i.status_d i.female_dis i.practitioner_dis i.editor_dis group_amre group_ap group_cf group_efce group_efel group_effe group_ifm group_me group_pere group_risk, vce(cluster group)
eststo: qui reg ln_total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a euclid_dis i.status_d i.female_dis tilburg_rank_weighted_dis group_amre group_ap group_cf group_efce group_efel group_effe group_ifm group_me group_pere group_risk sjr, vce(cluster group)
eststo: qui reg ln_total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a euclid_dis i.status_d i.female_dis i.practitioner_dis i.editor_dis group_amre group_ap group_cf group_efce group_efel group_effe group_ifm group_me group_pere group_risk sjr, vce(cluster group)
esttab using ./990_output/Tables/type_reg-status, replace label ///
    alignment(D{.}{.}{-1}) p star(* 0.1 ** 0.05 *** 0.01) delimiter(_tab "&") booktabs ///
	nolegend nonote stats(N r2 r2_p aic, labels("\textit{N}" "R$^{2}$" "Pseudo R$^{2}$" "AIC")) ///
	substitute("=1" "") nobaselevels wrap varwidth(20) modelwidth(15) drop(*.num_auth *age* *.statusmin_a *.statusmax_a) ///
    indicate("Group FE=*group*" "Paper controls=num_pages" "Author controls=euclid_auth" "Journal control=sjr", labels("\multicolumn{1}{c}{$\checkmark$}" ""))
estimates clear

** Discussant Centrality
eststo: qui logit top i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a euclid_dis i.status_d group_amre group_ap group_cf group_efce group_efel group_effe group_ifm group_me group_pere group_risk i.female_dis coauth_neighborhood_45_dis informal_neighborhood_45_dis, vce(cluster group)
eststo: qui reg sjr ii.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a euclid_dis i.status_d group_amre group_ap group_cf group_efce group_efel group_effe group_ifm group_me group_pere group_risk i.female_dis coauth_neighborhood_45_dis informal_neighborhood_45_dis, vce(cluster group)
eststo: qui reg ln_total_citations i.num_auth num_pages age c.age#c.age euclid_auth i.statusmin_a i.statusmax_a euclid_dis i.status_d group_amre group_ap group_cf group_efce group_efel group_effe group_ifm group_me group_pere group_risk i.female_dis coauth_neighborhood_45_dis informal_neighborhood_45_dis sjr, vce(cluster group)
esttab using ./990_output/Tables/type_reg-centrality, replace label ///
    alignment(D{.}{.}{-1}) p star(* 0.1 ** 0.05 *** 0.01) delimiter(_tab "&") booktabs ///
	nolegend nonote stats(N r2 r2_p aic, labels("\textit{N}" "R$^{2}$" "Pseudo R$^{2}$" "AIC")) ///
	substitute("=1" "") nobaselevels wrap varwidth(20) modelwidth(15) drop(*.num_auth *age* *.statusmin_a *.statusmax_a) ///
    indicate("Group FE=*group*" "Paper controls=num_pages" "Author controls=euclid_auth" "Journal control=sjr", labels("\multicolumn{1}{c}{$\checkmark$}" ""))
estimates clear

log close
